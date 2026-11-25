# Step 1: 12 4-Core RISC-V Benchmarks & 4-Core OpenHW CVA6 + 16-Way Shared L2 Baseline

Baseline RTL evaluation running 12 4-core RISC-V benchmarks on 4-core OpenHW CVA6 (`fpga_linux_cv64a6`, `cva6/core/cva6.sv`) connected via `axi_xbar` to a 512 KiB, 16-way, write-back shared L2 cache (`way_en = 16'hFFFF`, Verilator 5.036).

## Layout

- `benchmarks/`: 7 standard (`bm01..bm07`) and 5 L2-targeted (`bm08..bm12`) 4-core RV64IMA_Zicsr benchmarks using atomic `amoor.d`/`amoswap.d` synchronization across cores.
- `run_step1_baseline.sh`: Runs all 12 ELFs on `cva6/work-ver-l2-4core/Variane_testharness` (`+WS_EN=0`) and invokes `parse_step1_baseline.py`.
- `parse_step1_baseline.py`: Aggregates per-benchmark logs and CACTI 7.0 (22nm) power metrics into `results/step1_baseline_summary.csv` and `results/step1_baseline_report.md`.

## Build and Run

```bash
# Build 12 4-core RISC-V ELFs
make -C step1_baseline/benchmarks

# Build 4-core OpenHW CVA6 + Shared L2 Verilator binary
cd cva6 && make -f corev_apu/tb/Makefile.l2_4core && cd ..

# Run all 12 baseline benchmarks
./step1_baseline/run_step1_baseline.sh
```
