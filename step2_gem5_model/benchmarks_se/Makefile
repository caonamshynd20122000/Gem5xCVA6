RISCV_PREFIX ?= $(shell command -v riscv64-unknown-elf-gcc >/dev/null 2>&1 && echo riscv64-unknown-elf- || echo ../../../tools/riscv64-gnu-toolchain/bin/riscv64-unknown-elf-)
CC := $(RISCV_PREFIX)gcc
STEP1_SRC := ../../step1_baseline/benchmarks
CFLAGS := -O2 -march=rv64im_zicsr -mabi=lp64 -mcmodel=medany -nostdlib -nostartfiles -ffreestanding -I$(STEP1_SRC)
LDFLAGS := -T link_gem5_se.ld -Wl,--no-warn-rwx-segments

BUILD_DIR := build

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

ELFS := $(addprefix $(BUILD_DIR)/,$(addsuffix .elf,$(BENCHMARKS)))

all: $(BUILD_DIR) $(ELFS)

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(BUILD_DIR)/%.elf: $(STEP1_SRC)/%.c crt0_gem5_se.S syscalls_gem5_se.c link_gem5_se.ld
	$(CC) $(CFLAGS) $(LDFLAGS) crt0_gem5_se.S syscalls_gem5_se.c $< -o $@

clean:
	rm -rf $(BUILD_DIR)

.PHONY: all clean
