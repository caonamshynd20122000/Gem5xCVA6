# Step 2: gem5 Model — 4-Core CVA6 + 512 KiB 16-Way Write-Back Shared L2 Way-Shutdown

## Directory Layout

- `src/way_shutdown_tags.{hh,cc}`: C++ `WayShutdownSetAssoc` class inheriting `gem5::BaseSetAssoc`, supporting 4 modes:
  - `static` (Baseline 16-way & Static-k Oracle sweep)
  - `selective_ways` (Albonesi Miss-Rate Threshold + Hysteresis)
  - `way_util` (Per-Way Hit Utilization Counter)
  - `atd_dirty_aware` (16-Set Sampled-Set ATD + Write-Back Dirty-Flush Cost Guard)
- `src/apply_gem5_patch.py`: Automatically copies `way_shutdown_tags.{hh,cc}` into `gem5/src/mem/cache/tags/` and registers `WayShutdownSetAssoc` in `Tags.py` and `SConscript`.
- `configs/cva6_4core_l2_way_shutdown.py`: gem5 system configuration with 4x `RiscvMinorCPU`, Private L1I (16 KiB, 4-Way), Private L1D (32 KiB, 8-Way), `L2XBar`, and Shared L2 (512 KiB, 16-Way Write-Back).
- `benchmarks_se/`: 4-Core Linux SE-mode startup wrapper (`SYS_clone`) compiling the exact 12 C benchmarks from Step 1 with shared memory support.
- `scripts/run_step2_gem5_dse.sh`: Runs all 12 benchmarks x 8 configurations (96 runs) and automatically invokes `parse_and_plot_step2.py`.
- `scripts/parse_and_plot_step2.py`: Aggregates gem5 stats + CACTI 7.0 (22nm) power model into `results/step2_gem5_comparison.csv`, `results/step2_gem5_report.md`, and `results/step2_pareto_comparison.png`.

## How to Build & Run

1. Apply patch and build `gem5.fast` (RISC-V):
```bash
.venv/bin/python step2_gem5_model/src/apply_gem5_patch.py
cd gem5 && ../.venv/bin/scons build/RISCV/gem5.fast -j4 --linker=lld && cd ..
```

2. Build SE-mode benchmarks and run the full Step 2 DSE:
```bash
make -C step2_gem5_model/benchmarks_se
./step2_gem5_model/scripts/run_step2_gem5_dse.sh
```
