#ifndef GEM5_CVA6_BENCH_4CORE_H
#define GEM5_CVA6_BENCH_4CORE_H

#include <stdint.h>
#include <stddef.h>

#define NUM_CORES 4

/* L2 Cache Geometry: 512 KiB, 16-Way, 64B Line -> 512 Sets, 32 KiB per Way */
#define L2_SIZE_BYTES      (512 * 1024)
#define L2_NUM_WAYS        16
#define L2_LINE_BYTES      64
#define L2_NUM_SETS        512
#define L2_WAY_BYTES       (32 * 1024)
#define L2_WAY_U64         (L2_WAY_BYTES / sizeof(uint64_t)) /* 4096 uint64_t per way */

static inline uint64_t bench_hartid(void) {
    uint64_t val = 0;
    __asm__ volatile ("csrr %0, mhartid" : "=r"(val));
    return val;
}

static inline uint64_t bench_rdcycle(void) {
    uint64_t val = 0;
    __asm__ volatile ("csrr %0, mcycle" : "=r"(val));
    return val;
}

static inline uint64_t bench_rdinstret(void) {
    uint64_t val = 0;
    __asm__ volatile ("csrr %0, minstret" : "=r"(val));
    return val;
}

static inline void bench_barrier(void) {
    __asm__ volatile ("fence" ::: "memory");
}

/* Synchronize all 4 cores at a phase boundary */
void bench_phase_sync(int cid, int phase_id);

/* Implemented by each benchmark: executed in parallel on Core 0, 1, 2, 3 */
uint64_t run_benchmark_core(int cid);

#endif /* GEM5_CVA6_BENCH_4CORE_H */
