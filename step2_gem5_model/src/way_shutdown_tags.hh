/*
 * Copyright (c) 2026 Gem 5 x CVA6 Project
 * Custom gem5 Tag Store: WayShutdownSetAssoc for 16-Way Write-Back Shared L2 Cache
 * Extends gem5::BaseSetAssoc with dynamic 16-way enable bitmask, Write-Back dirty-way flush accounting,
 * wakeup latency, and 4 selectable policies:
 *   0 = static          (Fixed k active ways: Baseline 16-way or Static-k Oracle)
 *   1 = selective_ways  (Albonesi Miss-Rate Threshold + Hysteresis)
 *   2 = way_util        (Per-Way & Per-Core Hit Utilization Counter)
 *   3 = atd_dirty_aware (Core-Aware 16-Set Sampled ATD + Write-Back Dirty-Flush Cost Guard)
 */

#ifndef __MEM_CACHE_TAGS_WAY_SHUTDOWN_TAGS_HH__
#define __MEM_CACHE_TAGS_WAY_SHUTDOWN_TAGS_HH__

#include <array>
#include <cstdint>
#include <vector>

#include "mem/cache/tags/base_set_assoc.hh"
#include "params/WayShutdownSetAssoc.hh"

namespace gem5
{

class WayShutdownSetAssoc : public BaseSetAssoc
{
  public:
    typedef WayShutdownSetAssocParams Params;
    WayShutdownSetAssoc(const Params &p);
    virtual ~WayShutdownSetAssoc() = default;

    CacheBlk* accessBlock(const PacketPtr pkt, Cycles &lat) override;
    CacheBlk* findBlock(const CacheBlk::KeyType &key) const override;
    CacheBlk* findVictim(const CacheBlk::KeyType &key,
                         const std::size_t size,
                         std::vector<CacheBlk*>& evict_blks,
                         const uint64_t partition_id=0) override;

  protected:
    /** Policy selection: 0=static, 1=selective_ways, 2=way_util, 3=atd_dirty_aware */
    const int policyMode;
    const unsigned initialActiveWays;
    const unsigned minActiveWays;
    const unsigned epochAccesses;
    const Cycles wakeupLatency;

    /** Current 16-bit active way bitmask and active way count */
    uint16_t wayEnableMask;
    unsigned currentActiveWays;

    /** Epoch monitoring state */
    uint64_t epochAccessCnt;
    uint64_t epochMissCnt;
    uint32_t lowMissStreak;
    std::array<uint64_t, 16> epochWayHits;

    /** Sampled-Set Auxiliary Tag Directory (ATD: 16 sampled sets x 16 LRU stack ways) */
    static constexpr unsigned ATD_NUM_SETS = 16;
    static constexpr unsigned ATD_SET_MASK = 0x1F; // Sample 1 in 32 sets (512 / 32 = 16 sets)
    struct AtdSet {
        std::array<Addr, 16> lruStackTags;
        std::array<bool, 16> valid;
    };
    std::array<AtdSet, ATD_NUM_SETS> atdSets;
    std::array<uint64_t, 16> atdStackHits;
    uint64_t atdSampledAccesses;

    /** Evaluate policy at epoch boundary and update wayEnableMask */
    void evaluateEpochPolicy(Cycles &extra_lat);

    /** Count dirty blocks in a way and flush/invalidate when shutting down (1 -> 0) */
    uint64_t countDirtyBlocksInWay(unsigned way) const;
    uint64_t shutdownWayAndFlushDirty(unsigned way);

    /** Update Sampled-Set ATD on L2 access */
    void probeAndUpdateAtd(Addr addr);

    struct WayShutdownStats : public statistics::Group
    {
        WayShutdownStats(statistics::Group *parent);
        statistics::Scalar epochsEvaluated;
        statistics::Scalar wayShutdownEvents;
        statistics::Scalar wayWakeupEvents;
        statistics::Scalar dirtyFlushWritebacks;
        statistics::Scalar activeWayAccessAccum;
        statistics::Vector wayActiveEpochs;
    } wsStats;
};

} // namespace gem5

#endif // __MEM_CACHE_TAGS_WAY_SHUTDOWN_TAGS_HH__
