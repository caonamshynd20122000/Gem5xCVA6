#include "bench_4core.h"

/* Single HTIF tohost symbol at 0x8000_1000: bit 0 = PASS (1), bits [63:1] = 4-core combined checksum */
volatile uint64_t tohost __attribute__((section(".tohost"), aligned(64))) = 0;

volatile uint64_t boot_ready __attribute__((aligned(64))) = 0;
volatile uint64_t core_done[NUM_CORES] __attribute__((aligned(64))) = {0};
volatile uint64_t core_checksum[NUM_CORES] __attribute__((aligned(64))) = {0};
volatile uint64_t core_phase[NUM_CORES] __attribute__((aligned(64))) = {0};

/* Coherent cross-core load/store using RISC-V AMO (bypasses private L1D via axi_riscv_atomics) */
static inline uint64_t amo_load_u64(volatile uint64_t *ptr) {
    uint64_t val;
    __asm__ volatile ("amoor.d.aq %0, zero, (%1)" : "=r"(val) : "r"(ptr) : "memory");
    return val;
}

static inline void amo_store_u64(volatile uint64_t *ptr, uint64_t val) {
    __asm__ volatile ("amoswap.d.rl zero, %0, (%1)" :: "r"(val), "r"(ptr) : "memory");
}

void bench_phase_sync(int cid, int phase_id) {
    bench_barrier();
    amo_store_u64(&core_phase[cid], (uint64_t)phase_id);
    while (1) {
        int all_reached = 1;
        for (int c = 0; c < NUM_CORES; c++) {
            if (amo_load_u64(&core_phase[c]) < (uint64_t)phase_id) {
                all_reached = 0;
                break;
            }
        }
        if (all_reached) {
            break;
        }
    }
    bench_barrier();
}

void core_entry(int cid) {
    uint64_t csum = run_benchmark_core(cid);
    bench_barrier();
    amo_store_u64(&core_checksum[cid], csum);
    amo_store_u64(&core_done[cid], 1ULL);

    if (cid == 0) {
        while (!amo_load_u64(&core_done[1]) ||
               !amo_load_u64(&core_done[2]) ||
               !amo_load_u64(&core_done[3])) {
            /* Wait for worker cores 1..3 */
        }
        uint64_t total_csum = amo_load_u64(&core_checksum[0])
                            ^ (amo_load_u64(&core_checksum[1]) << 1)
                            ^ (amo_load_u64(&core_checksum[2]) << 2)
                            ^ (amo_load_u64(&core_checksum[3]) << 3);
        bench_barrier();
        /* Encode PASS (bit 0 = 1) + 63-bit combined checksum */
        amo_store_u64(&tohost, (total_csum << 1) | 1ULL);
    }

    while (1) {
        __asm__ volatile ("wfi");
    }
}
