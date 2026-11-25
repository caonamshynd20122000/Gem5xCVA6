/*
 * bm10_l2_heavy_4cores.c — 4-Core L2 Heavy Load (All 4 Cores use 112-128 KiB/core = 14-15 L2 Ways!)
 * - Total 14 congruent 32 KiB banks (448 KiB = 14 L2 ways) actively shared/accessed by all 4 cores.
 * - Core 0: banks 0..3 (4 ways), Core 1: banks 4..7 (4 ways), Core 2: banks 8..10 (3 ways), Core 3: banks 11..13 (3 ways).
 * - Because each core's working set (96-128 KiB) exceeds its 32 KiB L1D, EVERY access misses L1D
 *   and hits in Shared L2 ONLY IF >= 14 L2 ways are active!
 * - High-Performance Test: Way-Shutdown MUST keep 14-16 ways ON to avoid severe L2 thrashing!
 */
#include "common/bench_4core.h"

#define TOTAL_HEAVY_WAYS 14
static uint64_t heavy_l2_banks[TOTAL_HEAVY_WAYS][L2_WAY_U64] __attribute__((aligned(32768)));

static const int core_way_start[NUM_CORES] = {0, 4, 8, 11};
static const int core_way_count[NUM_CORES] = {4, 4, 3, 3};

uint64_t run_benchmark_core(int cid) {
    int w_start = core_way_start[cid];
    int w_count = core_way_count[cid];

    for (int w = 0; w < w_count; w++) {
        int bank = w_start + w;
        for (size_t i = 0; i < L2_WAY_U64; i += 8) {
            heavy_l2_banks[bank][i] = (uint64_t)((bank + 1) * 131 + i);
        }
    }
    bench_phase_sync(cid, 1);

    uint64_t acc = 0;
    for (int pass = 0; pass < 8; pass++) {
        for (size_t i = 0; i < L2_WAY_U64; i += 8) {
            uint64_t s = 0;
            for (int w = 0; w < w_count; w++) {
                s += heavy_l2_banks[w_start + w][i];
            }
            heavy_l2_banks[w_start + (pass % w_count)][i] = s ^ (uint64_t)pass;
            acc += s;
        }
    }
    return acc;
}
