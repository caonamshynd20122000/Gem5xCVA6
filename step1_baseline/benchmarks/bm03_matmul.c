/*
 * bm03_matmul.c — 4-Core Parallel Blocked Matrix Multiplication (adapted from riscv-tests mt-matmul)
 * - Matrices A, B, C of size 96 x 96 x int64_t (72 KiB per matrix -> 216 KiB total).
 * - Total working set (216 KiB) exceeds Private L1D (32 KiB) and occupies ~7 ways of Shared L2 (512 KiB).
 * - Each of the 4 CVA6 cores computes 24 rows of C = A * B with high spatial & temporal reuse in L2.
 */
#include "common/bench_4core.h"

#define MAT_N 96 /* 96 * 96 * 8B = 73,728 B (~72 KiB) per matrix -> 216 KiB total (~7 L2 ways) */

static int64_t mat_a[MAT_N * MAT_N] __attribute__((aligned(4096)));
static int64_t mat_b[MAT_N * MAT_N] __attribute__((aligned(4096)));
static int64_t mat_c[MAT_N * MAT_N] __attribute__((aligned(4096)));

uint64_t run_benchmark_core(int cid) {
    int rows_per_core = MAT_N / NUM_CORES;
    int r_start = cid * rows_per_core;
    int r_end = r_start + rows_per_core;

    /* Parallel initialization of A and B */
    for (int r = r_start; r < r_end; r++) {
        for (int c = 0; c < MAT_N; c++) {
            mat_a[r * MAT_N + c] = (int64_t)((r * 13 + c * 7 + 3) & 0x7f);
            mat_b[r * MAT_N + c] = (int64_t)(((r ^ c) * 5 + 1) & 0x7f);
            mat_c[r * MAT_N + c] = 0;
        }
    }
    bench_phase_sync(cid, 1);

    /* Blocked matrix multiplication (tile = 12) */
    const int B = 12;
    for (int kk = 0; kk < MAT_N; kk += B) {
        for (int jj = 0; jj < MAT_N; jj += B) {
            for (int i = r_start; i < r_end; i++) {
                for (int k = kk; k < kk + B; k++) {
                    int64_t a_ik = mat_a[i * MAT_N + k];
                    for (int j = jj; j < jj + B; j++) {
                        mat_c[i * MAT_N + j] += a_ik * mat_b[k * MAT_N + j];
                    }
                }
            }
        }
    }

    uint64_t csum = 0;
    for (int i = r_start; i < r_end; i++) {
        for (int j = 0; j < MAT_N; j += 4) {
            csum ^= (uint64_t)mat_c[i * MAT_N + j] + (uint64_t)(i * MAT_N + j);
        }
    }
    return csum;
}
