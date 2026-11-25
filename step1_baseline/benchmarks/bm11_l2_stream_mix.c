/*
 * bm11_l2_stream_mix.c — 4-Core L2 Cache-Sensitive + Streaming Interference Mix
 * - Cores 0 & 1 repeatedly access a hot 64 KiB working set per core (2 L2 ways/core = 4 L2 ways total).
 * - Cores 2 & 3 stream sequentially through a 512 KiB buffer per core (1 MB total, zero temporal reuse).
 * - Smart Policy Differentiator:
 *   - Naive Miss-Rate policy sees high L2 misses from Cores 2 & 3 and turns all 16 L2 ways ON (wasting power).
 *   - Core-Aware / Sampled-Set ATD policy recognizes only 4-6 ways provide marginal hits and gates 10-12 ways!
 */
#include "common/bench_4core.h"

#define HOT_WAYS_PER_CORE 2
#define STREAM_U64_PER_CORE (16 * L2_WAY_U64) /* 512 KiB per streaming core = 1 MB total */

static uint64_t hot_l2[2][HOT_WAYS_PER_CORE][L2_WAY_U64] __attribute__((aligned(32768)));
static uint64_t stream_buf[2][STREAM_U64_PER_CORE] __attribute__((aligned(32768)));

uint64_t run_benchmark_core(int cid) {
    uint64_t acc = 0;

    if (cid < 2) {
        /* Cores 0 & 1: High-reuse 64 KiB L2 working set (2 L2 ways each = 4 ways total) */
        for (int w = 0; w < HOT_WAYS_PER_CORE; w++) {
            for (size_t i = 0; i < L2_WAY_U64; i += 8) {
                hot_l2[cid][w][i] = (uint64_t)(cid * 911 + w * 43 + i);
            }
        }
        for (int pass = 0; pass < 10; pass++) {
            for (size_t i = 0; i < L2_WAY_U64; i += 8) {
                uint64_t s = hot_l2[cid][0][i] + hot_l2[cid][1][i] + (uint64_t)pass;
                hot_l2[cid][pass & 1][i] = s;
                acc += s;
            }
        }
    } else {
        /* Cores 2 & 3: Non-reusable 512 KiB streaming scan */
        int sc = cid - 2;
        for (size_t i = 0; i < STREAM_U64_PER_CORE; i += 8) {
            stream_buf[sc][i] = (uint64_t)(i * 7 + sc + 1);
        }
        bench_barrier();
        for (size_t i = 0; i < STREAM_U64_PER_CORE; i += 8) {
            uint64_t v = stream_buf[sc][i] + (uint64_t)(sc + 3);
            stream_buf[sc][i] = v;
            acc ^= v;
        }
    }
    return acc;
}
