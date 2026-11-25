# Step 3 Final Report: 3-Way Validation (Baseline RTL vs gem5 Model vs Custom Way-Shutdown RTL)

- **Functional Verification:** **12/12 PASS** (bit-exact 4-core checksum match against Step 1 RTL Baseline)
- **Implemented RTL Policy:** `atd_dirty_aware` (`l2_way_shutdown_ctrl.sv` + `cva6_shared_l2_16way_ws.sv`, 16-set Sampled-Set ATD + Dirty-Flush Guard <= 96 lines + `T_wakeup = 6 cycles`)

## 1. High-Level 3-Way Comparison (Average Across 12 Benchmarks)

| Platform / Configuration | Avg Active L2 Ways (/16) | 4-Core IPC Change (%) | L2 Leakage Saving (%) | Total Shutdown Dirty Flushes | Avg EDP Improvement (%) |
| :--- | ---: | ---: | ---: | ---: | ---: |
| **Step 1: CVA6 RTL Baseline (16-Way Always-On)** | 16.00 | +0.00% | 0.00% | 0 | +0.00% |
| **Step 2: gem5 Model (`atd_dirty_aware`)** | 11.10 | -0.28% | 24.67% | 157 | +20.24% |
| **Step 3: CVA6 Custom RTL (`atd_dirty_aware`)** | **4.82** | **-7.52%** | **56.25%** | **69** | **+42.88%** |

## 2. Per-Benchmark Breakdown (Custom RTL vs Step 1 Baseline & Step 2 gem5)

| Benchmark | Checksum | RTL Ways (/16) | gem5 Ways (/16) | RTL IPC Delta (%) | gem5 IPC Delta (%) | RTL Leak Save (%) | RTL Energy Save (%) | RTL EDP Improv (%) | Shutdown Flushes |
| :--- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `bm01_coremark` | MATCH | 2.40 | 16.00 | +0.26% | +0.00% | 68.42% | +67.28% | +67.37% | 0 |
| `bm02_dhrystone` | MATCH | 3.95 | 16.00 | +0.00% | +0.00% | 60.63% | +58.21% | +58.21% | 0 |
| `bm03_matmul` | MATCH | 6.61 | 8.40 | -1.44% | -0.05% | 47.26% | +43.93% | +43.11% | 7 |
| `bm04_spmv` | MATCH | 5.09 | 8.20 | -7.58% | +0.22% | 54.89% | +47.38% | +43.06% | 0 |
| `bm05_qsort_rsort` | MATCH | 5.59 | 8.13 | -8.98% | -0.72% | 52.35% | +42.80% | +37.15% | 40 |
| `bm06_vvadd` | MATCH | 5.55 | 11.76 | -10.20% | -5.93% | 52.60% | +41.38% | +34.72% | 4 |
| `bm07_memcpy` | MATCH | 6.37 | 14.10 | -12.48% | +3.67% | 48.43% | +35.17% | +25.93% | 0 |
| `bm08_l2_light_1core` | MATCH | 2.79 | 4.75 | -7.68% | +0.00% | 66.48% | +58.82% | +55.39% | 0 |
| `bm09_l2_medium_2cores` | MATCH | 4.05 | 8.00 | -11.44% | -0.79% | 60.14% | +49.14% | +42.57% | 3 |
| `bm10_l2_heavy_4cores` | MATCH | 5.54 | 13.77 | -13.42% | +0.53% | 52.63% | +39.17% | +29.74% | 3 |
| `bm11_l2_stream_mix` | MATCH | 3.93 | 9.92 | -4.29% | -0.70% | 60.70% | +51.83% | +49.67% | 0 |
| `bm12_l2_dynamic_4phases` | MATCH | 5.97 | 14.13 | -13.02% | +0.43% | 50.44% | +37.06% | +27.63% | 12 |
