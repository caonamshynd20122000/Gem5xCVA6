#!/usr/bin/env bash
set -euo pipefail

# Gem5 x CVA6 — Step 3 RTL Evaluation & 3-Way Comparison Runner
# Builds Verilator RTL (atd_dirty_aware), runs all 12 Step 1 4-core ELFs,
# verifies 12/12 PASS + bit-exact checksums, and generates 3-way comparison report.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STEP3_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ROOT_DIR="$(cd "${STEP3_DIR}/.." && pwd)"
BENCH_DIR="${ROOT_DIR}/step1_baseline/benchmarks/build"
TB_DIR="${STEP3_DIR}/tb"
LOGS_DIR="${STEP3_DIR}/results/logs"
VENV_PY="${ROOT_DIR}/.venv/bin/python"

mkdir -p "${LOGS_DIR}"

echo "[STEP 3] Compiling Step 3 Verilator RTL (4-Core CVA6 + atd_dirty_aware Shared L2)..."
make -C "${TB_DIR}"

SIM_BIN="${TB_DIR}/obj_dir/Vcva6_4core_soc_ws_top"

BENCHMARKS=(
    bm01_coremark
    bm02_dhrystone
    bm03_matmul
    bm04_spmv
    bm05_qsort_rsort
    bm06_vvadd
    bm07_memcpy
    bm08_l2_light_1core
    bm09_l2_medium_2cores
    bm10_l2_heavy_4cores
    bm11_l2_stream_mix
    bm12_l2_dynamic_4phases
)

PASS_CNT=0
for bm in "${BENCHMARKS[@]}"; do
    ELF="${BENCH_DIR}/${bm}.elf"
    LOG="${LOGS_DIR}/${bm}_ws_atd.log"
    echo "[STEP 3] Running ${bm} (atd_dirty_aware RTL)..."
    if "${SIM_BIN}" "+ELF=${ELF}" "+WS_EN=1" > "${LOG}" 2>&1; then
        PASS_CNT=$((PASS_CNT + 1))
        grep -E "Verdict|Avg Active Ways|Total 4-Core Inst|Total L2\+DRAM" "${LOG}"
    else
        echo "[FAIL] ${bm} failed! See ${LOG}"
        exit 1
    fi
done

echo "[STEP 3] Completed ${PASS_CNT}/12 benchmarks PASS. Generating 3-way comparison report..."
"${VENV_PY}" "${SCRIPT_DIR}/compare_3way_report.py"
echo "[DONE] Report: ${STEP3_DIR}/results/step3_3way_comparison.md"
