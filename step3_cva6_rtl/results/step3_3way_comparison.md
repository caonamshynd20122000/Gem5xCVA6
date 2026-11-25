# Step 3 Final Report: 3-Way Validation (Baseline RTL vs gem5 Model vs Custom Way-Shutdown RTL)

- **Functional Verification:** **12/12 PASS** (bit-exact 4-core checksum match against Step 1 RTL Baseline)
- **Implemented RTL Policy:** `atd_dirty_aware` (`l2_way_shutdown_ctrl.sv` + `cva6_shared_l2_16way_ws.sv`, 16-set Sampled-Set ATD + Dirty-Flush Guard <= 96 lines + `T_wakeup = 6 cycles`)

## 1. High-Level 3-Way Comparison (Average Across 12 Benchmarks)

| Platform / Configuration | Avg Active L2 Ways (/16) | 4-Core IPC Change (%) | L2 Leakage Saving (%) | Total Shutdown Dirty Flushes | Avg EDP Improvement (%) |
| :--- | ---: | ---: | ---: | ---: | ---: |
| **Step 1: CVA6 RTL Baseline (16-Way Always-On)** | 16.00 | +0.00% | 0.00% | 0 | +0.00% |
| **Step 2: gem5 Model (`atd_dirty_aware`)** | 11.09 | -0.92% | 25.75% | 176 | +15.15% |
| **Step 3: CVA6 Custom RTL (`atd_dirty_aware`)** | **5.59** | **+0.03%** | **52.36%** | **211** | **+38.53%** |

## 2. Per-Benchmark Breakdown (Custom RTL vs Step 1 Baseline & Step 2 gem5)

| Benchmark | Checksum | RTL Ways (/16) | gem5 Ways (/16) | RTL IPC Delta (%) | gem5 IPC Delta (%) | RTL Leak Save (%) | RTL Energy Save (%) | RTL EDP Improv (%) | Shutdown Flushes |
| :--- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `bm01_coremark` | MATCH | 2.19 | 16.00 | +0.00% | +0.00% | 69.48% | +67.86% | +67.86% | 0 |
| `bm02_dhrystone` | MATCH | 3.26 | 16.00 | +0.00% | +0.00% | 64.10% | +56.41% | +56.41% | 0 |
| `bm03_matmul` | MATCH | 6.79 | 8.40 | +0.04% | -0.05% | 46.34% | +37.88% | +37.90% | 4 |
| `bm04_spmv` | MATCH | 5.81 | 8.20 | +0.21% | -1.46% | 51.27% | +39.36% | +39.41% | 28 |
| `bm05_qsort_rsort` | MATCH | 6.91 | 8.13 | -0.50% | -0.76% | 45.71% | +35.35% | +34.99% | 0 |
| `bm06_vvadd` | MATCH | 6.65 | 11.65 | +0.49% | -3.78% | 47.03% | +28.10% | +28.32% | 158 |
| `bm07_memcpy` | MATCH | 5.90 | 14.10 | +0.87% | -0.15% | 50.80% | +27.18% | +27.79% | 0 |
| `bm08_l2_light_1core` | MATCH | 3.39 | 4.75 | +0.69% | +0.00% | 63.47% | +52.27% | +52.59% | 0 |
| `bm09_l2_medium_2cores` | MATCH | 5.14 | 8.00 | -0.55% | -1.30% | 54.64% | +37.38% | +37.03% | 4 |
| `bm10_l2_heavy_4cores` | MATCH | 6.75 | 13.81 | -0.74% | -1.46% | 46.56% | +26.74% | +26.02% | 5 |
| `bm11_l2_stream_mix` | MATCH | 6.74 | 9.92 | +0.12% | -0.00% | 46.60% | +29.75% | +29.75% | 0 |
| `bm12_l2_dynamic_4phases` | MATCH | 7.58 | 14.08 | -0.24% | -2.09% | 42.38% | +24.56% | +24.25% | 12 |
