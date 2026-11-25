OUTPUT_ARCH("riscv")
ENTRY(_start)

SECTIONS
{
    . = 0x00010000;
    .text : {
        *(.text.init)
        *(.text .text.*)
    }
    . = ALIGN(4096);
    .rodata : {
        *(.rodata .rodata.*)
        *(.srodata .srodata.*)
    }
    . = ALIGN(4096);
    .data : {
        *(.data .data.*)
        *(.sdata .sdata.*)
    }
    PROVIDE(__global_pointer$ = . + 0x800);
    . = ALIGN(4096);
    .bss : {
        __bss_start = .;
        *(.sbss .sbss.*)
        *(.bss .bss.*)
        *(COMMON)
        . = ALIGN(64);
        __bss_end = .;
    }
    _end = .;
}
