# Makefile for Verilator Compilation of Step 3:
# 4-Core CVA6 + 16-Way Shared L2 + atd_dirty_aware Way-Shutdown RTL

VERILATOR ?= /usr/local/bin/verilator
TOP_MOD   := cva6_4core_soc_ws_top
STEP1_RTL := ../../step1_baseline/cva6_l2_rtl_baseline
STEP3_RTL := ../rtl

RTL_SRCS  := \
	$(STEP1_RTL)/cva6_4core_l2_pkg.sv \
	$(STEP1_RTL)/cva6_core_tile_l1.sv \
	$(STEP3_RTL)/l2_way_shutdown_ctrl.sv \
	$(STEP3_RTL)/cva6_shared_l2_16way_ws.sv \
	$(STEP3_RTL)/cva6_4core_soc_ws_top.sv

CPP_SRC   := sim_main_ws.cpp
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
