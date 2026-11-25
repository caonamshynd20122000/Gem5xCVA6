# Step 2: gem5 Model — 4-Core OpenHW CVA6 + 512 KiB 16-Way Write-Back Shared L2 Way-Shutdown

## Calibrated System Parameters (`configs/cva6_4core_l2_way_shutdown.py`)

Aligned with OpenHW CVA6 (`fpga_linux_cv64a6`):
- 4x `RiscvMinorCPU` (1 GHz, 1-issue, 2-commit, 16-entry ITLB & DTLB, BTB=32, BHT=128, RAS=2)
- Private L1I (16 KiB, 4-way) and Private L1D (32 KiB, 8-way, 8 write buffers)
- 64-bit `L2XBar` and `SystemXBar` (`width=8`, matching 64-bit `axi_xbar`)
- Shared L2 (512 KiB, 16-way, 64B line, write-back, 4-cycle hit, LRU replacement, `WayShutdownSetAssoc`)
- DRAM (`latency=28ns`, `bandwidth=8GB/s`, `0.650 nJ` per 64B access)

## Layout

- `src/way_shutdown_tags.{hh,cc}`: `WayShutdownSetAssoc` inheriting `gem5::BaseSetAssoc` (`static`, `selective_ways`, `way_util`, `atd_dirty_aware`).
- `src/apply_gem5_patch.py`: Copies `way_shutdown_tags.{hh,cc}` into `gem5/src/mem/cache/tags/` and registers the SimObject in `Tags.py` and `SConscript`.
- `benchmarks_se/`: 4-core Linux SE-mode wrapper (`SYS_clone`) compiling the 12 C benchmarks from Step 1.
- `scripts/run_step2_gem5_dse.sh`: Runs 12 benchmarks x 8 configs (96 runs) and calls `parse_and_plot_step2.py`.
- `scripts/parse_and_plot_step2.py`: Generates `results/step2_gem5_comparison.csv`, `results/step2_gem5_report.md`, and `results/step2_pareto_comparison.png`.

## Build and Run

```bash
.venv/bin/python step2_gem5_model/src/apply_gem5_patch.py
cd gem5 && ../.venv/bin/scons build/RISCV/gem5.fast -j4 --linker=lld && cd ..
make -C step2_gem5_model/benchmarks_se
./step2_gem5_model/scripts/run_step2_gem5_dse.sh
```
