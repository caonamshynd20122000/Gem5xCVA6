// Copyright 2026 Gem 5 x CVA6 Project
// Verilator C++ Testbench for 4-Core CVA6 + 512 KiB 16-Way Write-Back Shared L2 Cache Baseline
// Loads compiled RISC-V ELF64 binaries directly into DRAM and reports RTL performance + CACTI 7.0 L2 Power.

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <elf.h>
#include <string>
#include <vector>

#include "Vcva6_4core_soc_top.h"
#include "Vcva6_4core_soc_top___024root.h"
#include "verilated.h"

static constexpr uint64_t DRAM_BASE = 0x80000000ULL;
static constexpr uint64_t DRAM_SIZE = 32ULL * 1024ULL * 1024ULL;

static bool load_elf64(const char *path, Vcva6_4core_soc_top *top) {
    FILE *fp = std::fopen(path, "rb");
    if (!fp) {
        std::fprintf(stderr, "[ERROR] Cannot open ELF file: %s\n", path);
        return false;
    }

    Elf64_Ehdr ehdr;
    if (std::fread(&ehdr, sizeof(ehdr), 1, fp) != 1) {
        std::fclose(fp);
        return false;
    }
    if (std::memcmp(ehdr.e_ident, ELFMAG, SELFMAG) != 0 || ehdr.e_machine != EM_RISCV) {
        std::fprintf(stderr, "[ERROR] Not a valid RISC-V ELF64 binary: %s\n", path);
        std::fclose(fp);
        return false;
    }

    for (int i = 0; i < ehdr.e_phnum; i++) {
        Elf64_Phdr phdr;
        std::fseek(fp, ehdr.e_phoff + i * sizeof(Elf64_Phdr), SEEK_SET);
        if (std::fread(&phdr, sizeof(phdr), 1, fp) != 1) continue;
        if (phdr.p_type != PT_LOAD || phdr.p_memsz == 0) continue;

        uint64_t paddr = phdr.p_paddr;
        if (paddr < DRAM_BASE || (paddr + phdr.p_memsz) > (DRAM_BASE + DRAM_SIZE)) {
            std::fprintf(stderr, "[ERROR] Segment out of DRAM range: 0x%llx\n",
                         (unsigned long long)paddr);
            std::fclose(fp);
            return false;
        }

        std::vector<uint8_t> buf(phdr.p_filesz, 0);
        std::fseek(fp, phdr.p_offset, SEEK_SET);
        if (phdr.p_filesz > 0 && std::fread(buf.data(), 1, phdr.p_filesz, fp) != phdr.p_filesz) {
            std::fclose(fp);
            return false;
        }

        for (uint64_t off = 0; off < phdr.p_memsz; off++) {
            uint64_t addr = paddr + off;
            uint64_t word_idx = (addr - DRAM_BASE) >> 3;
            uint64_t byte_shift = (addr & 7ULL) * 8ULL;
            uint8_t bval = (off < phdr.p_filesz) ? buf[off] : 0;
            uint64_t mask = ~(0xFFULL << byte_shift);
            top->rootp->cva6_4core_soc_top__DOT__dram_mem[word_idx] =
                (top->rootp->cva6_4core_soc_top__DOT__dram_mem[word_idx] & mask) |
                ((uint64_t)bval << byte_shift);
        }
    }

    std::fclose(fp);
    return true;
}

int main(int argc, char **argv) {
    Verilated::commandArgs(argc, argv);

    const char *elf_path = nullptr;
    int active_ways = 16;
    uint64_t max_cycles = 25000000ULL;

    for (int i = 1; i < argc; i++) {
        if (std::strncmp(argv[i], "+ELF=", 5) == 0) {
            elf_path = argv[i] + 5;
        } else if (std::strncmp(argv[i], "+L2_WAYS=", 9) == 0) {
            active_ways = std::atoi(argv[i] + 9);
        } else if (std::strncmp(argv[i], "+MAX_CYCLES=", 12) == 0) {
            max_cycles = std::strtoull(argv[i] + 12, nullptr, 10);
        }
    }

    if (!elf_path) {
        std::fprintf(stderr, "Usage: %s +ELF=<path/to/bm.elf> [+L2_WAYS=16] [+MAX_CYCLES=25000000]\n", argv[0]);
        return 1;
    }
    if (active_ways < 1 || active_ways > 16) {
        std::fprintf(stderr, "[ERROR] +L2_WAYS must be 1..16\n");
        return 1;
    }

    uint16_t way_mask = (active_ways == 16) ? 0xFFFFU : (uint16_t)((1U << active_ways) - 1U);

    Vcva6_4core_soc_top *top = new Vcva6_4core_soc_top;

    // Clear simulated DRAM and load ELF64 binary
    for (size_t i = 0; i < (DRAM_SIZE / 8); i++) {
        top->rootp->cva6_4core_soc_top__DOT__dram_mem[i] = 0ULL;
    }
    if (!load_elf64(elf_path, top)) {
        delete top;
        return 1;
    }

    // Reset sequence
    top->clk_i = 0;
    top->rst_ni = 0;
    top->l2_way_en_i = way_mask;
    for (int r = 0; r < 6; r++) {
        top->clk_i = !top->clk_i;
        top->eval();
    }
    top->rst_ni = 1;

    // Main simulation loop
    uint64_t cyc = 0;
    while (cyc < max_cycles && !Verilated::gotFinish()) {
        top->clk_i = 1;
        top->eval();
        top->clk_i = 0;
        top->eval();
        cyc++;
        if (top->tohost_o != 0ULL) {
            break;
        }
    }

    uint64_t total_insts = 0;
    uint64_t total_l1d_acc = 0, total_l1d_miss = 0;
    for (int c = 0; c < 4; c++) {
        total_insts    += top->core_instret_o[c];
        total_l1d_acc  += top->core_l1d_acc_o[c];
        total_l1d_miss += top->core_l1d_miss_o[c];
    }

    double agg_ipc = (top->soc_cycles_o > 0) ? ((double)total_insts / (double)top->soc_cycles_o) : 0.0;
    double l2_miss_rate = (top->l2_accesses_o > 0)
        ? ((double)top->l2_misses_o / (double)top->l2_accesses_o * 100.0)
        : 0.0;

    // CACTI 7.0 (22nm, 512 KiB, 16-Way, 64B Line) Power Model
    // Dynamic Read = 19.6445 pJ (1.2278 pJ/way), Dynamic Write = 20.8143 pJ
    // Leakage (16 ways ON) = 111.726 mW (Cell leakage = 93.685 mW = 5.8553 mW/way; Periph = 18.041 mW)
    const double e_read_per_way_nj = 0.0196445 / 16.0;
    const double e_write_l2_nj     = 0.0208143;
    const double p_leak_way_mw     = 93.6846 / 16.0;
    const double p_leak_periph_mw  = 18.0414;
    const double p_gated_ratio     = 0.04;
    const double e_dram_access_nj  = 0.650; // Off-chip DRAM 64B refill/writeback energy (nJ)

    double sim_sec = (double)top->soc_cycles_o * 1e-9; // 1 GHz clock
    int gated_ways = 16 - active_ways;
    double l2_leak_power_mw = p_leak_periph_mw
                            + active_ways * p_leak_way_mw
                            + gated_ways * p_leak_way_mw * p_gated_ratio;
    double l2_dyn_energy_nj = (double)top->l2_read_acc_o * active_ways * e_read_per_way_nj
                            + (double)top->l2_write_acc_o * e_write_l2_nj;
    double l2_leak_energy_nj = l2_leak_power_mw * sim_sec * 1e6;
    double dram_energy_nj = (double)(top->l2_misses_o + top->l2_writebacks_o) * e_dram_access_nj;
    double total_energy_nj = l2_dyn_energy_nj + l2_leak_energy_nj + dram_energy_nj;

    std::printf("====================================================================\n");
    std::printf("[CVA6-4Core-L2-RTL] ELF              : %s\n", elf_path);
    std::printf("[CVA6-4Core-L2-RTL] Verdict          : %s (tohost=0x%llx, checksum=0x%016llx)\n",
                ((top->tohost_o & 1ULL) == 1ULL) ? "PASS" : "TIMEOUT/FAIL",
                (unsigned long long)top->tohost_o,
                (unsigned long long)top->tohost_checksum_o);
    std::printf("[CVA6-4Core-L2-RTL] Active L2 Ways   : %d / 16 (mask=0x%04x)\n", active_ways, way_mask);
    std::printf("[CVA6-4Core-L2-RTL] SoC Cycles       : %llu\n", (unsigned long long)top->soc_cycles_o);
    std::printf("[CVA6-4Core-L2-RTL] Total 4-Core Inst: %llu (Aggregate IPC = %.4f)\n",
                (unsigned long long)total_insts, agg_ipc);
    for (int c = 0; c < 4; c++) {
        std::printf("  Core %d: insts=%llu, l1d_acc=%llu, l1d_miss=%llu, l2_acc=%llu, l2_hit=%llu, l2_miss=%llu\n",
                    c,
                    (unsigned long long)top->core_instret_o[c],
                    (unsigned long long)top->core_l1d_acc_o[c],
                    (unsigned long long)top->core_l1d_miss_o[c],
                    (unsigned long long)top->l2_core_acc_o[c],
                    (unsigned long long)top->l2_core_hits_o[c],
                    (unsigned long long)top->l2_core_misses_o[c]);
    }
    std::printf("[CVA6-4Core-L2-RTL] L2 Accesses      : %llu (Read=%llu, Write=%llu)\n",
                (unsigned long long)top->l2_accesses_o,
                (unsigned long long)top->l2_read_acc_o,
                (unsigned long long)top->l2_write_acc_o);
    std::printf("[CVA6-4Core-L2-RTL] L2 Hits / Misses : %llu / %llu (Miss Rate = %.2f%%)\n",
                (unsigned long long)top->l2_hits_o,
                (unsigned long long)top->l2_misses_o,
                l2_miss_rate);
    std::printf("[CVA6-4Core-L2-RTL] L2 Dirty WB Evict: %llu\n",
                (unsigned long long)top->l2_writebacks_o);
    std::printf("[CVA6-4Core-L2-RTL] L2 Leakage Power : %.3f mW\n", l2_leak_power_mw);
    std::printf("[CVA6-4Core-L2-RTL] L2 Dynamic Energy: %.2f nJ\n", l2_dyn_energy_nj);
    std::printf("[CVA6-4Core-L2-RTL] L2 Leakage Energy: %.2f nJ\n", l2_leak_energy_nj);
    std::printf("[CVA6-4Core-L2-RTL] DRAM Miss+WB Ener: %.2f nJ\n", dram_energy_nj);
    std::printf("[CVA6-4Core-L2-RTL] Total L2+DRAM En : %.2f nJ\n", total_energy_nj);
    std::printf("CSV_LINE,%s,%d,%llu,%llu,%.4f,%llu,%llu,%llu,%.2f,%llu,%.3f,%.2f,%.2f,%.2f,%.2f,0x%016llx\n",
                elf_path, active_ways,
                (unsigned long long)top->soc_cycles_o,
                (unsigned long long)total_insts,
                agg_ipc,
                (unsigned long long)top->l2_accesses_o,
                (unsigned long long)top->l2_hits_o,
                (unsigned long long)top->l2_misses_o,
                l2_miss_rate,
                (unsigned long long)top->l2_writebacks_o,
                l2_leak_power_mw,
                l2_dyn_energy_nj,
                l2_leak_energy_nj,
                dram_energy_nj,
                total_energy_nj,
                (unsigned long long)top->tohost_checksum_o);
    std::printf("====================================================================\n");

    int rc = ((top->tohost_o & 1ULL) == 1ULL) ? 0 : 2;
    delete top;
    return rc;
}
