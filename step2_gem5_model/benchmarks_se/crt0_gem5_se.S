/*
 * crt0_gem5_se.S — 4-Core RV64 Linux SE-mode startup for gem5
 * Spawns Cores 1, 2, 3 via Linux SYS_clone (220) sharing the same address space
 * (CLONE_VM | CLONE_FS | CLONE_FILES | CLONE_SIGHAND | CLONE_THREAD = 0x00010f00),
 * then runs Core 0. No M-mode CSRs or wfi instructions.
 */
.section .text.init
.globl _start
_start:
    .option push
    .option norelax
    la gp, __global_pointer$
    .option pop

    /* Spawn worker threads for cid = 1, 2, 3 */
    li s0, 1
    li s1, 4
    la s2, worker_stacks

spawn_loop:
    /* child_stack = worker_stacks + s0 * 16384 (16 KiB per worker) */
    slli t0, s0, 14
    add a1, s2, t0

    /* SYS_clone(flags=0x00010f00, child_stack=a1, ptid=0, tls=0, ctid=0) */
    li a0, 0x00010f00
    li a2, 0
    li a3, 0
    li a4, 0
    li a7, 220
    ecall

    /* a0 == 0 in child thread -> jump to worker_entry(cid = s0) */
    beqz a0, is_worker

    addi s0, s0, 1
    blt s0, s1, spawn_loop

    /* Core 0 runs core0_entry(0) and terminates with SYS_exit_group */
    li a0, 0
    call core0_entry

    li a0, 0
    li a7, 94
    ecall

is_worker:
    mv a0, s0
    call worker_entry

    li a0, 0
    li a7, 93
    ecall

.section .bss
.align 12
worker_stacks:
    .space 65536
