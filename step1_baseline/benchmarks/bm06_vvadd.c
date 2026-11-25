/*
 * bm06_vvadd.c — 4-Core Parallel Vector-Vector Addition (adapted from riscv-tests mt-vvadd)
 * - 3 vectors (A, B, C) of 24,576 x uint64_t (192 KiB per vector = 576 KiB total > 512 KiB L2).
 * - High memory bandwidth streaming across all 4 cores with low temporal reuse.
 */
#include "common/bench_4core.h"

#define VVADD_N 24576 /* 24576 * 8B = 192 KiB per array -> 576 KiB total */

static uint64_t vv_a[VVADD_N] __attribute__((aligned(4096)));
static uint64_t vv_b[VVADD_N] __attribute__((aligned(4096)));
static uint64_t vv_c[VVADD_N] __attribute__((aligned(4096)));

uint64_t run_benchmark_core(int cid) {
    int chunk = VVADD_N / NUM_CORES;
    int start = cid * chunk;
    int end = start + chunk;

    for (int i = start; i < end; i++) {
        vv_a[i] = (uint64_t)i * 3ULL + 1ULL;
        vv_b[i] = (uint64_t)(i ^ 0x5a5a) * 7ULL;
    }
    bench_phase_sync(cid, 1);

    uint64_t csum = 0;
    for (int pass = 0; pass < 2; pass++) {
        for (int i = start; i < end; i++) {
            uint64_t v = vv_a[i] + vv_b[i] + (uint64_t)pass;
            vv_c[i] = v;
            csum += v;
        }
    }
    return csum;
}
