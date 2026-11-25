#!/usr/bin/env bash
set -euo pipefail

# Gem5xCVA6 — Step 3 RTL Evaluation on Real 4-Core OpenHW CVA6 (atd_dirty_aware)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STEP3_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ROOT_DIR="$(cd "${STEP3_DIR}/.." && pwd)"
CVA6_DIR="${ROOT_DIR}/cva6"
BENCH_DIR="${ROOT_DIR}/step1_baseline/benchmarks/build"
LOGS_DIR="${STEP3_DIR}/results/logs"
VENV_PY="${ROOT_DIR}/.venv/bin/python"
SIM_BIN="${CVA6_DIR}/work-ver-l2-4core/Variane_testharness"

mkdir -p "${LOGS_DIR}"

echo "[STEP 3] Building 4-Core OpenHW CVA6 + atd_dirty_aware Shared L2 (Verilator)..."
make -C "${CVA6_DIR}" -f corev_apu/tb/Makefile.l2_4core clean all

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
    echo "[STEP 3] Running ${bm} on 4-Core OpenHW CVA6 (atd_dirty_aware)..."
    if "${SIM_BIN}" "+ELF=${ELF}" "+WS_EN=1" > "${LOG}" 2>&1; then
        PASS_CNT=$((PASS_CNT + 1))
        grep -E "Verdict|Avg Active Ways|SoC Cycles|L2 Dirty WB|Total L2\+DRAM" "${LOG}"
    else
        echo "[FAIL] ${bm} failed! See ${LOG}"
        exit 1
    fi
done

echo "[STEP 3] Completed ${PASS_CNT}/12 benchmarks PASS on 4-Core OpenHW CVA6. Generating 3-way report..."
"${VENV_PY}" "${SCRIPT_DIR}/compare_3way_report.py"
echo "[DONE] Report: ${STEP3_DIR}/results/step3_3way_comparison.md"
