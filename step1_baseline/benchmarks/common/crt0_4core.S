.section .text.init
.globl _start
_start:
    .option push
    .option norelax
    la gp, __global_pointer$
    .option pop

    /* Read core ID (mhartid = 0..3) and set 16 KiB per-core stack */
    csrr a0, mhartid
    la t0, __stack_top
    slli t1, a0, 14
    sub sp, t0, t1

    /* Core 0 clears .bss and releases Cores 1..3 */
    bnez a0, wait_bss

    la t0, __bss_start
    la t1, __bss_end
1:
    bgeu t0, t1, 2f
    sd zero, 0(t0)
    addi t0, t0, 8
    j 1b
2:
    fence
    la t0, boot_ready
    li t1, 1
    amoswap.d.rl zero, t1, (t0)
    fence
    j run_core

wait_bss:
    la t0, boot_ready
3:
    amoor.d.aq t1, zero, (t0)
    beqz t1, 3b
    fence

run_core:
    call core_entry
4:
    wfi
    j 4b
