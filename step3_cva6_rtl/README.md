# Step 3: CVA6 Shared L2 Way-Shutdown RTL (`atd_dirty_aware`)

SystemVerilog RTL implementation of the `atd_dirty_aware` way-shutdown L2 cache for the 4-core CVA6 cluster.

## Directory Layout

- `rtl/l2_way_shutdown_ctrl.sv`: Sampled-Set ATD (16/512 sets, 16-way LRU stack), Epoch Decision Engine (2048 accesses, streaming detector < 5%, 98.5% hit retention), Dirty-Flush Cost Guard (`<= 96` dirty lines), and Power-Gating / Wakeup FSM (`T_wakeup = 6 cycles`).
- `rtl/cva6_shared_l2_16way_ws.sv`: 512 KiB 16-Way Write-Back Shared L2 Cache enhanced with O(1) per-way dirty counters and a 16-set/cycle background Dirty-Way Flush Engine.
- `rtl/cva6_4core_soc_ws_top.sv`: Top-level 4-Core CVA6 cluster reusing `cva6_4core_l2_pkg.sv` and `cva6_core_tile_l1.sv` from Step 1 verbatim for fair comparison.
- `tb/sim_main_ws.cpp` & `tb/Makefile`: Verilator C++ testbench loading Step 1 RISC-V ELF64 binaries and computing cycle-accurate active ways and CACTI 7.0 (22nm) power/energy.
- `scripts/run_step3_rtl_eval.sh`: Compiles Verilator RTL, runs all 12 benchmarks, and generates the 3-way comparison report.
- `scripts/compare_3way_report.py`: Verifies 12/12 bit-exact checksum match against Step 1 and compares **Step 1 Baseline RTL vs Step 2 gem5 Model vs Step 3 Custom RTL**.

## How to Run

```bash
./step3_cva6_rtl/scripts/run_step3_rtl_eval.sh
```

Results are written to:
- `step3_cva6_rtl/results/step3_3way_comparison.md`
- `step3_cva6_rtl/results/step3_rtl_summary.csv`
- `step3_cva6_rtl/results/step3_3way_comparison.png`
