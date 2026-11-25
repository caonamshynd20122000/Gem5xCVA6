/*
 * Copyright (c) 2026 Gem 5 x CVA6 Project
 * Implementation of WayShutdownSetAssoc for 16-Way Write-Back Shared L2 Cache in gem5.
 */

#include "mem/cache/tags/way_shutdown_tags.hh"

#include <algorithm>
#include <cmath>

#include "sim/system.hh"

namespace gem5
{

WayShutdownSetAssoc::WayShutdownStats::WayShutdownStats(statistics::Group *parent)
    : statistics::Group(parent, "way_shutdown"),
      ADD_STAT(epochsEvaluated, statistics::units::Count::get(),
               "Number of L2 Way-Shutdown epochs evaluated"),
      ADD_STAT(wayShutdownEvents, statistics::units::Count::get(),
               "Number of L2 way shutdown transitions (1 -> 0)"),
      ADD_STAT(wayWakeupEvents, statistics::units::Count::get(),
               "Number of L2 way wakeup transitions (0 -> 1)"),
      ADD_STAT(dirtyFlushWritebacks, statistics::units::Count::get(),
               "Number of dirty L2 cache lines flushed to DRAM on way shutdown"),
      ADD_STAT(activeWayAccessAccum, statistics::units::Count::get(),
               "Cumulative active ways probed across all L2 accesses"),
      ADD_STAT(wayActiveEpochs, statistics::units::Count::get(),
               "Number of epochs each L2 way [0..15] remained active")
{
    wayActiveEpochs.init(16);
}

WayShutdownSetAssoc::WayShutdownSetAssoc(const Params &p)
    : BaseSetAssoc(p),
      policyMode(p.policy_mode),
      initialActiveWays(p.initial_active_ways),
      minActiveWays(p.min_active_ways),
      epochAccesses(p.epoch_accesses),
      wakeupLatency(p.wakeup_latency),
      currentActiveWays(std::clamp<unsigned>(p.initial_active_ways, 1, p.assoc)),
      epochAccessCnt(0),
      epochMissCnt(0),
      lowMissStreak(0),
      atdSampledAccesses(0),
      wsStats(this)
{
    wayEnableMask = (currentActiveWays >= 16)
        ? 0xFFFFU
        : static_cast<uint16_t>((1U << currentActiveWays) - 1U);
    allocAssoc = currentActiveWays;

    epochWayHits.fill(0);
    atdStackHits.fill(0);
    for (auto &s : atdSets) {
        s.lruStackTags.fill(0);
        s.valid.fill(false);
    }
}

CacheBlk*
WayShutdownSetAssoc::findBlock(const CacheBlk::KeyType &key) const
{
    std::vector<ReplaceableEntry*> entries = indexingPolicy->getPossibleEntries(key);
    for (ReplaceableEntry* entry : entries) {
        unsigned way = entry->getWay();
        if ((wayEnableMask & (1U << way)) == 0) {
            continue;
        }
        CacheBlk* blk = static_cast<CacheBlk*>(entry);
        if (blk->match(key)) {
            return blk;
        }
    }
    return nullptr;
}

CacheBlk*
WayShutdownSetAssoc::accessBlock(const PacketPtr pkt, Cycles &lat)
{
    Cycles extra_lat(0);
    if (epochAccessCnt >= epochAccesses) {
        evaluateEpochPolicy(extra_lat);
    }

    Addr addr = pkt->getAddr();
    probeAndUpdateAtd(addr);

    CacheBlk *blk = findBlock({addr, pkt->isSecure()});

    // Only enabled ways are probed in parallel (gates dynamic tag & data lookup energy)
    stats.tagAccesses += currentActiveWays;
    wsStats.activeWayAccessAccum += currentActiveWays;
    if (sequentialAccess) {
        if (blk != nullptr) {
            stats.dataAccesses += 1;
        }
    } else {
        stats.dataAccesses += currentActiveWays;
    }

    epochAccessCnt++;
    if (blk != nullptr) {
        blk->increaseRefCount();
        replacementPolicy->touch(blk->replacementData, pkt);
        unsigned hit_way = blk->getWay();
        if (hit_way < 16) {
            epochWayHits[hit_way]++;
        }
    } else {
        epochMissCnt++;
    }

    lat = lookupLatency + extra_lat;
    return blk;
}

CacheBlk*
WayShutdownSetAssoc::findVictim(const CacheBlk::KeyType &key,
                                const std::size_t size,
                                std::vector<CacheBlk*>& evict_blks,
                                const uint64_t partition_id)
{
    std::vector<ReplaceableEntry*> all_entries = indexingPolicy->getPossibleEntries(key);
    std::vector<ReplaceableEntry*> active_entries;
    active_entries.reserve(currentActiveWays);

    for (ReplaceableEntry* entry : all_entries) {
        if (wayEnableMask & (1U << entry->getWay())) {
            active_entries.push_back(entry);
        }
    }

    if (partitionManager) {
        partitionManager->filterByPartition(active_entries, partition_id);
    }

    CacheBlk* victim = active_entries.empty() ? nullptr :
        static_cast<CacheBlk*>(replacementPolicy->getVictim(active_entries));
    evict_blks.push_back(victim);
    return victim;
}

void
WayShutdownSetAssoc::probeAndUpdateAtd(Addr addr)
{
    unsigned set_idx = (addr >> 6) & 0x1FFU; // 512 sets, 64B line
    if ((set_idx & ATD_SET_MASK) != 0) {
        return; // Only sample 1 in 32 sets (16 sampled sets total)
    }
    unsigned atd_idx = (set_idx >> 5) & (ATD_NUM_SETS - 1);
    Addr tag = addr >> 15;
    AtdSet &aset = atdSets[atd_idx];
    atdSampledAccesses++;

    int hit_depth = -1;
    for (unsigned d = 0; d < 16; d++) {
        if (aset.valid[d] && aset.lruStackTags[d] == tag) {
            hit_depth = static_cast<int>(d);
            break;
        }
    }

    if (hit_depth >= 0) {
        atdStackHits[hit_depth]++;
        // Move hit tag to MRU position (depth 0) preserving LRU stack property
        for (int d = hit_depth; d > 0; d--) {
            aset.lruStackTags[d] = aset.lruStackTags[d - 1];
            aset.valid[d] = aset.valid[d - 1];
        }
        aset.lruStackTags[0] = tag;
        aset.valid[0] = true;
    } else {
        // Shift stack down and insert at MRU (depth 0)
        for (int d = 15; d > 0; d--) {
            aset.lruStackTags[d] = aset.lruStackTags[d - 1];
            aset.valid[d] = aset.valid[d - 1];
        }
        aset.lruStackTags[0] = tag;
        aset.valid[0] = true;
    }
}

uint64_t
WayShutdownSetAssoc::countDirtyBlocksInWay(unsigned way) const
{
    uint64_t dirty_cnt = 0;
    for (const CacheBlk &blk : blks) {
        if (blk.isValid() && blk.getWay() == way && blk.isSet(CacheBlk::DirtyBit)) {
            dirty_cnt++;
        }
    }
    return dirty_cnt;
}

uint64_t
WayShutdownSetAssoc::shutdownWayAndFlushDirty(unsigned way)
{
    uint64_t flushed = 0;
    for (CacheBlk &blk : blks) {
        if (blk.isValid() && blk.getWay() == way) {
            if (blk.isSet(CacheBlk::DirtyBit)) {
                flushed++;
                if (blk.data != nullptr) {
                    Addr blk_addr = regenerateBlkAddr(&blk);
                    system->physProxy.writeBlob(blk_addr, blk.data, blkSize);
                }
                blk.clearCoherenceBits(CacheBlk::DirtyBit);
            }
            invalidate(&blk);
        }
    }
    wsStats.dirtyFlushWritebacks += flushed;
    return flushed;
}

void
WayShutdownSetAssoc::evaluateEpochPolicy(Cycles &extra_lat)
{
    wsStats.epochsEvaluated++;
    for (unsigned w = 0; w < 16; w++) {
        if (wayEnableMask & (1U << w)) {
            wsStats.wayActiveEpochs[w]++;
        }
    }

    unsigned target_ways = currentActiveWays;
    double miss_rate = (epochAccessCnt > 0)
        ? (static_cast<double>(epochMissCnt) / static_cast<double>(epochAccessCnt))
        : 0.0;

    if (policyMode == 0) {
        // Mode 0: Static (keep initialActiveWays fixed)
        target_ways = currentActiveWays;
    } else if (policyMode == 1) {
        // Mode 1: Selective Cache Ways (Albonesi Miss-Rate Threshold + Hysteresis)
        if (miss_rate > 0.045) {
            lowMissStreak = 0;
            target_ways = std::min<unsigned>(16, currentActiveWays + 4);
        } else if (miss_rate < 0.020) {
            lowMissStreak++;
            if (lowMissStreak >= 2 && currentActiveWays > minActiveWays) {
                target_ways = std::max<unsigned>(minActiveWays, currentActiveWays - 2);
            }
        } else {
            lowMissStreak = 0;
        }
    } else if (policyMode == 2) {
        // Mode 2: Per-Way Utilization Counter
        unsigned active_util_ways = 0;
        uint64_t util_thresh = std::max<uint64_t>(2, epochAccessCnt / 80); // >= 1.25% of accesses
        for (unsigned w = 0; w < currentActiveWays; w++) {
            if (epochWayHits[w] >= util_thresh) {
                active_util_ways = w + 1;
            }
        }
        if (miss_rate > 0.040 && active_util_ways >= currentActiveWays - 1) {
            target_ways = std::min<unsigned>(16, currentActiveWays + 2);
        } else if (active_util_ways + 1 < currentActiveWays) {
            target_ways = std::max<unsigned>(minActiveWays, currentActiveWays - 2);
        }
    } else if (policyMode == 3) {
        // Mode 3: Core-Aware Sampled-Set ATD + Write-Back Dirty-Flush Cost Guard
        uint64_t total_atd_hits = 0;
        for (unsigned d = 0; d < 16; d++) {
            total_atd_hits += atdStackHits[d];
        }

        if (total_atd_hits == 0 || (atdSampledAccesses > 0 &&
            static_cast<double>(total_atd_hits) / static_cast<double>(atdSampledAccesses) < 0.05)) {
            // Pure streaming / non-reusable phase: extra ways yield ~0 marginal hits!
            target_ways = std::max<unsigned>(minActiveWays, 4);
        } else {
            // Find minimum ways k* capturing >= 98.5% of full 16-way ATD stack hits
            uint64_t target_hits = static_cast<uint64_t>(std::ceil(total_atd_hits * 0.985));
            uint64_t cum_hits = 0;
            unsigned k_opt = minActiveWays;
            for (unsigned d = 0; d < 16; d++) {
                cum_hits += atdStackHits[d];
                if (cum_hits >= target_hits) {
                    k_opt = std::max<unsigned>(minActiveWays, d + 1);
                    break;
                }
            }
            // Align up to even step (2, 4, 6, 8, 10, 12, 14, 16)
            if (k_opt & 1) k_opt++;
            target_ways = std::clamp<unsigned>(k_opt, minActiveWays, 16);
        }
    }

    // Apply Way Wakeup (0 -> 1) or Way Shutdown with Dirty-Flush Cost Guard (1 -> 0)
    if (target_ways > currentActiveWays) {
        unsigned woken = target_ways - currentActiveWays;
        wsStats.wayWakeupEvents += woken;
        currentActiveWays = target_ways;
        wayEnableMask = (currentActiveWays >= 16)
            ? 0xFFFFU
            : static_cast<uint16_t>((1U << currentActiveWays) - 1U);
        allocAssoc = currentActiveWays;
        extra_lat += wakeupLatency;
    } else if (target_ways < currentActiveWays) {
        for (unsigned w = currentActiveWays; w > target_ways; w--) {
            unsigned way_idx = w - 1;
            if (policyMode == 3) {
                // Dirty-Flush Cost-Benefit Guard: only shut down way if dirty lines <= 96
                uint64_t dirty_cnt = countDirtyBlocksInWay(way_idx);
                if (dirty_cnt > 96) {
                    target_ways = w;
                    break;
                }
            }
            shutdownWayAndFlushDirty(way_idx);
            wsStats.wayShutdownEvents++;
        }
        currentActiveWays = target_ways;
        wayEnableMask = (currentActiveWays >= 16)
            ? 0xFFFFU
            : static_cast<uint16_t>((1U << currentActiveWays) - 1U);
        allocAssoc = currentActiveWays;
    }

    // Reset epoch counters (decay ATD stack counters by half for smooth phase tracking)
    epochAccessCnt = 0;
    epochMissCnt = 0;
    epochWayHits.fill(0);
    atdSampledAccesses >>= 1;
    for (unsigned d = 0; d < 16; d++) {
        atdStackHits[d] >>= 1;
    }
}

} // namespace gem5
