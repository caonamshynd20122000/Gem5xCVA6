#!/usr/bin/env bash
set -euo pipefail

# Gem5xCVA6 — Step 1 Baseline Runner (Real 4-Core OpenHW CVA6 + 16-Way WB Shared L2)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CVA6_DIR="${ROOT_DIR}/cva6"
BENCH_DIR="${SCRIPT_DIR}/benchmarks/build"
LOGS_DIR="${SCRIPT_DIR}/results/logs"
SIM_BIN="${CVA6_DIR}/work-ver-l2-4core/Variane_testharness"

mkdir -p "${LOGS_DIR}"

echo "[STEP 1] Linking OpenHW CVA6 4-Core + Shared L2 Verilator binary..."
make -C "${CVA6_DIR}/work-ver-l2-4core" -f Variane_testharness.mk -j 4

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
    LOG="${LOGS_DIR}/${bm}_w16.log"
    echo "[STEP 1] Running ${bm} on 4-Core OpenHW CVA6 (16-way Baseline)..."
    if "${SIM_BIN}" "+ELF=${ELF}" > "${LOG}" 2>&1; then
        PASS_CNT=$((PASS_CNT + 1))
        grep -E "Verdict|SoC Cycles|L2 Accesses|L2 Dirty WB|L2\+DRAM Energy" "${LOG}"
    else
        echo "[FAIL] ${bm} failed! See ${LOG}"
        exit 1
    fi
done

echo "[STEP 1] Completed ${PASS_CNT}/12 benchmarks PASS on 4-Core OpenHW CVA6."
"${ROOT_DIR}/.venv/bin/python" "${SCRIPT_DIR}/parse_step1_baseline.py"
echo "[DONE] Baseline report: ${SCRIPT_DIR}/results/step1_baseline_report.md"
