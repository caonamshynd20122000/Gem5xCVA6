#!/usr/bin/env bash
# Gem 5 x CVA6 — Bước 1 (Step 1): Build & Run 12 4-Core RISC-V Benchmarks on CVA6 + 16-Way Shared L2 RTL (Verilator)
set -euo pipefail

STEP1_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${STEP1_DIR}/.." && pwd)"
BENCH_DIR="${STEP1_DIR}/benchmarks"
RTL_DIR="${STEP1_DIR}/cva6_l2_rtl_baseline"
RESULTS_DIR="${STEP1_DIR}/results"
LOG_DIR="${RESULTS_DIR}/logs"
SIM_BIN="${RTL_DIR}/obj_dir/Vcva6_4core_soc_top"

L2_WAYS_LIST="${1:-16}"

echo "[Step 1.1] Building 12 4-Core RISC-V Benchmarks (.elf)..."
make -C "${BENCH_DIR}" all

echo "[Step 1.2] Building 4-Core CVA6 + 16-Way Shared L2 RTL Simulator (Verilator)..."
make -C "${RTL_DIR}" all

mkdir -p "${LOG_DIR}"
rm -f "${LOG_DIR}"/*.log

BENCHMARKS=(
    "bm01_coremark"
    "bm02_dhrystone"
    "bm03_matmul"
    "bm04_spmv"
    "bm05_qsort_rsort"
    "bm06_vvadd"
    "bm07_memcpy"
    "bm08_l2_light_1core"
    "bm09_l2_medium_2cores"
    "bm10_l2_heavy_4cores"
    "bm11_l2_stream_mix"
    "bm12_l2_dynamic_4phases"
)

for bm in "${BENCHMARKS[@]}"; do
    elf="${BENCH_DIR}/build/${bm}.elf"
    for w in ${L2_WAYS_LIST}; do
        log_file="${LOG_DIR}/${bm}_w${w}.log"
        echo "------------------------------------------------------------"
        echo "[RUN] Benchmark: ${bm} | Shared L2 Active Ways: ${w}/16"
        "${SIM_BIN}" "+ELF=${elf}" "+L2_WAYS=${w}" | tee "${log_file}" | grep -E "Verdict|SoC Cycles|Total 4-Core Inst|L2 Hits / Misses|L2 Dirty WB|Total L2\+DRAM"
    done
done

echo "------------------------------------------------------------"
echo "[Step 1.3] Generating Summary CSV & Markdown Report..."
"${ROOT_DIR}/.venv/bin/python" "${STEP1_DIR}/parse_step1_baseline.py"
