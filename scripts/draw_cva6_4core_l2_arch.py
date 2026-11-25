#!/usr/bin/env python3
"""
Clean minimal architecture diagram:
4-Core OpenHW CVA6 (separate L1 I-Cache & L1 D-Cache -> AXI4 Arbiter)
+ Debug Module -> AXI4 Crossbar (axi_xbar) -> Shared L2 Cache (Write-Back) -> DRAM
and SoC Peripherals. Block names only, no file paths or verbose details.
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch


def blk(ax, x, y, w, h, title, fc="#FFFFFF", ec="#0F172A",
        lw=1.4, tsize=9.0, tc="#0F172A", top=False, ls="-"):
    p = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.04,rounding_size=0.10",
        facecolor=fc, edgecolor=ec, linewidth=lw, linestyle=ls, zorder=2
    )
    ax.add_patch(p)
    if top:
        ax.text(x + w / 2, y + h - 0.16, title, ha="center", va="top",
                fontsize=tsize, fontweight="bold", color=tc, zorder=3)
    else:
        ax.text(x + w / 2, y + h / 2, title, ha="center", va="center",
                fontsize=tsize, fontweight="bold", color=tc, zorder=3)


def wire(ax, x1, y1, x2, y2, label="", color="#1E293B", lw=1.4,
         style="-|>", ldx=0.0, ldy=0.0, lsize=7.4):
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
    fig, ax = plt.subplots(figsize=(16, 9.2))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9.2)
    ax.axis("off")

    ax.text(8.0, 8.85, "4-Core CVA6 Architecture with Shared Write-Back L2 Cache",
            ha="center", va="center", fontsize=13.5, fontweight="bold", color="#0F172A")

    # Outer SoC container
    blk(ax, 0.35, 0.35, 15.3, 8.15, "4-Core CVA6 SoC",
        fc="#F8FAFC", ec="#0F172A", lw=2.0, tsize=10.0, top=True)

    # ------------------------------------------------------------------
    # TOP ROW: 4x CVA6 Cores + Debug Module
    # ------------------------------------------------------------------
    core_w = 2.85
    gap = 0.25
    x0 = 0.65

    for c in range(4):
        cx = x0 + c * (core_w + gap)
        blk(ax, cx, 4.95, core_w, 3.05, f"CVA6 Core {c}",
            fc="#EFF6FF", ec="#1D4ED8", lw=1.6, tsize=9.2, tc="#1E3A8A", top=True)

        # Pipeline box
        blk(ax, cx + 0.18, 6.95, core_w - 0.36, 0.62, "CVA6 Pipeline",
            fc="#FFFFFF", ec="#1D4ED8", lw=1.2, tsize=8.2)

        # Separate L1 I-Cache and L1 D-Cache (NO connection between them!)
        cache_w = (core_w - 0.50) / 2
        ic_x = cx + 0.18
        dc_x = cx + 0.18 + cache_w + 0.14
        blk(ax, ic_x, 5.98, cache_w, 0.62, "L1 I-Cache",
            fc="#FFFFFF", ec="#1D4ED8", lw=1.2, tsize=7.8)
        blk(ax, dc_x, 5.98, cache_w, 0.62, "L1 D-Cache",
            fc="#FFFFFF", ec="#1D4ED8", lw=1.2, tsize=7.8)

        # AXI4 Arbiter inside each core
        blk(ax, cx + 0.18, 5.12, core_w - 0.36, 0.54, "AXI4 Arbiter",
            fc="#FEF3C7", ec="#B45309", lw=1.2, tsize=8.0, tc="#78350F")

        # Separate arrows: Pipeline <-> L1 I-Cache, Pipeline <-> L1 D-Cache
        wire(ax, ic_x + cache_w / 2, 6.95, ic_x + cache_w / 2, 6.60, style="<|-|>", color="#1D4ED8", lw=1.2)
        wire(ax, dc_x + cache_w / 2, 6.95, dc_x + cache_w / 2, 6.60, style="<|-|>", color="#1D4ED8", lw=1.2)

        # Separate arrows: L1 I-Cache <-> AXI4 Arbiter, L1 D-Cache <-> AXI4 Arbiter
        wire(ax, ic_x + cache_w / 2, 5.98, ic_x + cache_w / 2, 5.66, style="<|-|>", color="#B45309", lw=1.2)
        wire(ax, dc_x + cache_w / 2, 5.98, dc_x + cache_w / 2, 5.66, style="<|-|>", color="#B45309", lw=1.2)

        # Core AXI4 Arbiter <-> AXI4 Crossbar
        wire(ax, cx + core_w / 2, 4.95, cx + core_w / 2, 4.25,
             label="AXI4", style="<|-|>", color="#B45309", lw=1.5, ldx=0.32, lsize=7.0)

    # Debug Module
    dm_x = x0 + 4 * (core_w + gap)
    dm_w = 15.35 - dm_x
    blk(ax, dm_x, 4.95, dm_w, 3.05, "Debug Module",
        fc="#F1F5F9", ec="#475569", lw=1.5, tsize=9.0, tc="#334155")
    wire(ax, dm_x + dm_w / 2, 4.95, dm_x + dm_w / 2, 4.25,
         label="AXI4", style="<|-|>", color="#475569", lw=1.4, ldx=0.35, lsize=7.0)

    # ------------------------------------------------------------------
    # MIDDLE: AXI4 Crossbar (axi_xbar)
    # ------------------------------------------------------------------
    blk(ax, 0.65, 3.45, 14.70, 0.80, "AXI4 Crossbar (axi_xbar)",
        fc="#FEF3C7", ec="#B45309", lw=1.7, tsize=10.0, tc="#78350F")

    # ------------------------------------------------------------------
    # LOWER LEFT: Shared L2 Cache (Write-Back) -> DRAM
    # ------------------------------------------------------------------
    blk(ax, 0.65, 1.95, 9.60, 0.90, "Shared L2 Cache (Write-Back)",
        fc="#DCFCE7", ec="#15803D", lw=1.8, tsize=10.0, tc="#14532D")

    blk(ax, 0.65, 0.65, 9.60, 0.78, "DRAM",
        fc="#F1F5F9", ec="#334155", lw=1.5, tsize=9.8, tc="#0F172A")

    wire(ax, 5.45, 3.45, 5.45, 2.85,
         label="AXI4", style="<|-|>", color="#15803D", lw=1.6, ldx=0.40, lsize=7.4)
    wire(ax, 5.45, 1.95, 5.45, 1.43,
         label="AXI4", style="<|-|>", color="#334155", lw=1.6, ldx=0.40, lsize=7.4)

    # ------------------------------------------------------------------
    # LOWER RIGHT: Peripherals
    # ------------------------------------------------------------------
    blk(ax, 10.75, 0.65, 4.60, 2.20, "Peripherals",
        fc="#F1F5F9", ec="#475569", lw=1.5, tsize=9.6, tc="#334155", top=True)

    periphs = [
        ("BootROM", 10.95, 1.75), ("CLINT", 12.40, 1.75), ("PLIC", 13.85, 1.75),
        ("UART",    10.95, 0.90), ("Timer", 12.40, 0.90), ("GPIO / SPI", 13.85, 0.90),
    ]
    for name, px, py in periphs:
        blk(ax, px, py, 1.30, 0.58, name, fc="#FFFFFF", ec="#64748B", lw=1.1, tsize=7.6)

    wire(ax, 13.05, 3.45, 13.05, 2.85,
         label="AXI4", style="<|-|>", color="#475569", lw=1.5, ldx=0.40, lsize=7.4)

    docs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs"))
    out_png = os.path.join(docs_dir, "cva6_4core_l2_architecture.png")
    out_svg = os.path.join(docs_dir, "cva6_4core_l2_architecture.svg")
    plt.tight_layout(pad=0.25)
    plt.savefig(out_png, dpi=180, bbox_inches="tight", facecolor="white")
    plt.savefig(out_svg, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[OK] Saved:\n  - {out_png}\n  - {out_svg}")


if __name__ == "__main__":
    main()
