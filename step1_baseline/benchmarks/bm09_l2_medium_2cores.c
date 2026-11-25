/*
 * bm09_l2_medium_2cores.c — 4-Core L2 Medium Load (2 Cores use 128 KiB/core = 8 L2 Ways; 2 Cores in L1)
 * - Cores 0 & 1 each repeatedly sweep 4 x 32 KiB banks (128 KiB/core = 256 KiB total = 8 L2 ways).
 * - Cores 2 & 3 stay inside their Private L1 D-Cache (4 KiB buffer).
 * - Target for Way-Shutdown: ~8/16 L2 ways active, 8/16 L2 ways power-gated (~50% L2 leakage saved).
 */
#include "common/bench_4core.h"

#define WAYS_PER_ACTIVE_CORE 4
static uint64_t med_l2_banks[2][WAYS_PER_ACTIVE_CORE][L2_WAY_U64] __attribute__((aligned(32768)));
static uint64_t med_l1_buf[NUM_CORES][512] __attribute__((aligned(4096)));

uint64_t run_benchmark_core(int cid) {
    uint64_t acc = 0xabcdef01ULL + (uint64_t)cid;

    if (cid < 2) {
        for (int w = 0; w < WAYS_PER_ACTIVE_CORE; w++) {
            for (size_t i = 0; i < L2_WAY_U64; i += 8) {
                med_l2_banks[cid][w][i] = (uint64_t)((cid + 1) * 500 + w * 97 + i);
            }
        }
        for (int pass = 0; pass < 8; pass++) {
            for (size_t i = 0; i < L2_WAY_U64; i += 8) {
                uint64_t s = med_l2_banks[cid][0][i]
                           + med_l2_banks[cid][1][i]
                           + med_l2_banks[cid][2][i]
                           + med_l2_banks[cid][3][i];
                med_l2_banks[cid][pass & 3][i] = s + (uint64_t)pass;
                acc += s;
            }
        }
    } else {
        for (int i = 0; i < 512; i++) {
            med_l1_buf[cid][i] = (uint64_t)(i * 11 + cid);
        }
        for (int pass = 0; pass < 36; pass++) {
            for (int i = 0; i < 512; i += 8) {
                uint64_t v = (med_l1_buf[cid][i] ^ (uint64_t)pass) + 7ULL;
                med_l1_buf[cid][i] = v;
                acc += v;
            }
        }
    }
    return acc;
}
