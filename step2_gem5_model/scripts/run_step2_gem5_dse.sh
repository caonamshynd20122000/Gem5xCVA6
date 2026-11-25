#!/usr/bin/env bash
set -euo pipefail

# Gem 5 x CVA6 — Step 2 Full DSE Runner
# Runs 12 4-core RISC-V benchmarks across:
#   - Baseline (static 16 ways)
#   - Static Oracle sweep (12, 8, 4, 2 ways)
#   - Policy 1: selective_ways
#   - Policy 2: way_util
#   - Policy 3: atd_dirty_aware
# Then parses stats + CACTI 7.0 (22nm) power model into CSV, Markdown report & Pareto plot.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STEP2_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ROOT_DIR="$(cd "${STEP2_DIR}/.." && pwd)"
GEM5_BIN="${ROOT_DIR}/gem5/build/RISCV/gem5.fast"
VENV_PY="${ROOT_DIR}/.venv/bin/python"
BENCH_DIR="${STEP2_DIR}/benchmarks_se/build"
CONFIG="${STEP2_DIR}/configs/cva6_4core_l2_way_shutdown.py"
OUT_ROOT="${STEP2_DIR}/results"
LOGS_DIR="${OUT_ROOT}/logs"

if [[ ! -x "${GEM5_BIN}" ]]; then
    echo "[ERROR] Khong tim thay ${GEM5_BIN}."
    echo "Vui long bien dich gem5 truoc bang lenh:"
    echo "  cd ${ROOT_DIR}/gem5 && ${ROOT_DIR}/.venv/bin/scons build/RISCV/gem5.fast -j4 --linker=lld"
    exit 1
fi

if [[ ! -d "${BENCH_DIR}" ]]; then
    echo "[INFO] Dang bien dich 12 benchmark SE-mode..."
    make -C "${STEP2_DIR}/benchmarks_se"
fi

mkdir -p "${LOGS_DIR}"

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

# Format: "tag:policy:initial_ways"
CONFIGS=(
    "static16:static:16"
    "static12:static:12"
    "static8:static:8"
    "static4:static:4"
    "static2:static:2"
    "selective_ways:selective_ways:16"
    "way_util:way_util:16"
    "atd_dirty_aware:atd_dirty_aware:16"
)

TOTAL=$(( ${#BENCHMARKS[@]} * ${#CONFIGS[@]} ))
COUNT=0

for cfg in "${CONFIGS[@]}"; do
    IFS=":" read -r TAG POLICY INIT_WAYS <<< "${cfg}"
    for bm in "${BENCHMARKS[@]}"; do
        COUNT=$((COUNT + 1))
        ELF="${BENCH_DIR}/${bm}.elf"
        RUN_DIR="${LOGS_DIR}/${bm}__${TAG}"
        mkdir -p "${RUN_DIR}"
        echo "[${COUNT}/${TOTAL}] Running ${bm} | ${TAG} (policy=${POLICY}, init_ways=${INIT_WAYS})..."
        "${GEM5_BIN}" -r -e -d "${RUN_DIR}" --stats-file=stats.txt \
            "${CONFIG}" \
            --cmd "${ELF}" \
            --policy "${POLICY}" \
            --initial-ways "${INIT_WAYS}" \
            --min-ways 2 \
            --epoch-accesses 2048 \
            --wakeup-lat 6 \
            > "${RUN_DIR}/sim.log" 2>&1
    done
done

echo "[INFO] Hoan tat ${TOTAL} luot mo phong gem5. Dang tong hop bao cao & bieu do..."
"${VENV_PY}" "${STEP2_DIR}/scripts/parse_and_plot_step2.py"
echo "[DONE] Ket qua tai: ${OUT_ROOT}/step2_gem5_report.md"
