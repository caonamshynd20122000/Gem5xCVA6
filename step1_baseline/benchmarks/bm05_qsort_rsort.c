/*
 * bm05_qsort_rsort.c — 4-Core Sorting (QuickSort + RadixSort, adapted from riscv-tests qsort & rsort)
 * - Each core sorts an 80 KiB array (10,240 x uint64_t -> 320 KiB total across 4 cores = 10 L2 ways).
 * - Cores 0 & 1 run iterative QuickSort; Cores 2 & 3 run 8-bit LSD RadixSort (with scratch buffer).
 * - Generates heavy store traffic from L1 Write-Through into Shared L2 Write-Back (dirty lines!).
 */
#include "common/bench_4core.h"

#define SORT_ELEMS_PER_CORE 4096 /* 4096 * 8B = 32 KiB primary + 32 KiB scratch = 64 KiB/core (256 KiB total) */

static uint64_t sort_arr[NUM_CORES][SORT_ELEMS_PER_CORE] __attribute__((aligned(4096)));
static uint64_t sort_tmp[NUM_CORES][SORT_ELEMS_PER_CORE] __attribute__((aligned(4096)));

static void iterative_qsort(uint64_t *a, int n) {
    int stack_l[64], stack_r[64];
    int top = 0;
    stack_l[top] = 0;
    stack_r[top] = n - 1;

    while (top >= 0) {
        int l = stack_l[top];
        int r = stack_r[top--];
        while (l < r) {
            uint64_t pivot = a[(l + r) >> 1];
            int i = l, j = r;
            while (i <= j) {
                while (a[i] < pivot) i++;
                while (a[j] > pivot) j--;
                if (i <= j) {
                    uint64_t t = a[i];
                    a[i] = a[j];
                    a[j] = t;
                    i++;
                    j--;
                }
            }
            if (j - l < r - i) {
                if (i < r && top < 62) {
                    stack_l[++top] = i;
                    stack_r[top] = r;
                }
                r = j;
            } else {
                if (l < j && top < 62) {
                    stack_l[++top] = l;
                    stack_r[top] = j;
                }
                l = i;
            }
        }
    }
}

static void radix_sort_u16(uint64_t *a, uint64_t *tmp, int n) {
    uint32_t count[256];
    for (int shift = 0; shift < 16; shift += 8) {
        for (int b = 0; b < 256; b++) count[b] = 0;
        for (int i = 0; i < n; i++) {
            count[(a[i] >> shift) & 0xffU]++;
        }
        uint32_t total = 0;
        for (int b = 0; b < 256; b++) {
            uint32_t c = count[b];
            count[b] = total;
            total += c;
        }
        for (int i = 0; i < n; i++) {
            uint32_t bucket = (uint32_t)((a[i] >> shift) & 0xffU);
            tmp[count[bucket]++] = a[i];
        }
        for (int i = 0; i < n; i++) {
            a[i] = tmp[i];
        }
    }
}

uint64_t run_benchmark_core(int cid) {
    uint64_t *a = sort_arr[cid];
    uint64_t *tmp = sort_tmp[cid];
    uint64_t seed = 0x9e3779b97f4a7c15ULL ^ ((uint64_t)(cid + 1) * 0x1234567ULL);

    for (int i = 0; i < SORT_ELEMS_PER_CORE; i++) {
        seed ^= seed << 13;
        seed ^= seed >> 7;
        seed ^= seed << 17;
        a[i] = seed & 0xffffULL;
        tmp[i] = 0;
    }

    if ((cid & 1) == 0) {
        iterative_qsort(a, SORT_ELEMS_PER_CORE);
    } else {
        radix_sort_u16(a, tmp, SORT_ELEMS_PER_CORE);
    }

    uint64_t csum = 0;
    for (int i = 0; i < SORT_ELEMS_PER_CORE; i += 8) {
        csum = (csum * 131ULL) + a[i];
    }
    return csum;
}
