/*
 * bm04_spmv.c — 4-Core CSR Sparse Matrix-Vector Multiply (adapted from riscv-tests/benchmarks/spmv)
 * - Sparse matrix in CSR format: 1024 rows, 16 non-zeros/row = 16,384 non-zeros.
 * - val[16384] (128 KiB) + col_idx[16384] (64 KiB) + x[4096] (32 KiB) + y[1024] (8 KiB) = ~232 KiB.
 * - Indirect lookups x[col_idx[k]] spill out of L1D (32 KiB) and stress Shared L2 (~8-10 ways).
 */
#include "common/bench_4core.h"

#define SPMV_ROWS      1024
#define SPMV_NNZ_ROW   16
#define SPMV_NNZ       (SPMV_ROWS * SPMV_NNZ_ROW) /* 16384 */
#define SPMV_VEC_LEN   4096                       /* 32 KiB vector x */

static int64_t spmv_val[SPMV_NNZ] __attribute__((aligned(4096)));
static uint32_t spmv_col[SPMV_NNZ] __attribute__((aligned(4096)));
static int64_t spmv_x[SPMV_VEC_LEN] __attribute__((aligned(4096)));
static int64_t spmv_y[SPMV_ROWS] __attribute__((aligned(4096)));

uint64_t run_benchmark_core(int cid) {
    int rows_per_core = SPMV_ROWS / NUM_CORES;
    int r_start = cid * rows_per_core;
    int r_end = r_start + rows_per_core;

    /* Parallel CSR matrix and vector initialization */
    for (int i = cid * (SPMV_VEC_LEN / NUM_CORES); i < (cid + 1) * (SPMV_VEC_LEN / NUM_CORES); i++) {
        spmv_x[i] = (int64_t)((i * 19 + 7) & 0xff);
    }
    for (int r = r_start; r < r_end; r++) {
        int base = r * SPMV_NNZ_ROW;
        for (int k = 0; k < SPMV_NNZ_ROW; k++) {
            spmv_val[base + k] = (int64_t)(((r + k * 11) & 0x3f) + 1);
            /* Spread column indices across 32 KiB vector x to induce L1 misses into Shared L2 */
            spmv_col[base + k] = (uint32_t)((r * 3 + k * 251) & (SPMV_VEC_LEN - 1));
        }
        spmv_y[r] = 0;
    }
    bench_phase_sync(cid, 1);

    /* Execute 3 SpMV passes */
    uint64_t csum = 0;
    for (int pass = 0; pass < 3; pass++) {
        for (int r = r_start; r < r_end; r++) {
            int base = r * SPMV_NNZ_ROW;
            int64_t sum = 0;
            for (int k = 0; k < SPMV_NNZ_ROW; k++) {
                sum += spmv_val[base + k] * spmv_x[spmv_col[base + k]];
            }
            spmv_y[r] = sum + pass;
            csum ^= (uint64_t)sum;
        }
    }
    return csum;
}
