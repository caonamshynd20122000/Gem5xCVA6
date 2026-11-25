/*
 * bm08_l2_light_1core.c — 4-Core L2 Light Load (1 Core uses 96 KiB = 3 L2 Ways; 3 Cores stay in L1)
 * - Shared L2 is 512 KiB, 16-Way (32 KiB per Way).
 * - Core 0 repeatedly accesses 3 congruent 32 KiB banks (96 KiB = 3 L2 ways).
 * - Cores 1, 2, 3 execute compute + small 4 KiB L1-resident buffer (never missing L1 after warmup).
 * - Target for Way-Shutdown: Only ~4/16 L2 ways needed; 12/16 ways can be power-gated!
 */
#include "common/bench_4core.h"

#define ACTIVE_WAYS_C0 3
static uint64_t c0_l2_banks[ACTIVE_WAYS_C0][L2_WAY_U64] __attribute__((aligned(32768)));
static uint64_t l1_small[NUM_CORES][512] __attribute__((aligned(4096))); /* 4 KiB per core */

uint64_t run_benchmark_core(int cid) {
    uint64_t acc = 0x12345678ULL + (uint64_t)cid;

    if (cid == 0) {
        for (int w = 0; w < ACTIVE_WAYS_C0; w++) {
            for (size_t i = 0; i < L2_WAY_U64; i += 8) {
                c0_l2_banks[w][i] = (uint64_t)(w * 1000 + i);
            }
        }
        for (int pass = 0; pass < 10; pass++) {
            /* Step by 8 uint64_t = 64B (1 L2 cache line) across all 512 sets */
            for (size_t i = 0; i < L2_WAY_U64; i += 8) {
                uint64_t s = c0_l2_banks[0][i] + c0_l2_banks[1][i] + c0_l2_banks[2][i];
                c0_l2_banks[pass % ACTIVE_WAYS_C0][i] = s ^ (uint64_t)pass;
                acc += s;
            }
        }
    } else {
        for (int i = 0; i < 512; i++) {
            l1_small[cid][i] = (uint64_t)(i + cid * 77);
        }
        for (int pass = 0; pass < 40; pass++) {
            for (int i = 0; i < 512; i += 8) {
                uint64_t v = l1_small[cid][i] * 3ULL + (uint64_t)pass;
                l1_small[cid][i] = v;
                acc ^= v;
            }
        }
    }
    return acc;
}
