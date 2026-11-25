OUTPUT_ARCH("riscv")
ENTRY(_start)

SECTIONS
{
  . = 0x80000000;
  .text.init : { *(.text.init) }
  . = ALIGN(0x1000);
  .tohost : { *(.tohost) }
  . = ALIGN(0x1000);
  .text : { *(.text .text.*) }
  . = ALIGN(64);
  .rodata : { *(.rodata .rodata.*) }
  . = ALIGN(64);
  .data : {
    __global_pointer$ = . + 0x800;
    *(.sdata .sdata.*)
    *(.data .data.*)
  }
  . = ALIGN(4096);
  __bss_start = .;
  .bss : {
    *(.sbss .sbss.*)
    *(.bss .bss.*)
    *(COMMON)
  }
  . = ALIGN(64);
  __bss_end = .;
  . = ALIGN(0x1000);
  . += 0x10000; /* 64 KiB total stack (16 KiB x 4 cores) */
  __stack_top = .;
  _end = .;
}
