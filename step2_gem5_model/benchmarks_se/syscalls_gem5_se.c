#include "common/bench_4core.h"

volatile uint64_t core_done[NUM_CORES] __attribute__((aligned(64))) = {0};
volatile uint64_t core_checksum[NUM_CORES] __attribute__((aligned(64))) = {0};
volatile uint64_t core_phase[NUM_CORES] __attribute__((aligned(64))) = {0};
volatile uint64_t final_result __attribute__((aligned(64))) = 0;

static inline void se_exit_thread(int code) {
    register long a0 __asm__("a0") = code;
    register long a7 __asm__("a7") = 93; /* SYS_exit */
    __asm__ volatile ("ecall" :: "r"(a0), "r"(a7) : "memory");
}

static inline void se_exit_group(int code) {
    register long a0 __asm__("a0") = code;
    register long a7 __asm__("a7") = 94; /* SYS_exit_group */
    __asm__ volatile ("ecall" :: "r"(a0), "r"(a7) : "memory");
}

void bench_phase_sync(int cid, int phase_id) {
    bench_barrier();
    core_phase[cid] = (uint64_t)phase_id;
    bench_barrier();
    while (1) {
        int all_reached = 1;
        for (int c = 0; c < NUM_CORES; c++) {
            if (core_phase[c] < (uint64_t)phase_id) {
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

void worker_entry(int cid) {
    uint64_t csum = run_benchmark_core(cid);
    bench_barrier();
    core_checksum[cid] = csum;
    bench_barrier();
    core_done[cid] = 1;
    bench_barrier();
    se_exit_thread(0);
}

void core0_entry(int cid) {
    uint64_t csum = run_benchmark_core(cid);
    bench_barrier();
    core_checksum[0] = csum;
    bench_barrier();
    core_done[0] = 1;
    bench_barrier();

    while (!core_done[1] || !core_done[2] || !core_done[3]) {
        /* Wait for worker cores 1..3 */
    }
    uint64_t total_csum = core_checksum[0]
                        ^ (core_checksum[1] << 1)
                        ^ (core_checksum[2] << 2)
                        ^ (core_checksum[3] << 3);
    final_result = (total_csum << 1) | 1ULL;
    bench_barrier();
    se_exit_group(0);
}
