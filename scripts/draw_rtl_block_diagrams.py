#!/usr/bin/env python3
"""
Generate 3 separate pure-RTL hardware block diagrams (Top + 2 Submodules)
with exact Verilog signals, bit-widths, logic gates, MUXes, comparators, and FSMs:
  1. docs/diagram_1_l2_ws_top.png (.svg)         — L2 + Way-Shutdown Top-Level Interconnect
  2. docs/diagram_2_shared_l2_16way_ws.png (.svg) — Submodule: cva6_shared_l2_16way_ws
  3. docs/diagram_3_l2_way_shutdown_ctrl.png (.svg) — Submodule: l2_way_shutdown_ctrl
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Polygon


def blk(ax, x, y, w, h, title, body="", fc="#FFFFFF", ec="#0F172A",
        lw=1.4, tsize=8.8, bsize=7.2, tc="#0F172A", bc="#334155", top=False, ls="-"):
    p = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.04,rounding_size=0.10",
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
            ax.text(x + w / 2, y + h * 0.68, title, ha="center", va="center",
                    fontsize=tsize, fontweight="bold", color=tc, zorder=3)
            ax.text(x + w / 2, y + h * 0.28, body, ha="center", va="center",
                    fontsize=bsize, color=bc, linespacing=1.24, zorder=3)
        else:
            ax.text(x + w / 2, y + h / 2, title, ha="center", va="center",
                    fontsize=tsize, fontweight="bold", color=tc, zorder=3)


def mux(ax, x, y, w, h, label="MUX", fc="#FEF3C7", ec="#B45309"):
    pts = [(x, y), (x + w, y + h * 0.18), (x + w, y + h * 0.82), (x, y + h)]
    poly = Polygon(pts, closed=True, facecolor=fc, edgecolor=ec, linewidth=1.4, zorder=3)
    ax.add_patch(poly)
    ax.text(x + w * 0.46, y + h / 2, label, ha="center", va="center",
            fontsize=7.2, fontweight="bold", color="#78350F", zorder=4)


def wire(ax, x1, y1, x2, y2, label="", color="#1E293B", lw=1.4,
         style="-|>", rad=0.0, ldx=0.0, ldy=0.0, lsize=7.0, ha="center"):
    a = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle=style, mutation_scale=11,
        linewidth=lw, color=color,
        connectionstyle=f"arc3,rad={rad}", zorder=4
    )
    ax.add_patch(a)
    if label:
        mx = (x1 + x2) / 2 + ldx
        my = (y1 + y2) / 2 + ldy
        ax.text(mx, my, label, ha=ha, va="center",
                fontsize=lsize, fontweight="bold", color=color,
                bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.92),
                zorder=5)


def save_fig(fig, docs_dir, stem):
    png = os.path.join(docs_dir, f"{stem}.png")
    svg = os.path.join(docs_dir, f"{stem}.svg")
    plt.tight_layout(pad=0.25)
    plt.savefig(png, dpi=180, bbox_inches="tight", facecolor="white")
    plt.savefig(svg, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[OK] {png}")


# ==============================================================================
# DIAGRAM 1: TOP-LEVEL AXI4 SHARED L2 + WAY-SHUTDOWN SUBSYSTEM (axi_l2_wb_wrap)
# ==============================================================================
def draw_top(docs_dir):
    fig, ax = plt.subplots(figsize=(16, 8.2))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 8.2)
    ax.axis("off")

    ax.text(8.0, 7.90, "L2 Way-Shutdown Subsystem Block Diagram (axi_l2_wb_wrap)",
            ha="center", va="center", fontsize=13.0, fontweight="bold", color="#0F172A")
    ax.text(8.0, 7.56, "AXI4 Slave (from axi_xbar)  ->  cva6_shared_l2_16way_ws + l2_way_shutdown_ctrl  ->  AXI4 Master (to DRAM)",
            ha="center", va="center", fontsize=8.8, color="#475569")

    # Outer Subsystem Boundary: axi_l2_wb_wrap
    blk(ax, 2.35, 0.55, 11.3, 6.80,
        "axi_l2_wb_wrap (AXI4 Shared L2 + Way-Shutdown Top)",
        fc="#F8FAFC", ec="#0F172A", lw=2.0, tsize=9.8, top=True)

    # AXI4 Pass-through / Latency-Gate Bridge strip at top inside wrapper
    blk(ax, 2.75, 5.75, 10.50, 0.95,
        "AXI4 Channel Bridge & Latency Gate (AW / W / B / AR / R)",
        "Forwards AW, W, AR directly to mst  |  Extracts l2_req_valid, l2_req_is_write, l2_req_addr[63:0], core_id[1:0] on AR/AW fire\n"
        "Applies L2 Hit/Miss/WB/Wakeup latency backpressure on R & B valid/ready",
        fc="#FEF3C7", ec="#B45309", lw=1.5, tsize=8.6, bsize=7.0, tc="#78350F", top=True)

    # Submodule 1 (Left): cva6_shared_l2_16way_ws
    blk(ax, 2.75, 0.95, 4.40, 4.15,
        "i_l2_core\n(cva6_shared_l2_16way_ws)",
        "\n512 KiB, 16-Way, 64B Line\nWrite-Back Shared L2 Cache\n\n"
        "• Way-Gated Parallel Tag Lookup\n"
        "• Masked RR Victim Selector\n"
        "• O(1) Per-Way Dirty Counters\n"
        "• 16-Set/Cycle Dirty Flush Engine",
        fc="#F0FDF4", ec="#15803D", lw=1.8, tsize=9.0, bsize=7.4, tc="#14532D", top=True)

    # Submodule 2 (Right): l2_way_shutdown_ctrl
    blk(ax, 9.25, 0.95, 4.00, 4.15,
        "i_l2_ws_ctrl\n(l2_way_shutdown_ctrl)",
        "\nWay-Shutdown Controller\n(atd_dirty_aware)\n\n"
        "• 1/32 Set Sampler (set[4:0]==0)\n"
        "• 16-Set x 16-Way LRU ATD\n"
        "• Epoch Engine (2048 acc)\n"
        "• Dirty-Flush Guard (<= 96)\n"
        "• Power-Gate & Wakeup FSM",
        fc="#F0FDFA", ec="#0F766E", lw=1.8, tsize=9.0, bsize=7.4, tc="#134E4A", top=True)

    # External AXI4 Slave Ports (Left edge -> AXI4 Bridge)
    wire(ax, 0.20, 6.45, 2.75, 6.45, label="slv: AXI4 AW / W / AR", color="#B45309", lw=1.6, ldx=-0.12, ldy=0.18, lsize=7.3)
    wire(ax, 2.75, 5.98, 0.20, 5.98, label="slv: AXI4 R / B", color="#15803D", lw=1.6, ldx=-0.12, ldy=-0.18, lsize=7.3)

    # External AXI4 Master Ports (Right edge <- AXI4 Bridge -> DRAM)
    wire(ax, 13.25, 6.45, 15.80, 6.45, label="mst: AXI4 AW / W / AR", color="#B45309", lw=1.6, ldx=0.12, ldy=0.18, lsize=7.3)
    wire(ax, 15.80, 5.98, 13.25, 5.98, label="mst: AXI4 R / B", color="#15803D", lw=1.6, ldx=0.12, ldy=-0.18, lsize=7.3)

    # Control & Clock inputs (Left lower -> Wrapper)
    wire(ax, 0.20, 4.55, 2.35, 4.55, label="clk_i, rst_ni", color="#0F172A", lw=1.4, ldx=-0.10, ldy=0.16, lsize=7.2)
    wire(ax, 0.20, 3.85, 2.35, 3.85, label="ws_enable_i", color="#0F766E", lw=1.4, ldx=-0.10, ldy=0.16, lsize=7.2)

    # Telemetry Outputs (Left bottom from i_l2_core, Right bottom from i_l2_ws_ctrl)
    wire(ax, 2.75, 1.55, 0.20, 1.55, label="cnt_l2_*_o, shutdown_flushes", color="#475569", lw=1.3, ldx=-0.10, ldy=0.18, lsize=7.0)
    wire(ax, 13.25, 4.25, 15.80, 4.25, label="way_en_o[15:0]", color="#0369A1", lw=1.5, ldx=0.10, ldy=0.16, lsize=7.2)
    wire(ax, 13.25, 3.55, 15.80, 3.55, label="way_sd_o[15:0]", color="#0369A1", lw=1.5, ldx=0.10, ldy=0.16, lsize=7.2)
    wire(ax, 13.25, 2.15, 15.80, 2.15, label="cnt_ws_*_o (telemetry)", color="#475569", lw=1.3, ldx=0.10, ldy=0.16, lsize=7.0)

    # Bridge <-> Submodule 1 (L2 req / resp_lat)
    wire(ax, 4.30, 5.75, 4.30, 5.10, label="l2_req_*", color="#B45309", lw=1.5, ldx=-0.55, lsize=7.0)
    wire(ax, 5.65, 5.10, 5.65, 5.75, label="resp_lat[5:0]", color="#15803D", lw=1.5, ldx=0.72, lsize=7.0)

    # Bridge -> Submodule 2 (Off-critical-path snoop)
    wire(ax, 11.25, 5.75, 11.25, 5.10, label="l2_req_valid, l2_req_addr[63:0]", color="#0F766E", lw=1.5, ldx=0.0, lsize=6.9)

    # Inter-Submodule Signals (Between i_l2_core and i_l2_ws_ctrl)
    wire(ax, 9.25, 4.55, 7.15, 4.55, label="ws_way_en[15:0]", color="#0369A1", lw=1.5, ldy=0.16, lsize=7.1)
    wire(ax, 9.25, 3.95, 7.15, 3.95, label="ws_way_sd[15:0]", color="#0369A1", lw=1.5, ldy=0.16, lsize=7.1)
    wire(ax, 9.25, 3.35, 7.15, 3.35, label="ws_wakeup_stall", color="#0369A1", lw=1.4, ldy=0.16, lsize=7.1)
    wire(ax, 9.25, 2.70, 7.15, 2.70, label="ws_flush_req, way[3:0]", color="#B91C1C", lw=1.5, ldy=0.16, lsize=7.0)
    wire(ax, 7.15, 2.05, 9.25, 2.05, label="ws_flush_done", color="#B91C1C", lw=1.5, ldy=0.16, lsize=7.1)
    wire(ax, 7.15, 1.35, 9.25, 1.35, label="l2_way_dirty_cnt[0..15][9:0]", color="#A16207", lw=1.6, ldy=0.16, lsize=7.0)

    save_fig(fig, docs_dir, "diagram_1_l2_ws_top")


# ==============================================================================
# DIAGRAM 2: SUBMODULE 1 — cva6_shared_l2_16way_ws (INTERNAL LOGIC & SIGNALS)
# ==============================================================================
def draw_shared_l2(docs_dir):
    fig, ax = plt.subplots(figsize=(17.5, 10.5))
    ax.set_xlim(0, 17.5)
    ax.set_ylim(0, 10.5)
    ax.axis("off")

    ax.text(8.75, 10.22, "Block Diagram 2 — Submodule: cva6_shared_l2_16way_ws (Internal RTL Datapath & Logic)",
            ha="center", va="center", fontsize=13.0, fontweight="bold", color="#14532D")
    ax.text(8.75, 9.90, "512 KiB, 16-Way, 64B Line, Write-Back Shared L2 with O(1) Dirty Counters & Background Dirty-Way Flush Engine",
            ha="center", va="center", fontsize=8.8, color="#475569")

    # Outer Module Box
    blk(ax, 0.35, 0.35, 16.8, 9.48,
        "MODULE: cva6_shared_l2_16way_ws",
        fc="#F8FAFC", ec="#15803D", lw=2.0, tsize=9.8, tc="#14532D", top=True)

    # 1. Address Slicer
    blk(ax, 0.65, 7.45, 2.85, 1.65,
        "Address Slicer",
        "req_addr_i[63:0]\n"
        "• req_tag[48:0] = [63:15]\n"
        "• set_idx[8:0]  = [14:6]\n"
        "• offset[5:0]   = [5:0]",
        fc="#FEF3C7", ec="#B45309", lw=1.4, tsize=8.4, bsize=7.1, top=True)

    # 2. Tag / Valid / Dirty SRAM Arrays (512 x 16)
    blk(ax, 4.15, 7.15, 4.55, 2.00,
        "Directory & Data SRAM Arrays (512 Sets x 16 Ways)",
        "valid_arr[512][16]  |  dirty_arr[512][16]  |  tag_arr[512][16][48:0]\n"
        "Data SRAM: 16 Independent 32 KiB Way Banks (W0..W15)\n"
        "Per-Way Power Control:\n"
        "  • CS_n[w] = ~way_en_i[w]  (gates dynamic lookup)\n"
        "  • SD[w]   =  way_sd_i[w]  (power-gates 5.86 mW/way SRAM)",
        fc="#DCFCE7", ec="#15803D", lw=1.6, tsize=8.5, bsize=7.0, top=True)

    wire(ax, 3.50, 8.35, 4.15, 8.35, label="set_idx[8:0]", color="#B45309", lw=1.4, ldy=0.18, lsize=6.8)

    # 3. 16-Way Gated Parallel Tag Compare Logic
    blk(ax, 9.45, 7.45, 3.85, 1.65,
        "16x Parallel Tag Comparators\n& Priority Encoder",
        "For w = 0..15:\n"
        "match[w] = way_en_i[w] & valid_arr[set][w]\n"
        "         & (tag_arr[set][w] == req_tag)\n"
        "-> hit_found, hit_way[3:0], active_way_count[4:0]",
        fc="#EFF6FF", ec="#1D4ED8", lw=1.4, tsize=8.2, bsize=6.9, top=True)

    wire(ax, 8.70, 8.45, 9.45, 8.45, label="tag/valid[15:0]", color="#15803D", lw=1.4, ldy=0.18, lsize=6.7)
    ax.plot([2.08, 2.08, 11.35, 11.35], [9.10, 9.30, 9.30, 9.10], color="#B45309", lw=1.2, zorder=3)
    wire(ax, 11.35, 9.30, 11.35, 9.10, color="#B45309", lw=1.2)
    ax.text(3.85, 9.30, "req_tag[48:0] + way_en_i[15:0]", ha="center", va="center",
            fontsize=6.9, fontweight="bold", color="#B45309",
            bbox=dict(boxstyle="round,pad=0.10", fc="white", ec="none"), zorder=5)

    # 4. Masked Victim Selector (Free-Way + Round-Robin)
    blk(ax, 9.45, 5.15, 3.85, 1.80,
        "Masked Victim Selector (Active Ways Only)",
        "1) Free-Way Enc: first w with way_en_i[w] & !valid\n"
        "   -> free_found, free_way[3:0]\n"
        "2) RR Scan: rr_ptr[set_idx] + k (k=0..15)\n"
        "   first cand with way_en_i[cand] == 1",
        fc="#EFF6FF", ec="#1D4ED8", lw=1.4, tsize=8.2, bsize=6.9, top=True)

    mux(ax, 13.75, 5.55, 0.70, 1.05, label="MUX\nfree")
    wire(ax, 13.30, 6.25, 13.75, 6.25, label="free_way", color="#1D4ED8", lw=1.2, ldy=0.16, lsize=6.4)
    wire(ax, 13.30, 5.75, 13.75, 5.75, label="rr_cand", color="#1D4ED8", lw=1.2, ldy=-0.16, lsize=6.4)
    wire(ax, 14.45, 6.07, 15.10, 6.07, label="victim_way[3:0]", color="#1D4ED8", lw=1.4, ldy=0.20, lsize=6.7)

    # 5. Hit/Miss Allocation, Latency & Coherence Output Unit (Right)
    blk(ax, 14.65, 7.15, 2.25, 2.00,
        "L2 Response &\nCoherence Driver",
        "• resp_valid_o\n• resp_is_hit_o\n• l1_inval_valid_o\n  (if req_is_write_i)\n• l1_inval_src/addr",
        fc="#FFFFFF", ec="#15803D", lw=1.3, tsize=8.1, bsize=6.8, top=True)

    wire(ax, 13.30, 8.25, 14.65, 8.25, label="hit_found\nhit_way", color="#1D4ED8", lw=1.4, ldy=0.24, lsize=6.6)

    blk(ax, 13.75, 2.75, 3.15, 2.35,
        "Latency Adder & Miss/WB Logic",
        "Base = L2_HIT_LAT (4 cyc)\n"
        "+ DRAM_MISS_LAT (28 cyc) if !hit\n"
        "+ DRAM_WB_LAT (12 cyc)\n"
        "   if !hit & vic_valid & vic_dirty\n"
        "+ 6 cyc (T_wakeup) if wakeup_stall_i\n"
        "-> resp_latency_o[5:0]\n"
        "-> cnt_l2_writebacks_o++",
        fc="#FFFFFF", ec="#0369A1", lw=1.4, tsize=8.1, bsize=6.8, top=True)

    wire(ax, 15.30, 6.07, 15.30, 5.10, color="#1D4ED8", lw=1.3)

    # 6. O(1) Per-Way Dirty Counters (Middle-Left)
    blk(ax, 0.65, 3.95, 5.15, 2.55,
        "O(1) Per-Way Dirty Line Counters (way_dirty_cnt_o[0..15][9:0])",
        "16 x 10-bit Up/Down Registers (160 FFs total, zero-latency read by controller):\n"
        "• Hit Write (hit_found & req_is_write_i & !dirty[set][hit_way]):\n"
        "     dirty_arr <= 1'b1;   way_dirty_cnt_o[hit_way] <= +1\n"
        "• Miss Dirty Evict (!hit_found & vic_dirty & !req_is_write_i):\n"
        "     way_dirty_cnt_o[victim_way] <= -1\n"
        "• Miss Write-Allocate (!hit_found & !vic_dirty & req_is_write_i):\n"
        "     way_dirty_cnt_o[victim_way] <= +1\n"
        "• Background Way Flush: way_dirty_cnt_o[flush_way_q] -= chunk_dirty_cnt",
        fc="#FEF9C3", ec="#A16207", lw=1.6, tsize=8.3, bsize=6.8, top=True)

    wire(ax, 5.80, 4.35, 6.45, 4.35, style="<|-|>", label="-dirty", color="#A16207", lw=1.3, ldy=0.16, lsize=6.4)
    wire(ax, 4.80, 7.15, 4.80, 6.50, style="<|-|>", label="dirty_arr R/W", color="#A16207", lw=1.3, ldx=0.55, lsize=6.7)

    # 7. Background Dirty-Way Flush Engine (Bottom-Center)
    blk(ax, 6.45, 2.75, 6.75, 2.05,
        "Background Dirty-Way Flush Engine (16 Sets / Cycle = 32 Cycles per Way)",
        "Trigger: !flush_active_q & flush_req_i -> latch flush_way_q <= flush_way_i, flush_chunk_q <= 0\n"
        "Each Cycle (flush_chunk_q = 0..31): for j = 0..15, s = {flush_chunk_q[4:0], j[3:0]}:\n"
        "  • Popcount: chunk_dirty_cnt[4:0] = sum(valid_arr[s][flush_way_q] & dirty_arr[s][flush_way_q])\n"
        "  • Clear Array: valid_arr[s][flush_way_q] <= 0;  dirty_arr[s][flush_way_q] <= 0\n"
        "  • Accumulate: cnt_l2_shutdown_flushes_o += chunk_dirty_cnt\n"
        "Done (flush_chunk_q == 31): flush_active_q <= 0; pulse flush_done_o <= 1; way_dirty_cnt <= 0",
        fc="#FEE2E2", ec="#B91C1C", lw=1.6, tsize=8.3, bsize=6.8, top=True)

    # Connect Flush Engine back to Directory Arrays
    ax.plot([7.85, 7.85], [4.80, 7.15], color="#B91C1C", lw=1.4, zorder=3)
    wire(ax, 7.85, 4.80, 7.85, 7.15, label="clear valid/dirty\n(16 sets/cyc)", color="#B91C1C", lw=1.4, ldx=-0.78, ldy=0.1, lsize=6.6)

    # 8. Hardware Performance Counters Strip (Bottom)
    blk(ax, 0.65, 0.65, 16.25, 1.55,
        "Hardware Performance & Telemetry Counters (64-bit Registers)",
        "cnt_l2_accesses_o  |  cnt_l2_hits_o  |  cnt_l2_misses_o  |  cnt_l2_read_acc_o  |  cnt_l2_write_acc_o\n"
        "cnt_l2_writebacks_o (normal dirty evict)  |  cnt_l2_shutdown_flushes_o (way-shutdown dirty flush)  |  cnt_l2_tag_lookups_o (+active_way_count)\n"
        "Per-Way: cnt_l2_way_hits_o[0..15]  |  Per-Core: cnt_l2_core_acc_o[0..3], cnt_l2_core_hits_o[0..3], cnt_l2_core_misses_o[0..3]",
        fc="#F1F5F9", ec="#475569", lw=1.3, tsize=8.3, bsize=7.0, top=True)

    wire(ax, 9.80, 2.75, 9.80, 2.20, label="chunk_dirty_cnt", color="#B91C1C", lw=1.3, ldx=0.72, lsize=6.6)
    wire(ax, 15.30, 2.75, 15.30, 2.20, label="wb/miss/hit", color="#475569", lw=1.3, ldx=0.58, lsize=6.6)

    # External Control Port Annotations at Left/Bottom-Left
    blk(ax, 0.65, 2.75, 5.15, 0.90,
        "External Control Handshake Ports (with l2_way_shutdown_ctrl)",
        "IN : way_en_i[15:0], way_sd_i[15:0], wakeup_stall_i, flush_req_i, flush_way_i[3:0]\n"
        "OUT: flush_done_o, way_dirty_cnt_o[0..15][9:0]",
        fc="#E0F2FE", ec="#0369A1", lw=1.3, tsize=7.9, bsize=6.8, top=True)
    wire(ax, 5.80, 3.20, 6.45, 3.20, style="<|-|>", color="#0369A1", lw=1.4)

    save_fig(fig, docs_dir, "diagram_2_shared_l2_16way_ws")


# ==============================================================================
# DIAGRAM 3: SUBMODULE 2 — l2_way_shutdown_ctrl (INTERNAL LOGIC & FSM)
# ==============================================================================
def draw_ws_ctrl(docs_dir):
    fig, ax = plt.subplots(figsize=(17.5, 10.5))
    ax.set_xlim(0, 17.5)
    ax.set_ylim(0, 10.5)
    ax.axis("off")

    ax.text(8.75, 10.22, "Block Diagram 3 — Submodule: l2_way_shutdown_ctrl (atd_dirty_aware Internal Logic & FSM)",
            ha="center", va="center", fontsize=13.0, fontweight="bold", color="#134E4A")
    ax.text(8.75, 9.90, "Sampled-Set ATD (16x16 LRU) + Epoch Decision Datapath + Dirty-Flush Cost Guard + 3-State Power-Gating FSM",
            ha="center", va="center", fontsize=8.8, color="#475569")

    # Outer Module Box
    blk(ax, 0.35, 0.35, 16.8, 9.3,
        "MODULE: l2_way_shutdown_ctrl (Params: EPOCH=2048, MIN_WAYS=2, WAKEUP=6, DIRTY_THRESH=96, ATD_SETS=16)",
        fc="#F8FAFC", ec="#0F766E", lw=2.0, tsize=9.5, tc="#134E4A", top=True)

    # 1. 1/32 Set Sampler
    blk(ax, 0.65, 7.35, 3.15, 1.75,
        "1/32 Set Sampler Logic",
        "Inputs: l2_req_valid_i,\n        l2_req_addr_i[63:0]\n"
        "set_idx[8:0] = addr[14:6]\n"
        "atd_sampled  = valid & (set[4:0]==0)\n"
        "atd_set_idx[3:0] = set[8:5]\n"
        "atd_req_tag[19:0]= addr[34:15]",
        fc="#FEF3C7", ec="#B45309", lw=1.4, tsize=8.3, bsize=6.9, top=True)

    # 2. Sampled-Set ATD + 16-Way LRU Shift Network
    blk(ax, 4.55, 7.10, 6.25, 2.00,
        "Sampled-Set ATD & 16-Way LRU Stack (Tag-Only: 16 x 16 x 21b = 672 Bytes)",
        "Storage: atd_tag_q[16][16][19:0], atd_val_q[16][16]\n"
        "Combinational 16-Way Tag Match -> atd_hit_found, atd_hit_depth[3:0]\n"
        "Sequential LRU Stack Update (on atd_sampled):\n"
        "  • Hit at depth d: atd_hits_q[d]++; shift [0..d-1] -> [1..d]; insert tag at [0]\n"
        "  • Miss: shift [0..14] -> [1..15]; insert tag at [0] (evict LRU [15])\n"
        "  • Always tracks all 16 LRU depths even when L2 ways are power-gated",
        fc="#CCFBF1", ec="#0F766E", lw=1.6, tsize=8.4, bsize=6.9, top=True)

    wire(ax, 3.80, 8.20, 4.55, 8.20, label="sampled\nset, tag", color="#0F766E", lw=1.4, ldy=0.22, lsize=6.6)

    # 3. ATD Hit Counters + Exponential Decay Unit
    blk(ax, 11.55, 7.10, 5.30, 2.00,
        "ATD Marginal Hit Counters & Decay",
        "Registers:\n"
        "  • atd_hits_q[0..15][31:0]  (hits per LRU depth)\n"
        "  • atd_acc_q[31:0]          (total sampled accesses)\n"
        "  • epoch_acc_q[31:0]        (++ on l2_req_valid_i in S_IDLE)\n"
        "Epoch Trigger (epoch_acc_q >= 2048):\n"
        "  • epoch_acc_q <= 0;  cnt_epochs_o++\n"
        "  • Exponential Decay: atd_hits_q[d] >>= 1; atd_acc_q >>= 1",
        fc="#FFFFFF", ec="#0F766E", lw=1.4, tsize=8.3, bsize=6.8, top=True)

    wire(ax, 10.80, 8.10, 11.55, 8.10, label="hit_depth", color="#0F766E", lw=1.4, ldy=0.18, lsize=6.7)

    # 4. Epoch Decision Datapath (Middle Row)
    blk(ax, 0.65, 4.45, 4.20, 2.10,
        "Streaming Detector",
        "Adder Tree:\n"
        "  total_atd_hits = sum(atd_hits_q[0..15])\n\n"
        "Comparator (< 5% ATD Hit Rate):\n"
        "  is_stream = (total_atd_hits == 0) |\n"
        "              (total_atd_hits * 20 < atd_acc_q)\n"
        "-> Stream Target = 4 ways",
        fc="#EFF6FF", ec="#1D4ED8", lw=1.4, tsize=8.3, bsize=6.9, top=True)

    blk(ax, 5.30, 4.45, 5.05, 2.10,
        "98.5% Marginal-Hit Utility Selector",
        "Prefix-Sum Adder (d = 0..15):\n"
        "  cum_atd_hits[d] = sum(atd_hits_q[0..d])\n"
        "Threshold Comparator:\n"
        "  first d where (cum_atd_hits[d] * 1000 >= total * 985)\n"
        "  k_opt = max(MIN_WAYS, d + 1)\n"
        "Even-Aligner & Clamp:\n"
        "  if (k_opt[0] == 1) k_opt += 1;  clamp [2..16]",
        fc="#EFF6FF", ec="#1D4ED8", lw=1.4, tsize=8.3, bsize=6.9, top=True)

    mux(ax, 10.85, 4.95, 0.78, 1.15, label="MUX\nstream")
    # Route Streaming Detector output cleanly below Utility Selector into MUX top/bottom
    ax.plot([2.75, 2.75, 10.60, 10.60, 10.85], [4.45, 4.26, 4.26, 5.80, 5.80], color="#1D4ED8", lw=1.3, zorder=3)
    wire(ax, 10.60, 5.80, 10.85, 5.80, color="#1D4ED8", lw=1.3)
    ax.text(6.65, 4.26, "is_stream ? 4'd4", ha="center", va="center",
            fontsize=6.6, fontweight="bold", color="#1D4ED8",
            bbox=dict(boxstyle="round,pad=0.10", fc="white", ec="none"), zorder=5)
    ax.text(5.10, 6.72, "atd_hits_q[0..15], atd_acc_q", ha="center", va="center",
            fontsize=6.9, fontweight="bold", color="#0F766E",
            bbox=dict(boxstyle="round,pad=0.10", fc="white", ec="none"), zorder=5)
    # Route atd_hits_q from top-right down to Streaming Detector & Utility Selector
    ax.plot([14.20, 14.20, 2.75, 2.75], [7.10, 6.72, 6.72, 6.55], color="#0F766E", lw=1.3, zorder=3)
    wire(ax, 2.75, 6.72, 2.75, 6.55, color="#0F766E", lw=1.3)
    wire(ax, 7.80, 6.72, 7.80, 6.55, color="#0F766E", lw=1.3)

    wire(ax, 10.35, 5.25, 10.85, 5.25, label="k_opt", color="#1D4ED8", lw=1.3, ldy=-0.18, lsize=6.5)

    # 5. Direction Comparator & Dirty-Flush Cost Guard (Middle-Right)
    blk(ax, 12.40, 4.45, 4.45, 2.10,
        "Direction Comparator &\nWrite-Back Dirty-Flush Cost Guard",
        "Compare calc_target_ways[4:0] vs cur_ways_q[4:0]:\n"
        "• target > cur_ways_q  -->  WAKEUP_REQ (0 -> 1)\n"
        "• target < cur_ways_q  -->  Check Dirty Guard:\n"
        "    top_way = cur_ways_q - 1\n"
        "    guard_ok = (way_dirty_cnt_i[top_way] <= 96)\n"
        "    if (guard_ok) --> SHUTDOWN_REQ (1 -> 0)\n"
        "    else          --> ABORT (stay S_IDLE)",
        fc="#FEF9C3", ec="#A16207", lw=1.6, tsize=8.2, bsize=6.8, top=True)

    wire(ax, 11.63, 5.52, 12.40, 5.52, label="calc_target\n[4:0]", color="#1D4ED8", lw=1.4, ldy=0.25, lsize=6.6)

    # 6. 3-State Power-Gating & Wakeup FSM (Bottom-Left/Center)
    blk(ax, 0.65, 1.00, 10.30, 2.90,
        "3-State Power-Gating & Dirty-Flush Handshake FSM (state_q[1:0], cur_ways_q[4:0], target_ways_q[4:0])",
        fc="#E0F2FE", ec="#0369A1", lw=1.6, tsize=8.5, tc="#0C4A6E", top=True)

    blk(ax, 0.90, 1.25, 2.75, 2.10,
        "S_IDLE (2'd0)",
        "• flush_req_o <= 0\n"
        "• if !ws_enable_i:\n"
        "    way_en <= 16'hFFFF\n"
        "    way_sd <= 16'h0000\n"
        "• On Epoch trigger:\n"
        "    -> S_FLUSH_WAY\n"
        "    or S_WAKEUP_WAIT",
        fc="#FFFFFF", ec="#0369A1", lw=1.3, tsize=8.0, bsize=6.6, top=True)

    blk(ax, 4.25, 1.25, 3.15, 2.10,
        "S_FLUSH_WAY (2'd1)",
        "1->0 Shutdown Sequence:\n"
        "• way_en_o[w] <= 0; flush_req_o <= 1\n"
        "• Wait flush_done_i:\n"
        "    way_sd_o[w] <= 1 (Power-Gate)\n"
        "    cur_ways_q--; cnt_shutdowns++\n"
        "• Chain next way if (> target &\n"
        "  dirty_cnt <= 96), else -> S_IDLE",
        fc="#FEE2E2", ec="#B91C1C", lw=1.3, tsize=8.0, bsize=6.5, top=True)

    blk(ax, 7.95, 1.25, 2.75, 2.10,
        "S_WAKEUP_WAIT (2'd2)",
        "0->1 Wakeup Sequence:\n"
        "• way_sd_o <= ~mask(target)\n"
        "• wakeup_stall_o = 1'b1\n"
        "• wakeup_cnt_q: 6 -> 1\n"
        "• On wakeup_cnt_q == 1:\n"
        "    way_en_o <= mask(target)\n"
        "    cur_ways_q <= target -> S_IDLE",
        fc="#DCFCE7", ec="#15803D", lw=1.3, tsize=8.0, bsize=6.5, top=True)

    wire(ax, 3.65, 2.55, 4.25, 2.55, label="SD", color="#B91C1C", lw=1.3, ldy=0.16, lsize=6.5)
    wire(ax, 4.25, 1.85, 3.65, 1.85, label="done", color="#0369A1", lw=1.2, ldy=-0.16, lsize=6.4)
    wire(ax, 2.25, 1.25, 9.30, 1.25, label="WU (target > cur) / wakeup done -> S_IDLE",
         color="#15803D", lw=1.2, style="<|-|>", rad=0.14, ldy=-0.38, lsize=6.6)

    # Connect Comparator -> FSM
    ax.plot([14.60, 14.60, 5.82, 5.82], [4.45, 4.12, 4.12, 3.90], color="#A16207", lw=1.4, zorder=3)
    wire(ax, 5.82, 4.12, 5.82, 3.90, label="SHUTDOWN_REQ / WAKEUP_REQ", color="#A16207", lw=1.4, ldx=3.2, ldy=0.12, lsize=6.8)

    # 7. Output Decoder & Cycle-Accurate Active-Way Counter (Bottom-Right)
    blk(ax, 11.45, 1.00, 5.40, 2.90,
        "Output Mask Decoder & Telemetry Counters",
        "Combinational Function: ways_to_mask(k[4:0]) -> [15:0]\n"
        "  mask[w] = (w < k) ? 1'b1 : 1'b0\n\n"
        "Control Outputs to cva6_shared_l2_16way_ws:\n"
        "  • way_en_o[15:0],  way_sd_o[15:0],  wakeup_stall_o\n"
        "  • flush_req_o,     flush_way_o[3:0]\n\n"
        "Cycle-Accurate Leakage Telemetry:\n"
        "  powered_way_count = popcount(~way_sd_o[15:0])\n"
        "  cnt_active_way_cycles_o += powered_way_count\n"
        "  cnt_epochs_o, cnt_shutdowns_o, cnt_wakeups_o",
        fc="#F1F5F9", ec="#475569", lw=1.4, tsize=8.2, bsize=6.8, top=True)

    wire(ax, 10.95, 2.45, 11.45, 2.45, color="#0369A1", lw=1.5)

    save_fig(fig, docs_dir, "diagram_3_l2_way_shutdown_ctrl")


def main():
    docs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs"))
    draw_top(docs_dir)
    draw_shared_l2(docs_dir)
    draw_ws_ctrl(docs_dir)


if __name__ == "__main__":
    main()
