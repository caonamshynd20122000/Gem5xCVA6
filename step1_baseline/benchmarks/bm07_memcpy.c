/*
 * bm07_memcpy.c — 4-Core High-Bandwidth Memory Copy (adapted from riscv-tests mt-memcpy)
 * - Copies 32,768 x uint64_t (256 KiB src -> 256 KiB dst = 512 KiB total) across 4 cores.
 * - Heavy L1 Write-Through stream into L2 Write-Back (creates many dirty L2 lines).
 */
#include "common/bench_4core.h"

#define MEMCPY_N 32768 /* 256 KiB per array -> 512 KiB total */

static uint64_t mc_src[MEMCPY_N] __attribute__((aligned(4096)));
static uint64_t mc_dst[MEMCPY_N] __attribute__((aligned(4096)));

uint64_t run_benchmark_core(int cid) {
    int chunk = MEMCPY_N / NUM_CORES;
    int start = cid * chunk;
    int end = start + chunk;

    for (int i = start; i < end; i++) {
        mc_src[i] = ((uint64_t)i * 0x102030405ULL) ^ 0xa5a55a5aULL;
    }
    bench_phase_sync(cid, 1);

    for (int pass = 0; pass < 2; pass++) {
        for (int i = start; i < end; i += 4) {
            mc_dst[i + 0] = mc_src[i + 0] + (uint64_t)pass;
            mc_dst[i + 1] = mc_src[i + 1] + (uint64_t)pass;
            mc_dst[i + 2] = mc_src[i + 2] + (uint64_t)pass;
            mc_dst[i + 3] = mc_src[i + 3] + (uint64_t)pass;
        }
    }

    uint64_t csum = 0;
    for (int i = start; i < end; i += 16) {
        csum ^= mc_dst[i];
    }
    return csum;
}
