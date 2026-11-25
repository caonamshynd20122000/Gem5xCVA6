# Step 1: 12 4-Core RISC-V Benchmarks & CVA6 4-Core + 16-Way Shared L2 RTL Baseline (Verilator)

This directory contains all benchmark source code, SystemVerilog RTL, automation scripts, and baseline results for **Step 1** simulated on **Verilator 5.036**.

## 1. Directory Structure

```text
step1_baseline/
├── README.md                              # Step 1 build and run guide
├── run_step1_baseline.sh                  # Automated build & run script for all 12 benchmarks on Verilator
├── parse_step1_baseline.py                # Aggregates logs + CACTI 7.0 (22nm) power -> CSV & Markdown
├── benchmarks/                            # 12 4-Core RISC-V benchmarks (7 standard + 5 L2-targeted)
│   ├── common/
│   │   ├── bench_4core.h                  # 4-core barrier API, mhartid/mcycle/minstret helpers
│   │   ├── crt0_4core.S                   # 4-core SMP startup (16 KiB private stack per hart 0..3)
│   │   ├── syscalls_4core.c               # 4-core sync, checksum aggregation & HTIF tohost signaling
│   │   └── link_4core.ld                  # Linker script mapped at 0x80000000
│   ├── bm01_coremark.c .. bm12_l2_dynamic_4phases.c
│   └── Makefile                           # Builds all 12 ELFs using riscv64-unknown-elf-gcc 12.2.0
├── cva6_l2_rtl_baseline/                  # SystemVerilog RTL for 4-Core CVA6 + 16-Way WB Shared L2
│   ├── cva6_4core_l2_pkg.sv               # Parameters: 4 Cores, L1I(16KB,4w), L1D(32KB,8w,WT), L2(512KB,16w,WB)
│   ├── cva6_core_tile_l1.sv               # CVA6 RV64IM_Zicsr Core Tile + Private L1I + L1D (WT + L2 Inval)
│   ├── cva6_shared_l2_16way.sv            # Shared L2 Cache (512 KiB, 16-Way, 64B, Write-Back, way_en_i[15:0])
│   ├── cva6_4core_soc_top.sv              # Top-level 4-Core Cluster + L2XBar + Shared L2 + DRAM
│   ├── sim_main.cpp                       # Verilator C++ Testbench (ELF64 loader + CACTI Power Logger)
│   └── Makefile                           # Verilator build Makefile
└── results/
    ├── step1_baseline_summary.csv         # Aggregated CSV metrics
    └── step1_baseline_report.md           # Summary Markdown report
```

## 2. How to Run

### A. Run the full Step 1 suite (Build 12 benchmarks + Build Verilator RTL + Run 12 tests at 16-Way Baseline)
```bash
./step1_baseline/run_step1_baseline.sh 16
```

### B. Run a single benchmark on Verilator RTL
```bash
cd step1_baseline/cva6_l2_rtl_baseline
./obj_dir/Vcva6_4core_soc_top +ELF=../benchmarks/build/bm01_coremark.elf +L2_WAYS=16
./obj_dir/Vcva6_4core_soc_top +ELF=../benchmarks/build/bm10_l2_heavy_4cores.elf +L2_WAYS=16
```

### C. View the summary report
```bash
cat step1_baseline/results/step1_baseline_report.md
```
