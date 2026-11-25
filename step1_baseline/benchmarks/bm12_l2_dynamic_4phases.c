/*
 * bm12_l2_dynamic_4phases.c — 4-Core 4-Phase Dynamic Workload on 16-Way Write-Back Shared L2
 * Synchronizes all 4 cores across 4 distinct L2 demand phases:
 *   - Phase 1 (Light):   Only Core 0 uses 3 L2 ways (96 KiB); Cores 1..3 in L1 -> Target: 4/16 ways
 *   - Phase 2 (Heavy):   All 4 Cores use 3-4 L2 ways each (14 ways = 448 KiB) -> Target: Wakeup to 16/16 ways
 *   - Phase 3 (Stream):  4 Cores stream linearly without reuse -> Target: Shrink & flush dirty ways to 4/16 ways
 *   - Phase 4 (Medium):  Cores 0 & 1 use 4 L2 ways each (8 ways = 256 KiB) -> Target: 8/16 ways
 */
#include "common/bench_4core.h"

#define DYN_MAX_WAYS 14
static uint64_t dyn_l2_banks[DYN_MAX_WAYS][L2_WAY_U64] __attribute__((aligned(32768)));
static uint64_t dyn_l1_local[NUM_CORES][512] __attribute__((aligned(4096)));

static const int p2_start[NUM_CORES] = {0, 4, 8, 11};
static const int p2_count[NUM_CORES] = {4, 4, 3, 3};

uint64_t run_benchmark_core(int cid) {
    uint64_t acc = 0x55aa55aaULL ^ (uint64_t)cid;

    /* Initialize per-core L1 & L2 banks */
    for (int i = 0; i < 512; i += 8) {
        dyn_l1_local[cid][i] = (uint64_t)(cid * 17 + i);
    }
    for (int w = 0; w < p2_count[cid]; w++) {
        int b = p2_start[cid] + w;
        for (size_t i = 0; i < L2_WAY_U64; i += 8) {
            dyn_l2_banks[b][i] = (uint64_t)(b * 257 + i);
        }
    }
    bench_phase_sync(cid, 1);

    /* PHASE 1: Light (Core 0 uses 3 L2 ways; Cores 1..3 in L1) */
    if (cid == 0) {
        for (int pass = 0; pass < 4; pass++) {
            for (size_t i = 0; i < L2_WAY_U64; i += 8) {
                uint64_t s = dyn_l2_banks[0][i] + dyn_l2_banks[1][i] + dyn_l2_banks[2][i];
                dyn_l2_banks[pass % 3][i] = s + (uint64_t)pass;
                acc += s;
            }
        }
    } else {
        for (int pass = 0; pass < 16; pass++) {
            for (int i = 0; i < 512; i += 8) {
                dyn_l1_local[cid][i] += (uint64_t)pass;
                acc ^= dyn_l1_local[cid][i];
            }
        }
    }
    bench_phase_sync(cid, 2);

    /* PHASE 2: Heavy 4-Core (All 4 cores use 14 L2 ways total = 448 KiB) */
    int ws = p2_start[cid];
    int wc = p2_count[cid];
    for (int pass = 0; pass < 4; pass++) {
        for (size_t i = 0; i < L2_WAY_U64; i += 8) {
            uint64_t s = 0;
            for (int w = 0; w < wc; w++) {
                s += dyn_l2_banks[ws + w][i];
            }
            /* Dirty write into L2 bank */
            dyn_l2_banks[ws + (pass % wc)][i] = s ^ (uint64_t)pass;
            acc += s;
        }
    }
    bench_phase_sync(cid, 3);

    /* PHASE 3: Single-pass streaming across banks (triggers dirty way flush when scaling down) */
    for (int w = 0; w < wc; w++) {
        int b = ws + w;
        for (size_t i = 0; i < L2_WAY_U64; i += 8) {
            acc ^= dyn_l2_banks[b][i];
        }
    }
    bench_phase_sync(cid, 4);

    /* PHASE 4: Medium 2-Core (Cores 0 & 1 use 4 ways each = 8 L2 ways; Cores 2 & 3 in L1) */
    if (cid < 2) {
        int m_start = cid * 4;
        for (int pass = 0; pass < 4; pass++) {
            for (size_t i = 0; i < L2_WAY_U64; i += 8) {
                uint64_t s = dyn_l2_banks[m_start + 0][i]
                           + dyn_l2_banks[m_start + 1][i]
                           + dyn_l2_banks[m_start + 2][i]
                           + dyn_l2_banks[m_start + 3][i];
                dyn_l2_banks[m_start + (pass & 3)][i] = s;
                acc += s;
            }
        }
    } else {
        for (int pass = 0; pass < 16; pass++) {
            for (int i = 0; i < 512; i += 8) {
                acc += dyn_l1_local[cid][i];
            }
        }
    }

    return acc;
}
