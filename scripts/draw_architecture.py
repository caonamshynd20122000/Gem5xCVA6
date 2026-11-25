#!/usr/bin/env python3
"""
Generate high-resolution architecture diagram for Gem 5 x CVA6:
4-Core CVA6 Multicore Cluster + Private L1 (I$/D$) + Shared L2 Cache with Way-Shutdown Controller,
and 1-to-1 gem5 v26.0 Multicore Model + CACTI 7.0 L2 Power Evaluation.
"""

import os

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch


def draw_box(ax, x, y, w, h, title, subtitle="", fc="#F8FAFC", ec="#334155",
             lw=1.4, title_size=9.3, sub_size=7.4, title_color="#0F172A",
             sub_color="#334155", bold=True, align_top=False, linestyle="-",
             title_ha="center"):
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.015,rounding_size=0.08",
        facecolor=fc, edgecolor=ec, linewidth=lw, linestyle=linestyle, zorder=2
    )
    ax.add_patch(box)
    weight = "bold" if bold else "normal"
    tx = x + w / 2 if title_ha == "center" else x + 0.18
    if align_top:
        ax.text(tx, y + h - 0.13, title, ha=title_ha, va="top",
                fontsize=title_size, fontweight=weight, color=title_color, zorder=3)
        if subtitle:
            ax.text(x + w / 2, y + h - 0.40, subtitle, ha="center", va="top",
                    fontsize=sub_size, color=sub_color, zorder=3, linespacing=1.25)
    else:
        if subtitle:
            ax.text(x + w / 2, y + h * 0.65, title, ha="center", va="center",
                    fontsize=title_size, fontweight=weight, color=title_color, zorder=3)
            ax.text(x + w / 2, y + h * 0.27, subtitle, ha="center", va="center",
                    fontsize=sub_size, color=sub_color, zorder=3, linespacing=1.18)
        else:
            ax.text(x + w / 2, y + h / 2, title, ha="center", va="center",
                    fontsize=title_size, fontweight=weight, color=title_color, zorder=3)


def arrow(ax, x1, y1, x2, y2, color="#334155", lw=1.4, style="-|>", ls="-", rad=0.0):
    arr = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle=style, mutation_scale=11,
        color=color, linewidth=lw, linestyle=ls,
        connectionstyle=f"arc3,rad={rad}", zorder=4
    )
    ax.add_patch(arr)


def main():
    fig, ax = plt.subplots(figsize=(18.8, 12.2), dpi=180)
    ax.set_xlim(0, 18.8)
    ax.set_ylim(0, 12.2)
    ax.axis("off")
    fig.patch.set_facecolor("#FFFFFF")

    # Main Title
    ax.text(9.4, 11.88,
            "Gem 5 x CVA6 — 4-Core CVA6 Cluster & Shared L2 Cache Way-Shutdown Architecture",
            ha="center", va="center", fontsize=14.8, fontweight="bold", color="#0F172A")
    ax.text(9.4, 11.55,
            "Left: 4x CVA6 Core Tiles (Private L1 I$/D$) + L1-to-L2 Coherent XBar/NoC + Shared L2 Cache with Way-Shutdown  |  Right: 1-to-1 gem5 v26.0 4-Core Model + CACTI 7.0",
            ha="center", va="center", fontsize=9.1, color="#475569")

    # =========================================================================
    # LEFT PANEL: 4-CORE CVA6 SOC + SHARED L2 CACHE (RTL TARGET)
    # =========================================================================
    draw_box(ax, 0.25, 0.30, 11.80, 11.00,
             "4-CORE CVA6 MULTICORE CLUSTER  (4x RV64GC Core Tiles + Shared L2 Cache Target)",
             fc="#F8FAFC", ec="#1E3A8A", lw=2.0, title_size=11.0, title_color="#1E3A8A", align_top=True)

    # --- 4x CVA6 Core Tiles (Core 0 .. Core 3) ---
    tile_w = 2.68
    tile_gap = 0.19
    tile_y = 8.15
    tile_h = 2.65
    tile_centers = []

    for c in range(4):
        tx = 0.48 + c * (tile_w + tile_gap)
        tc = tx + tile_w / 2
        tile_centers.append(tc)

        draw_box(ax, tx, tile_y, tile_w, tile_h,
                 f"CVA6 Core Tile {c}",
                 fc="#EFF6FF", ec="#2563EB", lw=1.5, title_size=9.2, title_color="#1D4ED8", align_top=True)

        # Core pipeline inside tile
        draw_box(ax, tx + 0.12, tile_y + 1.48, tile_w - 0.24, 0.78,
                 f"CVA6 Core {c} (RV64GC)",
                 "6-Stage In-Order (1-issue, 2-commit)\nBHT(128) BTB(32) Scoreboard(8)",
                 fc="#FFFFFF", ec="#3B82F6", lw=1.1, title_size=8.0, sub_size=6.5)

        # Private L1I & L1D inside tile
        l1_w = (tile_w - 0.32) / 2
        draw_box(ax, tx + 0.12, tile_y + 0.52, l1_w, 0.76,
                 "L1 I-Cache",
                 "16 KiB | 4-Way\nRead-Only",
                 fc="#ECFDF5", ec="#059669", lw=1.1, title_size=7.6, sub_size=6.4, title_color="#065F46")
        draw_box(ax, tx + 0.20 + l1_w, tile_y + 0.52, l1_w, 0.76,
                 "L1 D-Cache",
                 "32 KiB | 8-Way\nWT + Inval",
                 fc="#FEF3C7", ec="#D97706", lw=1.1, title_size=7.6, sub_size=6.4, title_color="#92400E")

        # Arrows Core <-> L1I/L1D
        arrow(ax, tx + 0.12 + l1_w / 2, tile_y + 1.48, tx + 0.12 + l1_w / 2, tile_y + 1.29,
              color="#059669", lw=1.1, style="<|-|>")
        arrow(ax, tx + 0.20 + l1_w * 1.5, tile_y + 1.48, tx + 0.20 + l1_w * 1.5, tile_y + 1.29,
              color="#D97706", lw=1.1, style="<|-|>")

        # Tile L1 Arbiter bar
        draw_box(ax, tx + 0.12, tile_y + 0.10, tile_w - 0.24, 0.30,
                 f"Tile {c} AXI/L1.5 Port + Inval",
                 fc="#E0F2FE", ec="#0284C7", lw=1.0, title_size=7.1, title_color="#0369A1")

    # --- L1-to-L2 Coherent Interconnect (Crossbar / NoC) ---
    draw_box(ax, 0.48, 7.05, 11.30, 0.75,
             "L1-to-L2 Coherent Interconnect  (4-Port Coherent Crossbar / NoC — L2XBar)",
             "Routes L1I Misses + L1D Read Misses + L1D Write-Through Stream to Shared L2  |  Broadcasts L2 -> L1 Invalidations",
             fc="#DBEAFE", ec="#1D4ED8", lw=1.6, title_size=9.2, sub_size=7.4, title_color="#1E3A8A")

    for tc in tile_centers:
        arrow(ax, tc, 8.15, tc, 7.82, color="#1D4ED8", lw=1.6, style="<|-|>")

    # =========================================================================
    # SHARED L2 CACHE (MAIN FOCUS BOX — WAY-SHUTDOWN TARGET!)
    # =========================================================================
    draw_box(ax, 0.48, 2.30, 11.30, 4.40,
             "★ TARGET: SHARED L2 CACHE  (512 KiB, 16-Way Set-Associative, 32 KiB/Way, Write-Back) + WAY-SHUTDOWN",
             fc="#FFFBEB", ec="#D97706", lw=2.1, title_size=9.6, title_color="#92400E",
             align_top=True, title_ha="left")

    # Arrows from L1-to-L2 XBar into Shared L2
    arrow(ax, 3.35, 7.05, 3.35, 6.72, color="#B45309", lw=1.8, style="<|-|>")
    ax.text(3.50, 6.88, "4-Core L1 Requests & Fills (64b/128b)", ha="left", va="center",
            fontsize=7.3, color="#92400E", fontweight="bold")

    # Inside L2: Request Queue + Pipeline Controller + Directory
    draw_box(ax, 0.72, 5.45, 4.10, 0.82,
             "L2 Bank Controller & Coherence Directory",
             "Handles 4-Core L1 Misses, L1 WT Stores & L1 Inval Broadcast\nTracks Core Requestor ID (core_id = 0..3) & Tag/Set Lookup",
             fc="#FFFFFF", ec="#D97706", lw=1.3, title_size=8.3, sub_size=6.9)

    # Inside L2: Victim Selector
    draw_box(ax, 5.05, 5.45, 2.95, 0.82,
             "L2 Replacement & Victim Selector",
             "PLRU / SRRIP / Random / LRU\n(Allocation & eviction masked by way_en[W-1:0])",
             fc="#FEF3C7", ec="#B45309", lw=1.3, title_size=8.2, sub_size=6.9)

    # Inside L2: NEW Way-Shutdown Controller (Hero Purple Box)
    draw_box(ax, 8.70, 3.35, 2.85, 2.92,
             "★ L2 Way-Shutdown Ctrl",
             "• Epoch & Hysteresis FSM\n• Sampled-Set ATD (Tag-Only)\n  Estimates marginal hits per way\n• Per-Way & Per-Core (0..3)\n  Activity / Utility Counters\n• Dirty-Way Flush FSM (before PG)\n  & Wakeup Timer (T_wakeup)\n• CSR / MMIO Config & Perf Regs\n\nOutputs:\n  way_en[W-1:0]  (Active Mask)\n  way_sd[W-1:0]  (SRAM Sleep/PG)",
             fc="#FAF5FF", ec="#9333EA", lw=2.1, title_size=9.0, sub_size=6.9,
             title_color="#6B21A8", align_top=True)

    # Arrows: L2 Ctrl -> Victim Sel <-- Way-Shutdown Ctrl
    arrow(ax, 4.82, 5.86, 5.05, 5.86, color="#B45309", lw=1.3)
    arrow(ax, 8.70, 5.86, 8.02, 5.86, color="#9333EA", lw=1.6)
    ax.text(8.36, 5.96, "way_en\nmask", ha="center", va="bottom", fontsize=6.8, color="#7E22CE", fontweight="bold")

    # Shared L2 Tag + Data SRAM Way Banks (16 Independent Ways: W0 .. W15)
    draw_box(ax, 0.72, 3.35, 7.28, 1.85,
             "Shared L2 Tag + Data SRAM Banks  (16 Independent Ways x 32 KiB = 512 KiB, Write-Back)",
             fc="#FFFFFF", ec="#D97706", lw=1.3, title_size=8.3, title_color="#92400E", align_top=True)

    for w in range(16):
        wx = 0.84 + w * 0.442
        is_on = w < 8
        wfc = "#DCFCE7" if is_on else "#E2E8F0"
        wec = "#16A34A" if is_on else "#64748B"
        wtxt = "ON" if is_on else "OFF\n(PG)"
        wcol = "#166534" if is_on else "#475569"
        ls_w = "-" if is_on else "--"
        draw_box(ax, wx, 3.74, 0.40, 1.08, f"W{w}", wtxt,
                 fc=wfc, ec=wec, lw=1.0, title_size=6.8, sub_size=5.8,
                 title_color=wcol, sub_color=wcol, linestyle=ls_w)

    ax.text(4.36, 3.52,
            "16-Way Write-Back L2: Shutdown (1->0) flushes dirty lines in target way + gates SRAM power (saves up to 75-87% L2 Leakage)",
            ha="center", va="center", fontsize=6.7, color="#047857", fontweight="bold")

    # Arrows: L2 Ctrl <-> SRAM, Way-Shutdown -> SRAM
    arrow(ax, 2.75, 5.45, 2.75, 5.21, color="#B45309", lw=1.4, style="<|-|>")
    arrow(ax, 8.70, 4.30, 8.02, 4.30, color="#9333EA", lw=1.6)
    ax.text(8.36, 4.42, "cs gate,\nsd & flush", ha="center", va="bottom", fontsize=6.8, color="#7E22CE", fontweight="bold")

    # L2 Bottom row: MSHR + Writeback Buffer + Prefetcher/DMA
    draw_box(ax, 0.72, 2.45, 3.50, 0.68,
             "L2 MSHR & Fill Handler",
             "16-32 MSHRs (coalesces 4-core misses) -> DRAM Read",
             fc="#FFFFFF", ec="#D97706", lw=1.1, title_size=7.9, sub_size=6.8)
    draw_box(ax, 4.45, 2.45, 3.55, 0.68,
             "L2 Writeback & Way-Flush Buffer",
             "Evicts dirty lines on replacement or Way-Shutdown (1->0)",
             fc="#FFFFFF", ec="#D97706", lw=1.1, title_size=7.9, sub_size=6.8)
    draw_box(ax, 8.70, 2.45, 2.85, 0.68,
             "L2 Performance & Power Counters",
             "active_way_cycles, per_core_hits, flushes",
             fc="#FAF5FF", ec="#9333EA", lw=1.1, title_size=7.8, sub_size=6.8, title_color="#6B21A8")

    arrow(ax, 2.47, 3.35, 2.47, 3.14, color="#B45309", lw=1.2)
    arrow(ax, 6.22, 3.35, 6.22, 3.14, color="#B45309", lw=1.2)
    arrow(ax, 10.12, 3.35, 10.12, 3.14, color="#9333EA", lw=1.2)

    # --- SoC System Bus (AXI4 Crossbar below L2) ---
    draw_box(ax, 0.48, 1.32, 11.30, 0.65,
             "SoC System Interconnect: axi_xbar_intf  (64/128-bit AXI4 Memory Bus — SystemXBar)",
             "Connects Shared L2 Cache Miss/Writeback Port & Uncached Requests to Main Memory (DRAM) and Peripherals",
             fc="#E0F2FE", ec="#0284C7", lw=1.5, title_size=8.8, sub_size=7.2, title_color="#0369A1")

    arrow(ax, 2.47, 2.45, 2.47, 1.99, color="#0284C7", lw=1.5, style="<|-|>")
    arrow(ax, 6.22, 2.45, 6.22, 1.99, color="#0284C7", lw=1.5, style="<|-|>")

    # Parallel Slaves under System AXI4 Bus
    draw_box(ax, 0.48, 0.45, 5.45, 0.62,
             "Off-Chip Main Memory / DRAM  (AXI4 Slave)",
             "DDR3 / DDR4 Memory Controller (0x8000_0000+)",
             fc="#F1F5F9", ec="#334155", lw=1.4, title_size=8.4, sub_size=7.1)
    draw_box(ax, 6.33, 0.45, 5.45, 0.62,
             "SoC Peripherals via axi2apb  (MMIO Slaves)",
             "UART, Timer, PLIC, CLINT (4-Hart IPI/Timer), BootROM",
             fc="#F1F5F9", ec="#64748B", lw=1.2, title_size=8.4, sub_size=7.1)

    arrow(ax, 3.20, 1.32, 3.20, 1.08, color="#334155", lw=1.5, style="<|-|>")
    arrow(ax, 9.05, 1.32, 9.05, 1.08, color="#64748B", lw=1.3, style="<|-|>")

    # =========================================================================
    # RIGHT PANEL: GEM5 v26.0 4-CORE + SHARED L2 MODEL + CACTI 7.0
    # =========================================================================
    draw_box(ax, 12.35, 0.30, 6.20, 11.00,
             "gem5 v26.0 4-CORE + SHARED L2 MODEL",
             fc="#F8FAFC", ec="#0F766E", lw=2.0, title_size=11.0, title_color="#0F766E", align_top=True)

    # 4x CVA6MinorCPU + Private L1I/L1D in gem5
    draw_box(ax, 12.62, 8.15, 5.66, 2.65,
             "system.cpu[0..3]: 4x CVA6MinorCPU + Private L1 Caches",
             "• 4x RiscvMinorCPU (1-wide issue, 2-wide commit, CVA6FUPool)\n"
             "• 4x Private L1ICache (16 KiB, 4-Way)\n"
             "• 4x Private L1DCache (32 KiB, 8-Way, Write-Through / Clean)\n"
             "• Tagged with Requestor / PartitionID (core_id = 0..3)\n"
             "• Runs 4-Core Multi-Programmed or Multi-Threaded RISC-V Benchmarks",
             fc="#ECFEFF", ec="#0891B2", lw=1.5, title_size=9.0, sub_size=7.3,
             title_color="#155E75", align_top=True)

    # L2XBar in gem5
    draw_box(ax, 12.62, 7.05, 5.66, 0.75,
             "system.l2bus: L2XBar  (CoherentXBar, 16B / 128-bit)",
             "Aggregates 4x L1I + 4x L1D ports -> Shared L2 (snoop/coherence filter)",
             fc="#DBEAFE", ec="#1D4ED8", lw=1.5, title_size=8.7, sub_size=7.1, title_color="#1E3A8A")
    arrow(ax, 15.45, 8.15, 15.45, 7.82, color="#0891B2", lw=1.6, style="<|-|>")

    # Shared L2 Cache with Way-Shutdown in gem5
    draw_box(ax, 12.62, 3.15, 5.66, 3.55,
             "★ system.l2cache: Shared L2 Cache (Custom Way-Shutdown)",
             "• Capacity: 256 KiB (8-Way) or 512 KiB (16-Way), 64B line, mshrs=16\n"
             "• Tag Store: WayShutdownSetAssoc (extends BaseSetAssoc)\n"
             "• Dynamic Bitmask: way_enable_mask (gates lookup & victim selection)\n"
             "• Way Shutdown (1->0): counts dirty writebacks + invalidates way\n"
             "• Way Wakeup (0->1): models T_wakeup latency & switch energy\n\n"
             "Modeled Policies compared in Step 2:\n"
             "  1. Static-k Oracle (1..8/16 active ways)\n"
             "  2. Policy 1: Selective Ways (Miss-Rate / IPC + Hysteresis)\n"
             "  3. Policy 2: Per-Way & Per-Core Utilization Counter\n"
             "  4. Policy 3: Phase-Adaptive Sampled-Set ATD (High-Perf, Low-Power)",
             fc="#FAF5FF", ec="#9333EA", lw=1.9, title_size=8.8, sub_size=7.0,
             title_color="#6B21A8", align_top=True)
    arrow(ax, 15.45, 7.05, 15.45, 6.72, color="#9333EA", lw=1.7, style="<|-|>")

    # SystemXBar + DRAM in gem5
    draw_box(ax, 12.62, 1.75, 5.66, 1.05,
             "system.membus (SystemXBar) + DDR3_1600_8x8 / SimpleMemory",
             "Models off-chip DRAM latency (~50ns) & L2 miss/writeback traffic\nIncludes dirty-flush traffic incurred during L2 Way-Shutdown",
             fc="#F1F5F9", ec="#334155", lw=1.4, title_size=8.5, sub_size=7.1)
    arrow(ax, 15.45, 3.15, 15.45, 2.82, color="#334155", lw=1.6, style="<|-|>")

    # CACTI 7.0 Shared L2 Power & EDP Box
    draw_box(ax, 12.62, 0.45, 5.66, 0.98,
             "CACTI 7.0 Shared L2 Power & 4-Core EDP Evaluator (22nm)",
             "stats.txt: l2.active_way_cycles[0..W-1], l2.tag/data_accesses, flushes, misses\n"
             "-> L2 Dynamic + L2 Leakage Savings + Flush/Switch Cost + DRAM Energy -> EDP",
             fc="#FEF2F2", ec="#DC2626", lw=1.5, title_size=8.4, sub_size=6.9, title_color="#991B1B")
    arrow(ax, 18.28, 4.90, 18.44, 4.90, color="#DC2626", lw=1.3, style="-")
    arrow(ax, 18.44, 4.90, 18.44, 0.94, color="#DC2626", lw=1.3, style="-")
    arrow(ax, 18.44, 0.94, 18.28, 0.94, color="#DC2626", lw=1.4, style="-|>")

    # Dashed 1-to-1 correlation arrows between Left (4-Core CVA6 + Shared L2) and Right (gem5)
    for yc in [9.45, 7.42, 4.85, 1.65, 0.76]:
        arrow(ax, 12.05, yc, 12.35, yc, color="#0F766E", lw=1.6, ls="--", style="<|-|>")

    plt.tight_layout(pad=0.3)
    docs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs"))
    out_png = os.path.join(docs_dir, "cva6_gem5_architecture.png")
    out_svg = os.path.join(docs_dir, "cva6_gem5_architecture.svg")
    plt.savefig(out_png, dpi=200, bbox_inches="tight")
    plt.savefig(out_svg, bbox_inches="tight")
    print(f"Saved: {out_png}")
    print(f"Saved: {out_svg}")


if __name__ == "__main__":
    main()
