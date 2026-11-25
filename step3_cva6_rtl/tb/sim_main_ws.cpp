// Copyright 2026 Gem5 x CVA6 Project
// Verilator C++ Testbench (Step 3):
// 4-Core CVA6 + 512 KiB 16-Way Write-Back Shared L2 + atd_dirty_aware Way-Shutdown RTL

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <elf.h>
#include <string>
#include <vector>

#include "Vcva6_4core_soc_ws_top.h"
#include "Vcva6_4core_soc_ws_top___024root.h"
#include "verilated.h"

static constexpr uint64_t DRAM_BASE = 0x80000000ULL;
static constexpr uint64_t DRAM_SIZE = 32ULL * 1024ULL * 1024ULL;

static bool load_elf64(const char *path, Vcva6_4core_soc_ws_top *top) {
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
            top->rootp->cva6_4core_soc_ws_top__DOT__dram_mem[word_idx] =
                (top->rootp->cva6_4core_soc_ws_top__DOT__dram_mem[word_idx] & mask) |
                ((uint64_t)bval << byte_shift);
        }
    }

    std::fclose(fp);
    return true;
}

int main(int argc, char **argv) {
    Verilated::commandArgs(argc, argv);

    const char *elf_path = nullptr;
    int ws_enable = 1;
    uint64_t max_cycles = 25000000ULL;

    for (int i = 1; i < argc; i++) {
        if (std::strncmp(argv[i], "+ELF=", 5) == 0) {
            elf_path = argv[i] + 5;
        } else if (std::strncmp(argv[i], "+WS_EN=", 7) == 0) {
            ws_enable = std::atoi(argv[i] + 7);
        } else if (std::strncmp(argv[i], "+MAX_CYCLES=", 12) == 0) {
            max_cycles = std::strtoull(argv[i] + 12, nullptr, 10);
        }
    }

    if (!elf_path) {
        std::fprintf(stderr, "Usage: %s +ELF=<path/to/bm.elf> [+WS_EN=1] [+MAX_CYCLES=25000000]\n", argv[0]);
        return 1;
    }

    Vcva6_4core_soc_ws_top *top = new Vcva6_4core_soc_ws_top;

    for (size_t i = 0; i < (DRAM_SIZE / 8); i++) {
        top->rootp->cva6_4core_soc_ws_top__DOT__dram_mem[i] = 0ULL;
    }
    if (!load_elf64(elf_path, top)) {
        delete top;
        return 1;
    }

    // Reset sequence
    top->clk_i       = 0;
    top->rst_ni      = 0;
    top->ws_enable_i = (ws_enable != 0) ? 1 : 0;
    for (int r = 0; r < 6; r++) {
        top->clk_i = !top->clk_i;
        top->eval();
    }
    top->rst_ni = 1;

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
    for (int c = 0; c < 4; c++) {
        total_insts += top->core_instret_o[c];
    }

    double agg_ipc = (top->soc_cycles_o > 0) ? ((double)total_insts / (double)top->soc_cycles_o) : 0.0;
    double l2_miss_rate = (top->l2_accesses_o > 0)
        ? ((double)top->l2_misses_o / (double)top->l2_accesses_o * 100.0)
        : 0.0;
    double avg_active_ways = (top->soc_cycles_o > 0)
        ? ((double)top->ws_active_way_cycles_o / (double)top->soc_cycles_o)
        : 16.0;
    if (avg_active_ways < 1.0) avg_active_ways = 1.0;
    if (avg_active_ways > 16.0) avg_active_ways = 16.0;

    // CACTI 7.0 (22nm, 512 KiB, 16-Way, 64B Line) Power Model (identical constants to Step 1)
    const double e_read_per_way_nj = 0.0196445 / 16.0;
    const double e_write_l2_nj     = 0.0208143;
    const double p_leak_way_mw     = 93.6846 / 16.0;
    const double p_leak_periph_mw  = 18.0414;
    const double p_gated_ratio     = 0.04;
    const double e_dram_access_nj  = 0.650;

    double sim_sec = (double)top->soc_cycles_o * 1e-9; // 1 GHz
    double gated_ways = 16.0 - avg_active_ways;
    double l2_leak_power_mw = p_leak_periph_mw
                            + avg_active_ways * p_leak_way_mw
                            + gated_ways * p_leak_way_mw * p_gated_ratio;
    double l2_dyn_energy_nj = (double)top->l2_tag_lookups_o * e_read_per_way_nj
                            + (double)top->l2_write_acc_o * e_write_l2_nj;
    double l2_leak_energy_nj = l2_leak_power_mw * sim_sec * 1e6;
    uint64_t total_wb = top->l2_writebacks_o + top->l2_shutdown_flushes_o;
    double dram_energy_nj = (double)(top->l2_misses_o + total_wb) * e_dram_access_nj;
    double total_energy_nj = l2_dyn_energy_nj + l2_leak_energy_nj + dram_energy_nj;

    std::printf("====================================================================\n");
    std::printf("[CVA6-4Core-L2-WS-RTL] ELF              : %s\n", elf_path);
    std::printf("[CVA6-4Core-L2-WS-RTL] Mode             : %s\n", ws_enable ? "atd_dirty_aware" : "static16");
    std::printf("[CVA6-4Core-L2-WS-RTL] Verdict          : %s (tohost=0x%llx, checksum=0x%016llx)\n",
                ((top->tohost_o & 1ULL) == 1ULL) ? "PASS" : "TIMEOUT/FAIL",
                (unsigned long long)top->tohost_o,
                (unsigned long long)top->tohost_checksum_o);
    std::printf("[CVA6-4Core-L2-WS-RTL] Avg Active Ways  : %.2f / 16 (final mask=0x%04x, sd=0x%04x)\n",
                avg_active_ways, (unsigned)top->l2_way_en_o, (unsigned)top->l2_way_sd_o);
    std::printf("[CVA6-4Core-L2-WS-RTL] WS Transitions   : epochs=%llu, shutdowns=%llu, wakeups=%llu\n",
                (unsigned long long)top->ws_epochs_o,
                (unsigned long long)top->ws_shutdowns_o,
                (unsigned long long)top->ws_wakeups_o);
    std::printf("[CVA6-4Core-L2-WS-RTL] SoC Cycles       : %llu\n", (unsigned long long)top->soc_cycles_o);
    std::printf("[CVA6-4Core-L2-WS-RTL] Total 4-Core Inst: %llu (Aggregate IPC = %.4f)\n",
                (unsigned long long)total_insts, agg_ipc);
    std::printf("[CVA6-4Core-L2-WS-RTL] L2 Accesses      : %llu (Hits=%llu, Misses=%llu, Miss=%.2f%%)\n",
                (unsigned long long)top->l2_accesses_o,
                (unsigned long long)top->l2_hits_o,
                (unsigned long long)top->l2_misses_o,
                l2_miss_rate);
    std::printf("[CVA6-4Core-L2-WS-RTL] L2 Dirty WB      : normal=%llu, shutdown_flush=%llu\n",
                (unsigned long long)top->l2_writebacks_o,
                (unsigned long long)top->l2_shutdown_flushes_o);
    std::printf("[CVA6-4Core-L2-WS-RTL] L2 Leakage Power : %.3f mW\n", l2_leak_power_mw);
    std::printf("[CVA6-4Core-L2-WS-RTL] Total L2+DRAM En : %.2f nJ (Dyn=%.2f, Leak=%.2f, DRAM=%.2f)\n",
                total_energy_nj, l2_dyn_energy_nj, l2_leak_energy_nj, dram_energy_nj);
    std::printf("CSV_LINE,%s,%.2f,%llu,%llu,%.4f,%llu,%llu,%llu,%.2f,%llu,%llu,%llu,%llu,%llu,%.3f,%.2f,%.2f,%.2f,%.2f,0x%016llx\n",
                elf_path, avg_active_ways,
                (unsigned long long)top->soc_cycles_o,
                (unsigned long long)total_insts,
                agg_ipc,
                (unsigned long long)top->l2_accesses_o,
                (unsigned long long)top->l2_hits_o,
                (unsigned long long)top->l2_misses_o,
                l2_miss_rate,
                (unsigned long long)top->l2_writebacks_o,
                (unsigned long long)top->l2_shutdown_flushes_o,
                (unsigned long long)top->ws_epochs_o,
                (unsigned long long)top->ws_shutdowns_o,
                (unsigned long long)top->ws_wakeups_o,
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
