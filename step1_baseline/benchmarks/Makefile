# Makefile for Gem 5 x CVA6 — 12 4-Core RISC-V Benchmarks (Group A: 7 Standard + Group B: 5 Custom L2)

RISCV_PREFIX ?= $(shell command -v riscv64-unknown-elf-gcc >/dev/null 2>&1 && echo riscv64-unknown-elf- || echo ../../../tools/riscv64-gnu-toolchain/bin/riscv64-unknown-elf-)
CC      := $(RISCV_PREFIX)gcc
OBJDUMP := $(RISCV_PREFIX)objdump
SIZE    := $(RISCV_PREFIX)size

# Compile as 32-bit aligned RV64IM + Zicsr so both Verilator RTL and gem5 execute identical machine code
CFLAGS  := -O2 -march=rv64im_zicsr -mabi=lp64 -mcmodel=medany -fno-builtin -ffreestanding -nostdlib -Wall -Wextra -I.
LDFLAGS := -T common/link_4core.ld -nostdlib -static -Wl,--no-warn-rwx-segments

BENCHMARKS := \
	bm01_coremark \
	bm02_dhrystone \
	bm03_matmul \
	bm04_spmv \
	bm05_qsort_rsort \
	bm06_vvadd \
	bm07_memcpy \
	bm08_l2_light_1core \
	bm09_l2_medium_2cores \
	bm10_l2_heavy_4cores \
	bm11_l2_stream_mix \
	bm12_l2_dynamic_4phases

BUILD_DIR := build
ELFS := $(patsubst %,$(BUILD_DIR)/%.elf,$(BENCHMARKS))

.PHONY: all clean size

all: $(BUILD_DIR) $(ELFS) size

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(BUILD_DIR)/%.elf: %.c common/crt0_4core.S common/syscalls_4core.c common/bench_4core.h common/link_4core.ld
	$(CC) $(CFLAGS) common/crt0_4core.S common/syscalls_4core.c $< $(LDFLAGS) -o $@
	$(OBJDUMP) -d $@ > $@.dump

size: $(ELFS)
	$(SIZE) $(ELFS)

clean:
	rm -rf $(BUILD_DIR)/*
