# Makefile for Verilator Compilation of 4-Core CVA6 + 16-Way Shared L2 RTL Baseline

VERILATOR ?= /usr/local/bin/verilator
TOP_MOD   := cva6_4core_soc_top
RTL_SRCS  := cva6_4core_l2_pkg.sv cva6_shared_l2_16way.sv cva6_core_tile_l1.sv cva6_4core_soc_top.sv
CPP_SRC   := sim_main.cpp
OBJ_DIR   := obj_dir
SIM_BIN   := $(OBJ_DIR)/V$(TOP_MOD)

.PHONY: all clean

all: $(SIM_BIN)

$(SIM_BIN): $(RTL_SRCS) $(CPP_SRC)
	$(VERILATOR) --cc --exe --build -j 2 \
		-O3 -CFLAGS "-O3 -std=c++17" \
		-Wno-WIDTHTRUNC -Wno-WIDTHEXPAND -Wno-UNUSEDSIGNAL -Wno-UNUSEDPARAM \
		--top-module $(TOP_MOD) \
		$(RTL_SRCS) $(CPP_SRC)

clean:
	rm -rf $(OBJ_DIR)
