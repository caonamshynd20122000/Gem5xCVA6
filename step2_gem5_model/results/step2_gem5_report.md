# Step 2 Report: gem5 4-Core CVA6 + 16-Way Shared L2 Way-Shutdown DSE

## 1. Average Summary Across 12 Benchmarks (CACTI 7.0 22nm)

| Policy | Benchmarks | Avg Active Ways (/16) | IPC Change (%) | Avg L2 Miss Rate (%) | Total Dirty Flushes | Avg L2 Leakage (mW) | L2 Leakage Saving (%) | Avg EDP Improvement (%) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `static16` | 12 | 16.00 | +0.00% | 36.19% | 0 | 111.73 | 0.00% | +0.00% |
| `static12` | 12 | 12.00 | -5.61% | 44.81% | 0 | 88.30 | 20.96% | -26.92% |
| `static8` | 12 | 8.00 | -11.37% | 55.54% | 0 | 64.88 | 41.93% | -56.91% |
| `static4` | 12 | 4.00 | -21.49% | 76.53% | 0 | 41.46 | 62.89% | -149.94% |
| `static2` | 12 | 2.00 | -22.84% | 87.61% | 0 | 29.75 | 73.37% | -171.43% |
| `selective_ways` | 12 | 14.16 | -1.75% | 41.54% | 12635 | 100.95 | 9.64% | -17.82% |
| `way_util` | 12 | 10.33 | -8.19% | 49.20% | 10549 | 78.51 | 29.73% | -38.73% |
| `atd_dirty_aware` | 12 | 11.09 | -0.92% | 38.12% | 176 | 82.95 | 25.75% | +15.15% |

## 2. Selected Design for Step 3 (SystemVerilog RTL)

- **Winning Policy:** `atd_dirty_aware`
- **Avg Active L2 Ways:** 11.09 / 16
- **4-Core Aggregate IPC Change:** -0.92%
- **L2 Leakage Power Saving:** 25.75%
- **L2 + DRAM EDP Improvement:** +15.15%

## 3. Per-Benchmark Breakdown (Dynamic Policies vs Baseline 16-Way)

| Benchmark | Policy | Active Ways | IPC 4-Core | IPC Change (%) | L2 Miss (%) | Dirty Flush | Leakage Save (%) | EDP Improv (%) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `bm01_coremark` | `static16` | 16.00 | 2.894 | +0.00% | 96.51% | 0 | 0.00% | +0.00% |
| `bm01_coremark` | `selective_ways` | 16.00 | 2.894 | +0.00% | 96.51% | 0 | 0.00% | +0.00% |
| `bm01_coremark` | `way_util` | 16.00 | 2.894 | +0.00% | 96.51% | 0 | 0.00% | +0.00% |
| `bm01_coremark` | `atd_dirty_aware` | 16.00 | 2.894 | +0.00% | 96.51% | 0 | 0.00% | +0.00% |
| `bm02_dhrystone` | `static16` | 16.00 | 2.696 | +0.00% | 89.42% | 0 | 0.00% | +0.00% |
| `bm02_dhrystone` | `selective_ways` | 16.00 | 2.696 | +0.00% | 89.42% | 0 | 0.00% | +0.00% |
| `bm02_dhrystone` | `way_util` | 16.00 | 2.696 | +0.00% | 89.42% | 0 | 0.00% | +0.00% |
| `bm02_dhrystone` | `atd_dirty_aware` | 16.00 | 2.696 | +0.00% | 89.42% | 0 | 0.00% | +0.00% |
| `bm03_matmul` | `static16` | 16.00 | 2.871 | +0.00% | 31.55% | 0 | 0.00% | +0.00% |
| `bm03_matmul` | `selective_ways` | 13.00 | 2.867 | -0.12% | 34.21% | 228 | 15.72% | +14.85% |
| `bm03_matmul` | `way_util` | 10.00 | 2.871 | -0.00% | 31.61% | 2 | 31.44% | +30.92% |
| `bm03_matmul` | `atd_dirty_aware` | 8.40 | 2.869 | -0.05% | 33.14% | 0 | 39.83% | +38.91% |
| `bm04_spmv` | `static16` | 16.00 | 2.800 | +0.00% | 14.40% | 0 | 0.00% | +0.00% |
| `bm04_spmv` | `selective_ways` | 13.40 | 2.729 | -2.53% | 14.87% | 404 | 13.63% | -3.12% |
| `bm04_spmv` | `way_util` | 9.05 | 2.800 | -0.00% | 14.37% | 1 | 36.41% | +30.91% |
| `bm04_spmv` | `atd_dirty_aware` | 8.20 | 2.759 | -1.46% | 14.30% | 0 | 40.88% | +30.34% |
| `bm05_qsort_rsort` | `static16` | 16.00 | 2.812 | +0.00% | 25.10% | 0 | 0.00% | +0.00% |
| `bm05_qsort_rsort` | `selective_ways` | 11.20 | 2.762 | -1.81% | 31.99% | 1564 | 25.16% | +19.47% |
| `bm05_qsort_rsort` | `way_util` | 7.20 | 2.812 | -0.03% | 25.52% | 1030 | 46.12% | +41.96% |
| `bm05_qsort_rsort` | `atd_dirty_aware` | 8.13 | 2.791 | -0.76% | 29.18% | 0 | 41.23% | +36.43% |
| `bm06_vvadd` | `static16` | 16.00 | 2.819 | +0.00% | 33.47% | 0 | 0.00% | +0.00% |
| `bm06_vvadd` | `selective_ways` | 14.82 | 2.662 | -5.58% | 41.15% | 1041 | 6.17% | -27.82% |
| `bm06_vvadd` | `way_util` | 9.88 | 2.201 | -21.93% | 70.56% | 244 | 32.06% | -94.53% |
| `bm06_vvadd` | `atd_dirty_aware` | 11.65 | 2.712 | -3.78% | 38.95% | 0 | 22.81% | +1.76% |
| `bm07_memcpy` | `static16` | 16.00 | 1.860 | +0.00% | 36.50% | 0 | 0.00% | +0.00% |
| `bm07_memcpy` | `selective_ways` | 15.33 | 1.703 | -8.43% | 49.71% | 2536 | 3.49% | -43.51% |
| `bm07_memcpy` | `way_util` | 9.90 | 1.334 | -28.26% | 83.13% | 1276 | 31.94% | -149.13% |
| `bm07_memcpy` | `atd_dirty_aware` | 14.10 | 1.857 | -0.15% | 40.71% | 0 | 9.98% | -6.33% |
| `bm08_l2_light_1core` | `static16` | 16.00 | 2.370 | +0.00% | 10.36% | 0 | 0.00% | +0.00% |
| `bm08_l2_light_1core` | `selective_ways` | 11.00 | 2.323 | -1.99% | 18.56% | 528 | 26.20% | -21.46% |
| `bm08_l2_light_1core` | `way_util` | 6.62 | 2.370 | -0.00% | 10.36% | 1 | 49.13% | +45.32% |
| `bm08_l2_light_1core` | `atd_dirty_aware` | 4.75 | 2.370 | +0.00% | 10.36% | 0 | 58.96% | +54.39% |
| `bm09_l2_medium_2cores` | `static16` | 16.00 | 1.854 | +0.00% | 11.52% | 0 | 0.00% | +0.00% |
| `bm09_l2_medium_2cores` | `selective_ways` | 12.34 | 1.780 | -3.98% | 22.47% | 1930 | 19.17% | -79.66% |
| `bm09_l2_medium_2cores` | `way_util` | 8.91 | 1.856 | +0.14% | 11.95% | 146 | 37.13% | +28.76% |
| `bm09_l2_medium_2cores` | `atd_dirty_aware` | 8.00 | 1.830 | -1.30% | 14.30% | 0 | 41.93% | +22.13% |
| `bm10_l2_heavy_4cores` | `static16` | 16.00 | 1.162 | +0.00% | 11.18% | 0 | 0.00% | +0.00% |
| `bm10_l2_heavy_4cores` | `selective_ways` | 15.42 | 1.162 | -0.04% | 19.01% | 2316 | 3.04% | -39.38% |
| `bm10_l2_heavy_4cores` | `way_util` | 9.13 | 0.681 | -41.38% | 67.08% | 2917 | 36.01% | -342.97% |
| `bm10_l2_heavy_4cores` | `atd_dirty_aware` | 13.81 | 1.145 | -1.46% | 12.97% | 1 | 11.50% | +1.76% |
| `bm11_l2_stream_mix` | `static16` | 16.00 | 1.001 | +0.00% | 62.98% | 0 | 0.00% | +0.00% |
| `bm11_l2_stream_mix` | `selective_ways` | 16.00 | 1.001 | +0.00% | 62.98% | 0 | 0.00% | +0.00% |
| `bm11_l2_stream_mix` | `way_util` | 7.85 | 1.002 | +0.14% | 62.98% | 3662 | 42.72% | +13.68% |
| `bm11_l2_stream_mix` | `atd_dirty_aware` | 9.92 | 1.001 | -0.00% | 62.98% | 0 | 31.84% | +11.55% |
| `bm12_l2_dynamic_4phases` | `static16` | 16.00 | 1.437 | +0.00% | 11.34% | 0 | 0.00% | +0.00% |
| `bm12_l2_dynamic_4phases` | `selective_ways` | 15.40 | 1.487 | +3.46% | 17.62% | 2088 | 3.16% | -33.20% |
| `bm12_l2_dynamic_4phases` | `way_util` | 13.37 | 1.337 | -6.98% | 26.93% | 1270 | 13.81% | -69.71% |
| `bm12_l2_dynamic_4phases` | `atd_dirty_aware` | 14.08 | 1.407 | -2.09% | 14.59% | 175 | 10.07% | -9.15% |
