/*
 * bm02_dhrystone.c — 4-Core Dhrystone Integer Benchmark (adapted from CVA6 verif/tests/custom/dhrystone)
 * Exercises integer arithmetic, record/struct manipulation, 2D array indexing, and string comparison
 * across all 4 CVA6 cores. Working set (~8 KiB/core) stays inside Private L1 D-Cache.
 */
#include "common/bench_4core.h"

#define DHRY_ITERS 60
#define ARR_DIM    16

typedef struct {
    int32_t discr;
    int32_t enum_comp;
    int32_t int_comp;
    char str_comp[32];
} dhry_rec_t;

typedef struct {
    dhry_rec_t rec_a;
    dhry_rec_t rec_b;
    int32_t arr1[ARR_DIM];
    int32_t arr2[ARR_DIM][ARR_DIM];
} dhry_ws_t;

static dhry_ws_t dhry_ws[NUM_CORES] __attribute__((aligned(4096)));

static void str_copy31(char *dst, const char *src) {
    for (int i = 0; i < 31; i++) {
        dst[i] = src[i];
        if (src[i] == '\0') break;
    }
    dst[31] = '\0';
}

static int str_cmp31(const char *a, const char *b) {
    for (int i = 0; i < 31; i++) {
        if (a[i] != b[i]) return (int)a[i] - (int)b[i];
        if (a[i] == '\0') return 0;
    }
    return 0;
}

static void proc_8(int32_t *arr1, int32_t arr2[ARR_DIM][ARR_DIM], int32_t v1, int32_t v2) {
    int32_t idx = (v1 + 5) & (ARR_DIM - 1);
    arr1[idx] = v2;
    arr1[(idx + 1) & (ARR_DIM - 1)] = arr1[idx];
    arr1[(idx + 3) & (ARR_DIM - 1)] = idx;
    for (int i = 0; i < 4; i++) {
        int r = (idx + i) & (ARR_DIM - 1);
        arr2[idx][r] = v1 + i;
    }
    arr2[idx][(idx - 1) & (ARR_DIM - 1)] += 1;
    arr2[(idx + 2) & (ARR_DIM - 1)][idx] = arr1[idx];
}

uint64_t run_benchmark_core(int cid) {
    dhry_ws_t *ws = &dhry_ws[cid];
    ws->rec_a.discr = 0;
    ws->rec_a.enum_comp = 2;
    ws->rec_a.int_comp = 40 + cid;
    str_copy31(ws->rec_a.str_comp, "DHRYSTONE PROGRAM, SOME STRING");

    for (int r = 0; r < ARR_DIM; r++) {
        ws->arr1[r] = r + cid;
        for (int c = 0; c < ARR_DIM; c++) {
            ws->arr2[r][c] = r * ARR_DIM + c;
        }
    }
    ws->arr2[2][3] = 10;

    int32_t int_1 = 2 + cid;
    int32_t int_2 = 3 + cid;
    int32_t int_3 = 0;
    uint64_t checksum = 0;

    for (int run = 1; run <= DHRY_ITERS; run++) {
        /* Record copy & update (Proc_1) */
        ws->rec_b = ws->rec_a;
        ws->rec_a.int_comp = 5 + (run & 7);
        ws->rec_b.int_comp = ws->rec_a.int_comp + int_1;

        /* String operations */
        char str1[32], str2[32];
        str_copy31(str1, "DHRYSTONE PROGRAM, 1'ST STRING");
        str_copy31(str2, "DHRYSTONE PROGRAM, 2'ND STRING");
        int cmp = str_cmp31(str1, str2);

        while (int_1 < int_2) {
            int_3 = 5 * int_1 - int_2;
            int_3 = (int_1 + int_2 + int_3) / 2;
            int_1 += 1;
        }

        proc_8(ws->arr1, ws->arr2, int_1, int_3 + cmp);
        int_2 = int_1 * ((run & 3) + 1);
        int_1 = run & 7;

        checksum += (uint64_t)(ws->rec_b.int_comp ^ ws->arr2[int_1 & 15][(int_3) & 15]);
    }

    return checksum;
}
