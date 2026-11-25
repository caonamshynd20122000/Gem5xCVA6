#!/usr/bin/env python3
"""
Draw the exact current RTL architecture of /data/namcv10/gem5_cva6/cva6/
(OpenHW CVA6 fpga_linux_cv64a6 + ariane_testharness.sv).
Outputs:
  - docs/cva6_current_architecture.png
  - docs/cva6_current_architecture.svg
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch


def blk(ax, x, y, w, h, title, body="", fc="#FFFFFF", ec="#0F172A",
        lw=1.4, tsize=8.8, bsize=7.2, tc="#0F172A", bc="#334155", top=False, ls="-"):
    p = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.05,rounding_size=0.12",
        facecolor=fc, edgecolor=ec, linewidth=lw, linestyle=ls, zorder=2
    )
    ax.add_patch(p)
    if top:
        ax.text(x + w / 2, y + h - 0.14, title, ha="center", va="top",
                fontsize=tsize, fontweight="bold", color=tc, zorder=3)
        if body:
            ax.text(x + w / 2, y + h - 0.44, body, ha="center", va="top",
                    fontsize=bsize, color=bc, linespacing=1.28, zorder=3)
    else:
        if body:
            ax.text(x + w / 2, y + h * 0.67, title, ha="center", va="center",
                    fontsize=tsize, fontweight="bold", color=tc, zorder=3)
            ax.text(x + w / 2, y + h * 0.28, body, ha="center", va="center",
                    fontsize=bsize, color=bc, linespacing=1.24, zorder=3)
        else:
            ax.text(x + w / 2, y + h / 2, title, ha="center", va="center",
                    fontsize=tsize, fontweight="bold", color=tc, zorder=3)


def wire(ax, x1, y1, x2, y2, label="", color="#1E293B", lw=1.4,
         style="-|>", ldx=0.0, ldy=0.0, lsize=7.0):
    a = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle=style, mutation_scale=11,
        linewidth=lw, color=color, zorder=4
    )
    ax.add_patch(a)
    if label:
        mx = (x1 + x2) / 2 + ldx
        my = (y1 + y2) / 2 + ldy
        ax.text(mx, my, label, ha="center", va="center",
                fontsize=lsize, fontweight="bold", color=color,
                bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.92),
                zorder=5)


def main():
    fig, ax = plt.subplots(figsize=(16.5, 10.2))
    ax.set_xlim(0, 16.5)
    ax.set_ylim(0, 10.2)
    ax.axis("off")

    ax.text(8.25, 9.92,
            "Current OpenHW CVA6 Architecture in cva6/ (Target: fpga_linux_cv64a6)",
            ha="center", va="center", fontsize=13.2, fontweight="bold", color="#0F172A")
    ax.text(8.25, 9.60,
            "Top-Level TestHarness: cva6/corev_apu/tb/ariane_testharness.sv  |  Config: cva6/config/target/fpga_linux_cv64a6/rtl_cfg_pkg.sv",
            ha="center", va="center", fontsize=8.8, color="#475569")

    # Outer ariane_testharness container
    blk(ax, 0.35, 0.35, 15.8, 8.95,
        "ariane_testharness (Current Single-Core OpenHW CVA6 SoC)",
        fc="#F8FAFC", ec="#0F172A", lw=2.0, tsize=9.8, top=True)

    # ------------------------------------------------------------------
    # TOP-LEFT: i_ariane (cva6/core/cva6.sv)
    # ------------------------------------------------------------------
    blk(ax, 0.70, 5.10, 10.45, 3.65,
        "i_ariane (cva6/core/cva6.sv — RV64GC + B + Zkn, 6-Stage In-Order, Sv39 MMU, 8 PMP)",
        fc="#EFF6FF", ec="#1D4ED8", lw=1.8, tsize=9.1, tc="#1E3A8A", top=True)

    blk(ax, 0.95, 7.15, 2.35, 1.15,
        "Frontend / Fetch",
        "BTB(32), BHT(128, hist=3)\nRAS(2), Fetch FIFO\nITLB (16 entries)",
        fc="#FFFFFF", ec="#1D4ED8", lw=1.2, tsize=8.0, bsize=6.8)

    blk(ax, 3.55, 7.15, 2.30, 1.15,
        "Decode & Issue",
        "Scoreboard (8 entries)\nSingle-issue, 2-commit\nRegFile (INT + FP)",
        fc="#FFFFFF", ec="#1D4ED8", lw=1.2, tsize=8.0, bsize=6.8)

    blk(ax, 6.10, 7.15, 2.30, 1.15,
        "Execute Units",
        "ALU, MUL/DIV, Branch\nCVFPU (RVF + RVD)\nLSU + LoadBuf(8) + DTLB(16)",
        fc="#FFFFFF", ec="#1D4ED8", lw=1.2, tsize=8.0, bsize=6.8)

    blk(ax, 8.65, 7.15, 2.25, 1.15,
        "Commit & CSR",
        "2-Wide Commit Stage\nM/S/U CSRs, RVFI Trace\nPTW + PMP(8)",
        fc="#FFFFFF", ec="#1D4ED8", lw=1.2, tsize=8.0, bsize=6.8)

    wire(ax, 3.30, 7.72, 3.55, 7.72, color="#1D4ED8", lw=1.3)
    wire(ax, 5.85, 7.72, 6.10, 7.72, color="#1D4ED8", lw=1.3)
    wire(ax, 8.40, 7.72, 8.65, 7.72, color="#1D4ED8", lw=1.3)

    # Cache Subsystem inside cva6.sv (MEM_HPDCACHE_AXI)
    blk(ax, 0.95, 5.32, 9.95, 1.50,
        "cva6_hpdcache_subsystem (MemSubsystem = MEM_HPDCACHE_AXI)",
        fc="#DBEAFE", ec="#1D4ED8", lw=1.4, tsize=8.3, tc="#1E3A8A", top=True)

    blk(ax, 1.18, 5.48, 3.00, 0.92,
        "L1 I-Cache (HPIcache)",
        "16 KiB, 4-Way, 128-bit line",
        fc="#FFFFFF", ec="#1D4ED8", lw=1.1, tsize=7.9, bsize=6.8)

    blk(ax, 4.42, 5.48, 3.25, 0.92,
        "L1 D-Cache (HPDcache)",
        "32 KiB, 8-Way, 128-bit line\nWrite-Through (CACHE_WT), Wbuf(8)",
        fc="#FFFFFF", ec="#1D4ED8", lw=1.1, tsize=7.9, bsize=6.7)

    blk(ax, 7.90, 5.48, 2.80, 0.92,
        "AXI4 Arbiter",
        "noc_req_o / noc_resp_i\n64b Addr, 64b Data, 5b ID",
        fc="#FEF3C7", ec="#B45309", lw=1.2, tsize=7.9, bsize=6.7)

    wire(ax, 2.12, 7.15, 2.12, 6.40, style="<|-|>", color="#1D4ED8", lw=1.2)
    wire(ax, 7.25, 7.15, 6.20, 6.40, style="<|-|>", color="#1D4ED8", lw=1.2)
    wire(ax, 4.18, 5.94, 4.42, 5.94, color="#1D4ED8", lw=1.1)
    wire(ax, 7.67, 5.94, 7.90, 5.94, style="<|-|>", color="#B45309", lw=1.2)

    # ------------------------------------------------------------------
    # TOP-RIGHT: Debug Module (dm_top) -> slave[1]
    # ------------------------------------------------------------------
    blk(ax, 11.75, 5.75, 4.05, 3.00,
        "Debug Module (dm_top)",
        "RISC-V Debug Spec 0.13\nJTAG / DMI Interface\n\n"
        "• Master Port -> slave[1]\n"
        "• Slave Port  <- master[Debug]\n"
        "• debug_req_o -> i_ariane",
        fc="#F1F5F9", ec="#475569", lw=1.5, tsize=8.8, bsize=7.2, top=True)

    wire(ax, 11.75, 7.72, 11.15, 7.72, label="debug_req", color="#475569", lw=1.2, ldy=0.18, lsize=6.7)

    # ------------------------------------------------------------------
    # MIDDLE: axi_xbar (NrSlaves=2 -> NB_PERIPHERALS=10)
    # ------------------------------------------------------------------
    blk(ax, 0.70, 3.65, 15.10, 0.95,
        "axi_xbar (PULP AXI4 Crossbar — NrSlaves = 2 -> NB_PERIPHERALS = 10)",
        "Slaves: slave[0] = i_ariane (5b ID), slave[1] = Debug Module  |  Masters: 6b ID (IdWidthSlave = 5 + $clog2(2))\n"
        "Address Map: 0x0000_0000 Debug | 0x0001_0000 ROM | 0x0200_0000 CLINT | 0x0C00_0000 PLIC | 0x1000_0000 UART | 0x8000_0000 DRAM",
        fc="#FEF3C7", ec="#B45309", lw=1.6, tsize=9.0, bsize=7.1)

    wire(ax, 9.30, 5.10, 9.30, 4.60,
         label="slave[0]: axi_ariane_req / resp (AXI4)", color="#B45309", lw=1.6, ldx=-1.95, lsize=7.0)
    wire(ax, 13.75, 5.75, 13.75, 4.60,
         label="slave[1]: dm_axi_m", color="#475569", lw=1.4, ldx=0.85, lsize=6.9)

    # ------------------------------------------------------------------
    # BOTTOM-LEFT: DRAM Path (CURRENTLY NO L2 CACHE!)
    # ------------------------------------------------------------------
    blk(ax, 0.70, 0.65, 9.55, 2.35,
        "DRAM Memory Path (master[ariane_soc::DRAM] @ 0x8000_0000 — NO L2 CACHE YET)",
        fc="#FFF1F2", ec="#BE123C", lw=1.6, ls="--", tsize=8.8, tc="#9F1239", top=True)

    blk(ax, 0.95, 0.95, 2.50, 1.40,
        "axi_cut (dram)",
        "Register slice on\nmaster[DRAM]\nAXI4 64-bit",
        fc="#FFFFFF", ec="#BE123C", lw=1.2, tsize=8.0, bsize=6.8)

    blk(ax, 4.00, 0.95, 2.75, 1.40,
        "axi_delayer\n(dram_delayed)",
        "Configurable AXI4\nlatency injection\n(Insertion Point for L2)",
        fc="#FFE4E6", ec="#BE123C", lw=1.3, tsize=8.0, bsize=6.8)

    blk(ax, 7.30, 0.95, 2.70, 1.40,
        "axi2mem + sram",
        "24 MiB / 1 GiB DRAM\nELF loaded via DPI\n(elfloader.cc)",
        fc="#FFFFFF", ec="#475569", lw=1.3, tsize=8.0, bsize=6.8)

    wire(ax, 2.20, 3.65, 2.20, 2.35,
         label="master[0] (DRAM, AXI4)", color="#BE123C", lw=1.6, ldx=1.15, lsize=7.0)
    wire(ax, 3.45, 1.65, 4.00, 1.65, color="#BE123C", lw=1.4)
    wire(ax, 6.75, 1.65, 7.30, 1.65, color="#475569", lw=1.4)

    # ------------------------------------------------------------------
    # BOTTOM-RIGHT: SoC Peripherals (master[1..9])
    # ------------------------------------------------------------------
    blk(ax, 10.65, 0.65, 5.15, 2.35,
        "SoC Peripherals (master[1..9])",
        "• BootROM (0x0001_0000, bootrom.sv)\n"
        "• CLINT (0x0200_0000) & PLIC (0x0C00_0000)\n"
        "• UART (0x1000_0000) & Timer (0x1800_0000)\n"
        "• SPI, Ethernet, GPIO, Debug Slave\n"
        "• Connected via axi2apb / axi_lite",
        fc="#F1F5F9", ec="#475569", lw=1.4, tsize=8.8, bsize=7.1, top=True)

    wire(ax, 13.20, 3.65, 13.20, 3.00,
         label="master[1..9] (AXI4)", color="#475569", lw=1.4, ldx=0.95, lsize=7.0)

    docs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs"))
    out_png = os.path.join(docs_dir, "cva6_current_architecture.png")
    out_svg = os.path.join(docs_dir, "cva6_current_architecture.svg")
    plt.tight_layout(pad=0.25)
    plt.savefig(out_png, dpi=180, bbox_inches="tight", facecolor="white")
    plt.savefig(out_svg, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[OK] Saved:\n  - {out_png}\n  - {out_svg}")


if __name__ == "__main__":
    main()
