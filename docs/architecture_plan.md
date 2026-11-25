# Gem5 x CVA6 — Architecture Specification & Execution Plan (4-Core CVA6 + 16-Way Write-Back Shared L2 Cache)

> **Project:** Gem5 x CVA6  
> **Target Architecture:** **4-Core CVA6 RV64GC** multicore cluster (`Core Tile 0 .. Core Tile 3`, each with Private L1 I-Cache 16 KiB 4-way & Private L1 D-Cache 32 KiB 8-way Write-Through) connected via a **Coherent Crossbar (`L2XBar`)** to a **512 KiB, 16-Way, 64B Line, Write-Back Shared L2 Cache** featuring dynamic **Way-Shutdown**.  
> **3-Step Methodology:**
> - **Step 1 (`step1_baseline/`):** Build **12 RISC-V 4-Core benchmarks** (7 standard from CVA6 / UC Berkeley `riscv-tests` + 5 custom 4-Core L2 scenarios) and run the 16-way always-on **CVA6 4-Core + Shared L2 RTL Baseline** on **Verilator 5.036**.
> - **Step 2 (`step2_gem5_model/`):** Implement and evaluate **L2 Way-Shutdown** policies in **gem5 v26.0 + CACTI 7.0 (22nm)** to select the optimal architecture (high L2 power saving with 4-core IPC drop <= 1%-2%).
> - **Step 3 (`step3_cva6_rtl/`):** Implement the selected **16-Way Write-Back Shared L2 + Way-Shutdown Controller** in SystemVerilog RTL and perform 3-way validation (**Baseline RTL vs gem5 Model vs Custom RTL**) using **Verilator & Yosys**.

---

## 1. Hardware Architecture & CACTI 7.0 (22nm) Power Model

### 1.1. 4-Core CVA6 + Shared L2 System Specification
- **4x CVA6 Core Tiles (`Core 0 .. Core 3`):**
  - 6-stage In-Order pipeline (`RV64GC`), 1-wide issue, 2-wide commit, 8-entry scoreboard, BHT(128) + BTB(32) + RAS(2).
  - **Private L1 I-Cache (per core):** `16 KiB`, `4-way`, Read-Only.
  - **Private L1 D-Cache (per core):** `32 KiB`, `8-way`, **Write-Through (`CACHE_WT`)** + cross-core invalidation input from L2.
- **L1-to-L2 Coherent Interconnect (`L2XBar`):**
  - Aggregates L1I/L1D misses and L1D Write-Through store streams from all 4 cores to the Shared L2; broadcasts L2-to-L1 invalidations on cross-core writes.
- **Target: Shared L2 Cache (`512 KiB, 16-Way, Write-Back`):**
  - Geometry: **`512 KiB`** = **16 Ways x 32 KiB/Way** (`512 sets x 16 ways x 64B line`).
  - Write policy: **Write-Back, Write-Allocate** (16 MSHRs, Writeback & Dirty-Way Flush Buffer).
  - **Way Shutdown (`1 -> 0`) on Write-Back L2:**
    1. `L2 Way-Shutdown Ctrl` disables new allocations into Way `w` (`way_en[w] = 0`).
    2. **Dirty-Way Flush FSM** scans all 512 sets of Way `w`: clean lines (`dirty == 0`) are invalidated immediately; dirty lines (`dirty == 1`) are written back to DRAM via the `L2 Writeback Buffer`.
    3. Once flush completes, `way_sd[w] = 1` power-gates the 32 KiB SRAM array to eliminate leakage power.
  - **Way Wakeup (`0 -> 1`):**
    1. Deassert `way_sd[w] = 0`, wait `T_wakeup` cycles for SRAM rail recovery, ensure valid bits in Way `w` are cleared, then assert `way_en[w] = 1`.

### 1.2. CACTI 7.0 (22nm) Power & Area Metrics for 512 KiB 16-Way Shared L2
Extracted from [`mcpat_cacti/cva6_l2_512k_16w_22nm.cfg`](../mcpat_cacti/cva6_l2_512k_16w_22nm.cfg):
- **Access time:** `0.792 ns` | **Cycle time:** `0.440 ns` | **Area:** `0.413 mm^2` (`Data: 0.3875 mm^2`, `Tag: 0.0255 mm^2`)
- **Dynamic Read Energy / access (16 ways):** `19.645 pJ` (`Data: 16.298 pJ`, `Tag: 3.347 pJ` -> `1.228 pJ/way`)
- **Dynamic Write Energy / access:** `20.814 pJ`
- **Total Leakage Power (16 ways ON):** **`111.726 mW`** (`Data: 101.752 mW`, `Tag: 9.975 mW` — 11.5x higher than L1D)
  - **Power-gateable SRAM cell leakage:** `88.174 + 5.511 = 93.685 mW` (**83.85% of total L2 leakage**, or **`5.855 mW / way`**).
  - **Always-on peripheral leakage (decoders / H-tree):** `18.041 mW`.

---

## 2. Benchmark Suite (12 4-Core RISC-V Workloads)

All 12 benchmarks reside in `step1_baseline/benchmarks/` (compiled with `riscv64-unknown-elf-gcc 12.2.0`, `-O2 -march=rv64im_zicsr -mabi=lp64 -mcmodel=medany`) and are reused directly in Step 2 via the SE-mode `SYS_clone` wrapper.

### Group A — 7 Standard Benchmarks (CVA6 & UC Berkeley `riscv-tests/benchmarks`)

| # | Benchmark | Source | 4-Core Execution & Shared L2 Impact | Expected Optimal Ways |
| :-: | :--- | :--- | :--- | :---: |
| **1** | **`bm01_coremark`** | CVA6 (`verif/tests/custom/coremark`) | 4 cores run CoreMark (List, Matrix, State, CRC). ~16 KiB/core working set fits in L1 -> L2 mostly idle. | **2 - 4 / 16 ways** |
| **2** | **`bm02_dhrystone`** | CVA6 & `riscv-tests` (`dhrystone`) | 4 cores run Dhrystone. >99% L1 hit rate, minimal L2 residency needed. | **2 - 4 / 16 ways** |
| **3** | **`bm03_matmul`** | `riscv-tests` (`mm` / `mt-matmul`) | 4-core blocked matrix multiply (~225 KiB spills from L1 into L2 with high reuse). | **8 - 10 / 16 ways** |
| **4** | **`bm04_spmv`** | `riscv-tests` (`spmv`) | 4-core CSR Sparse Matrix-Vector Multiply (~234 KiB). Indirect indexing stresses L2. | **8 - 12 / 16 ways** |
| **5** | **`bm05_qsort_rsort`** | `riscv-tests` (`qsort` + `rsort`) | Cores 0,1 run QuickSort + Cores 2,3 run RadixSort (~266 KiB). Generates heavy L2 Write-Back dirty lines. | **10 - 12 / 16 ways** |
| **6** | **`bm06_vvadd`** | `riscv-tests` (`vvadd` / `mt-vvadd`) | 4-core vector addition (`C = A + B`, ~397 KiB). High memory bandwidth, low reuse. | **4 - 6 / 16 ways** |
| **7** | **`bm07_memcpy`** | `riscv-tests` (`memcpy` / `mt-memcpy`) | 4-core memory copy (~528 KiB). Continuous store stream creating L2 dirty evictions. | **4 - 6 / 16 ways** |

### Group B — 5 Custom 4-Core 16-Way Shared L2 Benchmarks

| # | Benchmark | 4-Core Workload Distribution (`Core 0..3`) | Evaluation Purpose | Expected Optimal Ways |
| :-: | :--- | :--- | :--- | :---: |
| **8** | **`bm08_l2_light_1core`** | Core 0 reuses 96 KiB (3 L2 ways); Cores 1..3 run light L1-resident ALU compute. | Verify deep shutdown (12/16 ways OFF, ~65-70% leakage saving) with zero IPC loss. | **4 / 16 ways** |
| **9** | **`bm09_l2_medium_2cores`** | Cores 0,1 reuse 128 KiB each (8 L2 ways total); Cores 2,3 stay in L1. | Verify medium-load balance (~8/16 ways ON, ~42% leakage saving). | **8 / 16 ways** |
| **10** | **`bm10_l2_heavy_4cores`** | All 4 Cores reuse 112 KiB/core (448 KiB = 14 L2 ways total). | **High-Performance test:** Controller must keep 14-16 ways ON to avoid severe conflict thrashing. | **14 - 16 / 16 ways** |
| **11** | **`bm11_l2_stream_mix`** | Cores 0,1 reuse 64 KiB/core (4 L2 ways); Cores 2,3 stream 1 MB (0 reuse). | **Policy intelligence test:** Avoid being fooled by streaming misses into enabling all 16 ways. | **4 - 6 / 16 ways** |
| **12** | **`bm12_l2_dynamic_4phases`** | All 4 Cores transition synchronously: **Light (4w) -> Heavy (16w) -> Stream (4w) -> Medium (8w)**. | Evaluate dynamic phase adaptation, `T_wakeup` overhead, and Write-Back dirty flush cost. | **Dynamic: 4 -> 16 -> 4 -> 8** |

---

## 3. 3-Step Execution Plan

### Step 1 (`step1_baseline/`) — 12 Benchmarks & 4-Core 16-Way L2 RTL Baseline
1. Compile all 12 4-core RISC-V benchmarks (`bm01..bm12`) into bare-metal `.elf` binaries.
2. Build and simulate the 4-Core CVA6 + 16-Way Write-Back Shared L2 RTL baseline (`way_en_i = 16'hFFFF`) in Verilator 5.036.
3. Record baseline cycles, 4-core aggregate IPC, L2 hits/misses/writebacks, CACTI 7.0 power/energy, and golden checksums.

### Step 2 (`step2_gem5_model/`) — gem5 Modeling & Way-Shutdown Policy DSE
1. Implement `WayShutdownSetAssoc` (inheriting `gem5::BaseSetAssoc`) in `gem5/src/mem/cache/tags/`:
   - Dynamic `wayEnableMask[15:0]`, Write-Back dirty-line flush to DRAM on `1 -> 0`, and `T_wakeup` latency on `0 -> 1`.
2. Evaluate 3 dynamic policies vs Baseline (16-way) and Static-k Oracle (`12, 8, 4, 2`):
   - **Policy 1 (`selective_ways`):** Miss-rate threshold + hysteresis.
   - **Policy 2 (`way_util`):** Per-way hit utilization counter.
   - **Policy 3 (`atd_dirty_aware`):** 16-set Sampled-Set ATD + Write-Back Dirty-Flush Cost Guard.
3. Generate CSV, Markdown report, and Pareto plot (IPC change vs L2 leakage saving & EDP improvement) to select the winning policy.

### Step 3 (`step3_cva6_rtl/`) — SystemVerilog RTL Implementation & 3-Way Validation
1. Implement the winning Way-Shutdown controller (`l2_way_shutdown_ctrl.sv`) in SystemVerilog RTL and integrate into `cva6_shared_l2_16way.sv`.
2. Verify functional correctness (exact checksum match against Step 1) in Verilator 5.036 and evaluate area/power with Yosys + CACTI 7.0.
3. Produce the final 3-way comparison report: **Baseline RTL vs gem5 Model vs Custom Way-Shutdown RTL**.
