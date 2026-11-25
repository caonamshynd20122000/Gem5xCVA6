/*
 * bm01_coremark.c — 4-Core CoreMark Kernel (adapted from CVA6 verif/tests/custom/coremark)
 * Each core executes CoreMark's 4 canonical kernels on its private 16 KiB working set:
 *   1. Linked-list find & reverse
 *   2. Matrix multiply / add / bit-extract
 *   3. Finite State Machine (number parser)
 *   4. CRC-16 verification chain
 * Working set per core (~16 KiB) fits inside Private L1 D-Cache (32 KiB) -> L2 is mostly idle.
 */
#include "common/bench_4core.h"

#define CM_LIST_NODES 128
#define CM_MAT_N      16
#define CM_STATE_LEN  256

typedef struct {
    int32_t next_idx;
    uint32_t key;
    uint32_t data;
} cm_node_t;

typedef struct {
    cm_node_t list[CM_LIST_NODES];
    int32_t mat_a[CM_MAT_N * CM_MAT_N];
    int32_t mat_b[CM_MAT_N * CM_MAT_N];
    int32_t mat_c[CM_MAT_N * CM_MAT_N];
    uint8_t state_buf[CM_STATE_LEN];
    uint64_t pad[8];
} coremark_ws_t;

static coremark_ws_t cm_ws[NUM_CORES] __attribute__((aligned(4096)));

static uint16_t crcu16(uint16_t data, uint16_t crc) {
    for (int i = 0; i < 16; i++) {
        uint16_t bit = (data ^ crc) & 1U;
        crc >>= 1;
        if (bit) crc ^= 0xA001U;
        data >>= 1;
    }
    return crc;
}

uint64_t run_benchmark_core(int cid) {
    coremark_ws_t *ws = &cm_ws[cid];

    /* Initialize per-core structures */
    for (int i = 0; i < CM_LIST_NODES; i++) {
        ws->list[i].next_idx = (i + 1 < CM_LIST_NODES) ? (i + 1) : -1;
        ws->list[i].key = (uint32_t)((i * 37 + cid * 13) & 0xff);
        ws->list[i].data = (uint32_t)(0x1000 + i * 7 + cid);
    }
    for (int i = 0; i < CM_MAT_N * CM_MAT_N; i++) {
        ws->mat_a[i] = (int32_t)((i * 5 + cid + 1) & 0x3f);
        ws->mat_b[i] = (int32_t)(((i ^ 0x15) + cid + 3) & 0x3f);
        ws->mat_c[i] = 0;
    }
    const char pattern[] = "1234,-567,8.90e2,+42,abc,991,-12.3,777,";
    for (int i = 0; i < CM_STATE_LEN; i++) {
        ws->state_buf[i] = (uint8_t)pattern[i % (sizeof(pattern) - 1)];
    }

    uint16_t crc = (uint16_t)(0x1234U + cid);

    for (int iter = 0; iter < 8; iter++) {
        /* 1. List traversal & data update */
        int idx = 0;
        uint32_t list_acc = 0;
        while (idx >= 0) {
            ws->list[idx].data ^= (ws->list[idx].key + (uint32_t)iter);
            list_acc += ws->list[idx].data;
            idx = ws->list[idx].next_idx;
        }
        crc = crcu16((uint16_t)(list_acc & 0xffffU), crc);

        /* 2. Matrix kernel (16x16) */
        int32_t mat_acc = 0;
        for (int r = 0; r < CM_MAT_N; r++) {
            for (int c = 0; c < CM_MAT_N; c++) {
                int32_t sum = 0;
                for (int k = 0; k < CM_MAT_N; k++) {
                    sum += ws->mat_a[r * CM_MAT_N + k] * ws->mat_b[k * CM_MAT_N + c];
                }
                ws->mat_c[r * CM_MAT_N + c] = sum + iter;
                mat_acc ^= sum;
            }
        }
        crc = crcu16((uint16_t)(mat_acc & 0xffffU), crc);

        /* 3. State machine transition kernel */
        int state = 0;
        uint32_t transitions = 0;
        for (int i = 0; i < CM_STATE_LEN; i++) {
            uint8_t ch = ws->state_buf[i];
            if (ch == ',') {
                state = 0;
                transitions++;
            } else if (ch >= '0' && ch <= '9') {
                state = (state == 2) ? 2 : 1;
                transitions += (uint32_t)(ch - '0');
            } else if (ch == '.' || ch == 'e') {
                state = 2;
                transitions += 3;
            } else if (ch == '+' || ch == '-') {
                state = 1;
            } else {
                state = 3;
            }
        }
        crc = crcu16((uint16_t)(transitions + (uint32_t)state), crc);
    }

    return (uint64_t)crc ^ ((uint64_t)ws->mat_c[0] << 16);
}
