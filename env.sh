#!/usr/bin/env bash
# Portable environment setup for Gem5 x CVA6 project

export GEM5_CVA6_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export GEM5_DIR="${GEM5_CVA6_ROOT}/gem5"
export CVA6_DIR="${GEM5_CVA6_ROOT}/cva6"
export CACTI_DIR="${GEM5_CVA6_ROOT}/mcpat_cacti/cacti"

# Optional RISC-V toolchain paths (override via environment if installed elsewhere)
export RISCV64_TOOLCHAIN="${RISCV64_TOOLCHAIN:-${GEM5_CVA6_ROOT}/../tools/riscv64-gnu-toolchain}"
export RISCV32_TOOLCHAIN="${RISCV32_TOOLCHAIN:-${GEM5_CVA6_ROOT}/../tools/riscv32-gnu-toolchain}"
export RISCV="${RISCV:-${RISCV64_TOOLCHAIN}}"

export PATH="${GEM5_CVA6_ROOT}/.venv/bin:${RISCV64_TOOLCHAIN}/bin:${RISCV32_TOOLCHAIN}/bin:${PATH}"

echo "[Gem5 x CVA6] Environment loaded:"
echo "  ROOT      : ${GEM5_CVA6_ROOT}"
echo "  Python    : $(which python3)"
echo "  SCons     : $(which scons 2>/dev/null || echo 'not installed yet')"
echo "  RISCV GCC : $(which riscv64-unknown-elf-gcc 2>/dev/null || echo 'not found')"
echo "  Verilator : $(which verilator 2>/dev/null || echo 'not found')"
