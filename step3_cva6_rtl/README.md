# Step 3: OpenHW CVA6 Shared L2 Way-Shutdown RTL (`atd_dirty_aware`)

SystemVerilog RTL implementation of the `atd_dirty_aware` dynamic way-shutdown 512 KiB, 16-way, write-back shared L2 cache integrated into the 4-core OpenHW CVA6 cluster (`fpga_linux_cv64a6`) via AXI4.

## Architecture & RTL Modules

- `rtl/l2_way_shutdown_ctrl.sv`: Sampled-Set ATD (16/512 sets, 16-way LRU stack, write-through MRU burst filter), Epoch Decision Engine (2048 accesses, 98.5% hit retention), Fast-Wakeup Miss-Spike Detector (`>= 24` misses per 256 accesses wakes `+4` ways immediately), Miss-Rate Shutdown Guard (`<= 2.5%` epoch miss rate), Dirty-Flush Cost Guard (`<= 96` dirty lines), and Power-Gating / Wakeup FSM (`T_wakeup = 6 cycles`).
- `rtl/cva6_shared_l2_16way_ws.sv`: 512 KiB, 16-way, 64B-line write-back shared L2 cache with per-way dirty counters, dynamic `way_en_i[15:0]` masking, and a background dirty-way flush engine.
- `rtl/axi_l2_wb_wrap.sv`: 64-bit AXI4 wrapper instantiating `cva6_shared_l2_16way_ws` and `l2_way_shutdown_ctrl` between the 4-core `axi_xbar` and `i_axi2mem` inside `cva6/corev_apu/tb/ariane_testharness.sv` (runtime selectable via `+WS_EN=0` baseline vs `+WS_EN=1` `atd_dirty_aware`).
- `rtl/cva6_l2_pkg.sv`: Shared L2 cache geometry and type definitions.
- `scripts/run_step3_rtl_eval.sh`: Rebuilds the 4-core OpenHW CVA6 Verilator binary (`cva6/work-ver-l2-4core/Variane_testharness`), runs all 12 benchmarks with `+WS_EN=1`, and generates the 3-way validation report.
- `scripts/compare_3way_report.py`: Verifies 12/12 bit-exact checksum match against Step 1 and compares Step 1 Baseline RTL, Step 2 gem5 Model, and Step 3 Custom RTL using CACTI 7.0 (22nm) power/energy metrics.

## 3-Way Summary (12 Benchmarks)

| Configuration | Avg Active Ways (/16) | 4-Core IPC Change (%) | L2 Leakage Saving (%) | Shutdown Dirty Flushes | Avg EDP Change (%) |
| :--- | ---: | ---: | ---: | ---: | ---: |
| Step 1: OpenHW CVA6 RTL Baseline (16-way) | 16.00 | +0.00% | 0.00% | 0 | +0.00% |
| Step 2: gem5 Model (`atd_dirty_aware`) | 11.10 | -0.28% | 24.67% | 157 | +20.24% |
| Step 3: OpenHW CVA6 RTL (`atd_dirty_aware`) | 12.54 | -0.03% | 17.43% | 345 | +15.67% |

- Functional verification: **12/12 PASS** (all 4-core checksums match Step 1 baseline).

## How to Run

```bash
./step3_cva6_rtl/scripts/run_step3_rtl_eval.sh
```

Results are written to:
- `step3_cva6_rtl/results/step3_3way_comparison.md`
- `step3_cva6_rtl/results/step3_rtl_summary.csv`
- `step3_cva6_rtl/results/step3_3way_comparison.png`
