# Step 2 Report: gem5 4-Core CVA6 + 16-Way Shared L2 Way-Shutdown DSE

## 1. Average Summary Across 12 Benchmarks (CACTI 7.0 22nm)

| Policy | Benchmarks | Avg Active Ways (/16) | IPC Change (%) | Avg L2 Miss Rate (%) | Total Dirty Flushes | Avg L2 Leakage (mW) | L2 Leakage Saving (%) | Avg EDP Improvement (%) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `static16` | 12 | 16.00 | +0.00% | 36.03% | 0 | 111.73 | 0.00% | +0.00% |
| `static12` | 12 | 12.00 | +0.52% | 44.64% | 0 | 89.24 | 20.12% | +5.31% |
| `static8` | 12 | 8.00 | -6.63% | 55.73% | 0 | 66.76 | 40.25% | +0.90% |
| `static4` | 12 | 4.00 | -15.61% | 76.09% | 0 | 44.27 | 60.37% | -20.94% |
| `static2` | 12 | 2.00 | -16.94% | 87.36% | 0 | 33.03 | 70.44% | -28.24% |
| `selective_ways` | 12 | 14.16 | -0.36% | 41.65% | 12473 | 101.38 | 9.26% | -3.12% |
| `way_util` | 12 | 9.76 | -5.94% | 54.10% | 13624 | 76.67 | 31.38% | -7.08% |
| `atd_dirty_aware` | 12 | 11.10 | -0.28% | 38.08% | 157 | 84.17 | 24.67% | +20.24% |

## 2. Selected Design for Step 3 (SystemVerilog RTL)

- **Winning Policy:** `atd_dirty_aware`
- **Avg Active L2 Ways:** 11.10 / 16
- **4-Core Aggregate IPC Change:** -0.28%
- **L2 Leakage Power Saving:** 24.67%
- **L2 + DRAM EDP Improvement:** +20.24%

## 3. Per-Benchmark Breakdown (Dynamic Policies vs Baseline 16-Way)

| Benchmark | Policy | Active Ways | IPC 4-Core | IPC Change (%) | L2 Miss (%) | Dirty Flush | Leakage Save (%) | EDP Improv (%) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `bm01_coremark` | `static16` | 16.00 | 2.892 | +0.00% | 96.74% | 0 | 0.00% | +0.00% |
| `bm01_coremark` | `selective_ways` | 16.00 | 2.892 | +0.00% | 96.74% | 0 | 0.00% | +0.00% |
| `bm01_coremark` | `way_util` | 16.00 | 2.892 | +0.00% | 96.74% | 0 | 0.00% | +0.00% |
| `bm01_coremark` | `atd_dirty_aware` | 16.00 | 2.892 | +0.00% | 96.74% | 0 | 0.00% | +0.00% |
| `bm02_dhrystone` | `static16` | 16.00 | 2.697 | +0.00% | 88.89% | 0 | 0.00% | +0.00% |
| `bm02_dhrystone` | `selective_ways` | 16.00 | 2.697 | +0.00% | 88.89% | 0 | 0.00% | +0.00% |
| `bm02_dhrystone` | `way_util` | 16.00 | 2.697 | +0.00% | 88.89% | 0 | 0.00% | +0.00% |
| `bm02_dhrystone` | `atd_dirty_aware` | 16.00 | 2.697 | +0.00% | 88.89% | 0 | 0.00% | +0.00% |
| `bm03_matmul` | `static16` | 16.00 | 2.864 | +0.00% | 31.54% | 0 | 0.00% | +0.00% |
| `bm03_matmul` | `selective_ways` | 13.00 | 2.861 | -0.11% | 34.21% | 228 | 15.09% | +14.65% |
| `bm03_matmul` | `way_util` | 10.00 | 2.864 | -0.00% | 31.60% | 2 | 30.19% | +29.98% |
| `bm03_matmul` | `atd_dirty_aware` | 8.40 | 2.862 | -0.05% | 33.04% | 0 | 38.24% | +37.81% |
| `bm04_spmv` | `static16` | 16.00 | 2.678 | +0.00% | 12.76% | 0 | 0.00% | +0.00% |
| `bm04_spmv` | `selective_ways` | 13.10 | 2.643 | -1.31% | 15.23% | 443 | 14.59% | +6.76% |
| `bm04_spmv` | `way_util` | 9.00 | 2.677 | -0.01% | 12.71% | 1 | 35.22% | +32.95% |
| `bm04_spmv` | `atd_dirty_aware` | 8.20 | 2.684 | +0.22% | 14.33% | 0 | 39.24% | +35.34% |
| `bm05_qsort_rsort` | `static16` | 16.00 | 2.804 | +0.00% | 25.08% | 0 | 0.00% | +0.00% |
| `bm05_qsort_rsort` | `selective_ways` | 12.13 | 2.788 | -0.57% | 28.63% | 1080 | 19.45% | +17.74% |
| `bm05_qsort_rsort` | `way_util` | 8.13 | 2.803 | -0.02% | 25.18% | 517 | 39.58% | +38.31% |
| `bm05_qsort_rsort` | `atd_dirty_aware` | 8.13 | 2.784 | -0.72% | 29.14% | 0 | 39.58% | +37.74% |
| `bm06_vvadd` | `static16` | 16.00 | 2.819 | +0.00% | 33.47% | 0 | 0.00% | +0.00% |
| `bm06_vvadd` | `selective_ways` | 14.82 | 2.622 | -6.99% | 41.16% | 1040 | 5.92% | -23.72% |
| `bm06_vvadd` | `way_util` | 9.88 | 2.160 | -23.36% | 70.51% | 244 | 30.78% | -64.62% |
| `bm06_vvadd` | `atd_dirty_aware` | 11.76 | 2.651 | -5.93% | 38.95% | 0 | 21.31% | +3.98% |
| `bm07_memcpy` | `static16` | 16.00 | 1.553 | +0.00% | 36.50% | 0 | 0.00% | +0.00% |
| `bm07_memcpy` | `selective_ways` | 15.33 | 1.499 | -3.50% | 50.08% | 2528 | 3.35% | -19.98% |
| `bm07_memcpy` | `way_util` | 9.90 | 1.257 | -19.06% | 83.84% | 1646 | 30.67% | -57.96% |
| `bm07_memcpy` | `atd_dirty_aware` | 14.10 | 1.610 | +3.67% | 40.66% | 0 | 9.58% | +6.76% |
| `bm08_l2_light_1core` | `static16` | 16.00 | 2.358 | +0.00% | 10.36% | 0 | 0.00% | +0.00% |
| `bm08_l2_light_1core` | `selective_ways` | 11.00 | 2.315 | -1.81% | 18.56% | 528 | 25.16% | -11.36% |
| `bm08_l2_light_1core` | `way_util` | 6.62 | 2.358 | -0.00% | 10.37% | 1 | 47.17% | +45.75% |
| `bm08_l2_light_1core` | `atd_dirty_aware` | 4.75 | 2.358 | +0.00% | 10.36% | 0 | 56.60% | +54.90% |
| `bm09_l2_medium_2cores` | `static16` | 16.00 | 1.731 | +0.00% | 11.52% | 0 | 0.00% | +0.00% |
| `bm09_l2_medium_2cores` | `selective_ways` | 12.34 | 1.694 | -2.15% | 22.45% | 1932 | 18.40% | -23.12% |
| `bm09_l2_medium_2cores` | `way_util` | 8.91 | 1.735 | +0.20% | 11.94% | 146 | 35.65% | +33.44% |
| `bm09_l2_medium_2cores` | `atd_dirty_aware` | 8.00 | 1.718 | -0.79% | 14.30% | 0 | 40.25% | +31.57% |
| `bm10_l2_heavy_4cores` | `static16` | 16.00 | 0.728 | +0.00% | 11.18% | 0 | 0.00% | +0.00% |
| `bm10_l2_heavy_4cores` | `selective_ways` | 15.32 | 0.760 | +4.28% | 22.73% | 2421 | 3.41% | +0.07% |
| `bm10_l2_heavy_4cores` | `way_util` | 5.58 | 0.536 | -26.41% | 94.05% | 6037 | 52.42% | -107.28% |
| `bm10_l2_heavy_4cores` | `atd_dirty_aware` | 13.77 | 0.732 | +0.53% | 13.08% | 1 | 11.20% | +7.84% |
| `bm11_l2_stream_mix` | `static16` | 16.00 | 0.724 | +0.00% | 62.98% | 0 | 0.00% | +0.00% |
| `bm11_l2_stream_mix` | `selective_ways` | 16.00 | 0.724 | +0.00% | 62.98% | 0 | 0.00% | +0.00% |
| `bm11_l2_stream_mix` | `way_util` | 8.00 | 0.723 | -0.23% | 63.00% | 1368 | 40.25% | +27.72% |
| `bm11_l2_stream_mix` | `atd_dirty_aware` | 9.92 | 0.719 | -0.70% | 62.98% | 0 | 30.57% | +24.40% |
| `bm12_l2_dynamic_4phases` | `static16` | 16.00 | 1.049 | +0.00% | 11.35% | 0 | 0.00% | +0.00% |
| `bm12_l2_dynamic_4phases` | `selective_ways` | 14.86 | 1.131 | +7.85% | 18.14% | 2273 | 5.75% | +1.57% |
| `bm12_l2_dynamic_4phases` | `way_util` | 9.11 | 1.024 | -2.41% | 60.39% | 3662 | 34.66% | -63.21% |
| `bm12_l2_dynamic_4phases` | `atd_dirty_aware` | 14.13 | 1.054 | +0.43% | 14.53% | 156 | 9.42% | +2.58% |
