# Step 3 Final Report: 3-Way Validation (Baseline RTL vs gem5 Model vs Custom Way-Shutdown RTL)

- **Functional Verification:** **12/12 PASS** (bit-exact 4-core checksum match against Step 1 RTL Baseline)
- **Implemented RTL Policy:** `atd_dirty_aware` (`l2_way_shutdown_ctrl.sv` + `cva6_shared_l2_16way_ws.sv`, 16-set Sampled-Set ATD + Dirty-Flush Guard <= 96 lines + `T_wakeup = 6 cycles`)

## 1. High-Level 3-Way Comparison (Average Across 12 Benchmarks)

| Platform / Configuration | Avg Active L2 Ways (/16) | 4-Core IPC Change (%) | L2 Leakage Saving (%) | Total Shutdown Dirty Flushes | Avg EDP Improvement (%) |
| :--- | ---: | ---: | ---: | ---: | ---: |
| **Step 1: CVA6 RTL Baseline (16-Way Always-On)** | 16.00 | +0.00% | 0.00% | 0 | +0.00% |
| **Step 2: gem5 Model (`atd_dirty_aware`)** | 11.10 | -0.28% | 24.67% | 157 | +20.24% |
| **Step 3: CVA6 Custom RTL (`atd_dirty_aware`)** | **12.54** | **-0.03%** | **17.43%** | **345** | **+15.67%** |

## 2. Per-Benchmark Breakdown (Custom RTL vs Step 1 Baseline & Step 2 gem5)

| Benchmark | Checksum | RTL Ways (/16) | gem5 Ways (/16) | RTL IPC Delta (%) | gem5 IPC Delta (%) | RTL Leak Save (%) | RTL Energy Save (%) | RTL EDP Improv (%) | Shutdown Flushes |
| :--- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `bm01_coremark` | MATCH | 4.75 | 16.00 | +0.30% | +0.00% | 56.59% | +55.32% | +55.45% | 2 |
| `bm02_dhrystone` | MATCH | 7.94 | 16.00 | +0.00% | +0.00% | 40.55% | +38.23% | +38.23% | 0 |
| `bm03_matmul` | MATCH | 7.90 | 8.40 | -0.02% | -0.05% | 40.74% | +38.52% | +38.51% | 15 |
| `bm04_spmv` | MATCH | 12.00 | 8.20 | -0.13% | +0.22% | 20.13% | +18.55% | +18.44% | 70 |
| `bm05_qsort_rsort` | MATCH | 11.29 | 8.13 | -0.33% | -0.72% | 23.70% | +21.24% | +20.98% | 148 |
| `bm06_vvadd` | MATCH | 14.59 | 11.76 | -0.22% | -5.93% | 7.11% | +5.25% | +5.05% | 102 |
| `bm07_memcpy` | MATCH | 16.00 | 14.10 | +0.00% | +3.67% | 0.00% | -1.70% | -1.70% | 0 |
| `bm08_l2_light_1core` | MATCH | 13.11 | 4.75 | +0.00% | +0.00% | 14.54% | +12.79% | +12.79% | 4 |
| `bm09_l2_medium_2cores` | MATCH | 14.85 | 8.00 | +0.00% | -0.79% | 5.79% | +4.23% | +4.23% | 4 |
| `bm10_l2_heavy_4cores` | MATCH | 16.00 | 13.77 | +0.00% | +0.53% | 0.00% | -1.41% | -1.41% | 0 |
| `bm11_l2_stream_mix` | MATCH | 16.00 | 9.92 | +0.00% | -0.70% | 0.00% | -1.13% | -1.13% | 0 |
| `bm12_l2_dynamic_4phases` | MATCH | 16.00 | 14.13 | +0.00% | +0.43% | 0.00% | -1.42% | -1.42% | 0 |
