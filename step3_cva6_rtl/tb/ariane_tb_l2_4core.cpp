// Standalone Verilator C++ Testbench for 4-Core OpenHW CVA6 + 16-Way Write-Back Shared L2
// Supports +WS_EN=0 (Step 1 Baseline 16-Way) and +WS_EN=1 (Step 3 atd_dirty_aware Way-Shutdown).

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <elf.h>
#include <vector>

#include "Variane_testharness.h"
#include "Variane_testharness___024root.h"
#include "Variane_testharness__Dpi.h"
#include "verilated.h"

extern "C" {
int debug_tick(svBit* debug_req_valid, svBit /*debug_req_ready*/,
               int* debug_req_bits_addr, int* debug_req_bits_op, int* debug_req_bits_data,
               svBit /*debug_resp_valid*/, svBit* debug_resp_ready,
               int /*debug_resp_bits_resp*/, int /*debug_resp_bits_data*/) {
    if (debug_req_valid) *debug_req_valid = 0;
    if (debug_req_bits_addr) *debug_req_bits_addr = 0;
    if (debug_req_bits_op) *debug_req_bits_op = 0;
    if (debug_req_bits_data) *debug_req_bits_data = 0;
    if (debug_resp_ready) *debug_resp_ready = 1;
    return 0;
}

int jtag_tick(svBit* jtag_TCK, svBit* jtag_TMS, svBit* jtag_TDI,
              svBit* jtag_TRSTn, svBit /*jtag_TDO*/) {
    if (jtag_TCK) *jtag_TCK = 0;
    if (jtag_TMS) *jtag_TMS = 0;
    if (jtag_TDI) *jtag_TDI = 0;
    if (jtag_TRSTn) *jtag_TRSTn = 1;
    return 0;
}

void read_elf(const char* /*filename*/) {}
char get_section(long long* address, long long* len) {
    if (address) *address = 0;
    if (len) *len = 0;
    return 0;
}
void read_section_sv(long long /*address*/, const svOpenArrayHandle /*buffer*/) {}
char read_symbol(const char* /*symbol_name*/, unsigned long long* address) {
    if (address) *address = 0;
    return 0;
}
}

static constexpr uint64_t DRAM_BASE  = 0x80000000ULL;
static constexpr uint64_t DRAM_WORDS = (1ULL << 25);

#define DRAM_MEM top->rootp->ariane_testharness__DOT__i_sram__DOT__gen_cut__BRA__0__KET____DOT__i_tc_sram_wrapper__DOT__i_tc_sram__DOT__sram.m_storage

static bool load_elf64(const char *path, Variane_testharness *top) {
    FILE *fp = std::fopen(path, "rb");
    if (!fp) {
        std::fprintf(stderr, "[ERROR] Cannot open ELF: %s\n", path);
        return false;
    }

    Elf64_Ehdr ehdr;
    if (std::fread(&ehdr, sizeof(ehdr), 1, fp) != 1 ||
        std::memcmp(ehdr.e_ident, ELFMAG, SELFMAG) != 0 ||
        ehdr.e_machine != EM_RISCV) {
        std::fprintf(stderr, "[ERROR] Invalid RISC-V ELF64: %s\n", path);
        std::fclose(fp);
        return false;
    }

    for (int i = 0; i < ehdr.e_phnum; i++) {
        Elf64_Phdr phdr;
        std::fseek(fp, ehdr.e_phoff + i * sizeof(Elf64_Phdr), SEEK_SET);
        if (std::fread(&phdr, sizeof(phdr), 1, fp) != 1) continue;
        if (phdr.p_type != PT_LOAD || phdr.p_memsz == 0) continue;

        uint64_t paddr = phdr.p_paddr;
        if (paddr < DRAM_BASE) continue;

        std::vector<uint8_t> buf(phdr.p_filesz, 0);
        std::fseek(fp, phdr.p_offset, SEEK_SET);
        if (phdr.p_filesz > 0 && std::fread(buf.data(), 1, phdr.p_filesz, fp) != phdr.p_filesz) {
            std::fclose(fp);
            return false;
        }

        for (uint64_t off = 0; off < phdr.p_memsz; off++) {
            uint64_t addr = paddr + off;
            uint64_t widx = (addr - DRAM_BASE) >> 3;
            uint64_t bsh  = (addr & 7ULL) * 8ULL;
            if (widx >= DRAM_WORDS) continue;
            uint8_t bval = (off < phdr.p_filesz) ? buf[off] : 0;
            uint64_t mask = ~(0xFFULL << bsh);
            DRAM_MEM[widx] = (DRAM_MEM[widx] & mask) | ((uint64_t)bval << bsh);
        }
    }
    std::fclose(fp);
    return true;
}

int main(int argc, char **argv) {
    Verilated::commandArgs(argc, argv);

    const char *elf_path = nullptr;
    int ws_enable = 0;
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
        std::fprintf(stderr, "Usage: %s +ELF=<path/to/bm.elf> [+WS_EN=0|1] [+MAX_CYCLES=25000000]\n", argv[0]);
        return 1;
    }

    Variane_testharness *top = new Variane_testharness;
    top->clk_i  = 0;
    top->rtc_i  = 0;
    top->rst_ni = 0;
    top->rootp->ariane_testharness__DOT__l2_ws_enable = (ws_enable != 0) ? 1 : 0;

    for (int r = 0; r < 10; r++) {
        top->clk_i = 0; top->eval();
        top->clk_i = 1; top->eval();
    }

    if (!load_elf64(elf_path, top)) {
        delete top;
        return 1;
    }

    top->rst_ni = 1;

    uint64_t cyc = 0;
    uint64_t tohost = 0;
    while (cyc < max_cycles && !Verilated::gotFinish()) {
        top->clk_i = 0;
        top->eval();
        top->clk_i = 1;
        top->eval();
        if ((cyc & 1ULL) == 0ULL) {
            top->rtc_i ^= 1;
        }
        cyc++;
        if ((cyc % 100000ULL) == 0ULL) {
            std::fprintf(stderr, "[progress] cyc=%llu l2_acc=%llu l2_miss=%llu way_en=0x%04x\n",
                         (unsigned long long)cyc,
                         (unsigned long long)top->rootp->ariane_testharness__DOT__l2_cnt_accesses,
                         (unsigned long long)top->rootp->ariane_testharness__DOT__l2_cnt_misses,
                         (unsigned)top->rootp->ariane_testharness__DOT__l2_way_en_cur);
        }
        tohost = top->rootp->ariane_testharness__DOT__l2_tohost_val;
        if (tohost != 0ULL) {
            break;
        }
    }

    uint64_t l2_acc     = top->rootp->ariane_testharness__DOT__l2_cnt_accesses;
    uint64_t l2_hits    = top->rootp->ariane_testharness__DOT__l2_cnt_hits;
    uint64_t l2_miss    = top->rootp->ariane_testharness__DOT__l2_cnt_misses;
    uint64_t l2_wr      = top->rootp->ariane_testharness__DOT__l2_cnt_write_acc;
    uint64_t l2_wb      = top->rootp->ariane_testharness__DOT__l2_cnt_writebacks;
    uint64_t l2_sd_fl   = top->rootp->ariane_testharness__DOT__l2_cnt_shutdown_flushes;
    uint64_t l2_tag_lkp = top->rootp->ariane_testharness__DOT__l2_cnt_tag_lookups;
    uint64_t ws_epochs  = top->rootp->ariane_testharness__DOT__l2_ws_epochs;
    uint64_t ws_sd      = top->rootp->ariane_testharness__DOT__l2_ws_shutdowns;
    uint64_t ws_wu      = top->rootp->ariane_testharness__DOT__l2_ws_wakeups;
    uint64_t ws_act_cyc = top->rootp->ariane_testharness__DOT__l2_ws_active_way_cycles;
    unsigned way_en_cur = top->rootp->ariane_testharness__DOT__l2_way_en_cur;
    unsigned way_sd_cur = top->rootp->ariane_testharness__DOT__l2_way_sd_cur;

    double miss_rate = (l2_acc > 0) ? ((double)l2_miss / (double)l2_acc * 100.0) : 0.0;
    double avg_ways  = (cyc > 0) ? ((double)ws_act_cyc / (double)cyc) : 16.0;
    if (avg_ways < 1.0) avg_ways = 1.0;
    if (avg_ways > 16.0) avg_ways = 16.0;

    // CACTI 7.0 (22nm) Power & Energy Model (identical to Step 1 & Step 2)
    const double e_read_per_way_nj = 0.0196445 / 16.0;
    const double e_write_l2_nj     = 0.0208143;
    const double p_leak_way_mw     = 93.6846 / 16.0;
    const double p_leak_periph_mw  = 18.0414;
    const double p_gated_ratio     = 0.04;
    const double e_dram_access_nj  = 0.650;

    double sim_sec    = (double)cyc * 1e-9;
    double gated_ways = 16.0 - avg_ways;
    double l2_leak_mw = p_leak_periph_mw + avg_ways * p_leak_way_mw + gated_ways * p_leak_way_mw * p_gated_ratio;
    double l2_dyn_nj  = (double)l2_tag_lkp * e_read_per_way_nj + (double)l2_wr * e_write_l2_nj;
    double l2_leak_nj = l2_leak_mw * sim_sec * 1e6;
    double dram_nj    = (double)(l2_miss + l2_wb + l2_sd_fl) * e_dram_access_nj;
    double tot_nj     = l2_dyn_nj + l2_leak_nj + dram_nj;

    std::printf("====================================================================\n");
    std::printf("[OpenHW-CVA6-4Core-L2] ELF              : %s\n", elf_path);
    std::printf("[OpenHW-CVA6-4Core-L2] Mode             : %s\n", ws_enable ? "atd_dirty_aware" : "static16");
    std::printf("[OpenHW-CVA6-4Core-L2] Verdict          : %s (tohost=0x%llx, checksum=0x%016llx)\n",
                ((tohost & 1ULL) == 1ULL) ? "PASS" : "TIMEOUT/FAIL",
                (unsigned long long)tohost, (unsigned long long)(tohost >> 1));
    std::printf("[OpenHW-CVA6-4Core-L2] Avg Active Ways  : %.2f / 16 (final mask=0x%04x, sd=0x%04x)\n",
                avg_ways, way_en_cur, way_sd_cur);
    std::printf("[OpenHW-CVA6-4Core-L2] WS Transitions   : epochs=%llu, shutdowns=%llu, wakeups=%llu\n",
                (unsigned long long)ws_epochs, (unsigned long long)ws_sd, (unsigned long long)ws_wu);
    std::printf("[OpenHW-CVA6-4Core-L2] SoC Cycles       : %llu\n", (unsigned long long)cyc);
    std::printf("[OpenHW-CVA6-4Core-L2] L2 Accesses      : %llu (Hits=%llu, Misses=%llu, Miss=%.2f%%)\n",
                (unsigned long long)l2_acc, (unsigned long long)l2_hits, (unsigned long long)l2_miss, miss_rate);
    std::printf("[OpenHW-CVA6-4Core-L2] L2 Dirty WB      : normal=%llu, shutdown_flush=%llu\n",
                (unsigned long long)l2_wb, (unsigned long long)l2_sd_fl);
    std::printf("[OpenHW-CVA6-4Core-L2] L2 Leakage Power : %.3f mW\n", l2_leak_mw);
    std::printf("[OpenHW-CVA6-4Core-L2] Total L2+DRAM En : %.2f nJ (Dyn=%.2f, Leak=%.2f, DRAM=%.2f)\n",
                tot_nj, l2_dyn_nj, l2_leak_nj, dram_nj);
    std::printf("CSV_LINE,%s,%.2f,%llu,0,0.0000,%llu,%llu,%llu,%.2f,%llu,%llu,%llu,%llu,%llu,%.3f,%.2f,%.2f,%.2f,%.2f,0x%016llx\n",
                elf_path, avg_ways,
                (unsigned long long)cyc,
                (unsigned long long)l2_acc,
                (unsigned long long)l2_hits,
                (unsigned long long)l2_miss,
                miss_rate,
                (unsigned long long)l2_wb,
                (unsigned long long)l2_sd_fl,
                (unsigned long long)ws_epochs,
                (unsigned long long)ws_sd,
                (unsigned long long)ws_wu,
                l2_leak_mw,
                l2_dyn_nj,
                l2_leak_nj,
                dram_nj,
                tot_nj,
                (unsigned long long)(tohost >> 1));
    std::printf("====================================================================\n");

    int rc = ((tohost & 1ULL) == 1ULL) ? 0 : 2;
    delete top;
    return rc;
}
