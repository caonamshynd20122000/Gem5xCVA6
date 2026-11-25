#!/usr/bin/env python3
"""
Parse gem5 Step 2 stats (12 benchmarks x 8 configs), apply CACTI 7.0 (22nm)
power/energy model for 512 KiB 16-Way Write-Back Shared L2 Cache, and generate:
  - results/step2_gem5_comparison.csv
  - results/step2_gem5_report.md
  - results/step2_pareto_comparison.png
"""

import csv
import math
import os
import re
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

STEP2_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOGS_DIR = os.path.join(STEP2_DIR, "results", "logs")
OUT_CSV = os.path.join(STEP2_DIR, "results", "step2_gem5_comparison.csv")
OUT_MD = os.path.join(STEP2_DIR, "results", "step2_gem5_report.md")
OUT_PNG = os.path.join(STEP2_DIR, "results", "step2_pareto_comparison.png")

BENCHMARKS = [
    "bm01_coremark",
    "bm02_dhrystone",
    "bm03_matmul",
    "bm04_spmv",
    "bm05_qsort_rsort",
    "bm06_vvadd",
    "bm07_memcpy",
    "bm08_l2_light_1core",
    "bm09_l2_medium_2cores",
    "bm10_l2_heavy_4cores",
    "bm11_l2_stream_mix",
    "bm12_l2_dynamic_4phases",
]

TAGS = [
    "static16",
    "static12",
    "static8",
    "static4",
    "static2",
    "selective_ways",
    "way_util",
    "atd_dirty_aware",
]

# CACTI 7.0 (22nm) model constants for 512 KiB, 16-Way, 64B Line Shared L2 Cache
L2_PERIPH_LEAK_MW = 18.041          # Peripheral leakage (always-on)
L2_WAY_LEAK_MW = 5.8553             # SRAM cell leakage per active way (16 * 5.8553 = 93.685 mW; total = 111.726 mW)
L2_BASE_LEAK_MW = L2_PERIPH_LEAK_MW + 16.0 * L2_WAY_LEAK_MW
L2_TAG_ACCESS_PJ = 0.25             # Dynamic energy per probed way tag (pJ)
L2_DATA_ACCESS_PJ = 1.228           # Dynamic energy per probed way data array (pJ)
DRAM_LINE_ACCESS_NJ = 1.50          # 64B DRAM read/writeback energy (nJ)

STAT_LINE_RE = re.compile(r"^([A-Za-z0-9_.:-]+)\s+([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?|nan|inf)")


def parse_stats_file(path):
    stats = {}
    if not os.path.exists(path):
        return stats
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = STAT_LINE_RE.match(line.strip())
            if m:
                key, val = m.group(1), m.group(2)
                try:
                    v = float(val)
                    if not math.isnan(v) and not math.isinf(v):
                        stats[key] = v
                except ValueError:
                    pass
    return stats


def get_first(stats, keys, default=0.0):
    for k in keys:
        if k in stats:
            return stats[k]
    return default


def extract_metrics(bm, tag, stats):
    sim_sec = get_first(stats, ["simSeconds"], 0.0)
    sim_ticks = get_first(stats, ["simTicks"], 0.0)
    if sim_sec == 0.0 and sim_ticks > 0.0:
        sim_sec = sim_ticks * 1e-12

    # 4-Core Aggregate IPC
    total_ipc = 0.0
    for c in range(4):
        total_ipc += get_first(stats, [f"system.cpu{c}.ipc"], 0.0)

    l2_accesses = get_first(stats, ["system.l2cache.overallAccesses::total"], 0.0)
    l2_misses = get_first(stats, ["system.l2cache.overallMisses::total"], 0.0)
    l2_miss_rate = (l2_misses / l2_accesses * 100.0) if l2_accesses > 0 else 0.0

    normal_wb = get_first(stats, ["system.l2cache.writebacks::total"], 0.0)
    dirty_flush_wb = get_first(stats, ["system.l2cache.tags.way_shutdown.dirtyFlushWritebacks"], 0.0)
    total_wb = normal_wb + dirty_flush_wb

    tag_accesses = get_first(stats, ["system.l2cache.tags.tagAccesses"], 0.0)
    data_accesses = get_first(stats, ["system.l2cache.tags.dataAccesses"], 0.0)
    active_way_accum = get_first(stats, ["system.l2cache.tags.way_shutdown.activeWayAccessAccum"], 0.0)
    epochs_eval = get_first(stats, ["system.l2cache.tags.way_shutdown.epochsEvaluated"], 0.0)
    shutdown_events = get_first(stats, ["system.l2cache.tags.way_shutdown.wayShutdownEvents"], 0.0)
    wakeup_events = get_first(stats, ["system.l2cache.tags.way_shutdown.wayWakeupEvents"], 0.0)

    way_active_sum = sum(
        get_first(stats, [f"system.l2cache.tags.way_shutdown.wayActiveEpochs::{w}"], 0.0)
        for w in range(16)
    )
    if tag.startswith("static"):
        avg_active_ways = float(tag.replace("static", ""))
    elif epochs_eval > 0 and way_active_sum > 0:
        avg_active_ways = way_active_sum / epochs_eval
    else:
        avg_active_ways = 16.0
    avg_active_ways = max(1.0, min(16.0, avg_active_ways))

    # CACTI 7.0 (22nm) Power & Energy
    leakage_mw = L2_PERIPH_LEAK_MW + avg_active_ways * L2_WAY_LEAK_MW
    leakage_saving_pct = (1.0 - leakage_mw / L2_BASE_LEAK_MW) * 100.0

    # Energy in nJ: mW * s = mJ -> * 1e6 = nJ; pJ * 1e-3 = nJ
    l2_leak_energy_nj = leakage_mw * sim_sec * 1e6
    l2_dyn_energy_nj = (tag_accesses * L2_TAG_ACCESS_PJ + data_accesses * L2_DATA_ACCESS_PJ) * 1e-3
    dram_energy_nj = (l2_misses + total_wb) * DRAM_LINE_ACCESS_NJ
    total_energy_nj = l2_leak_energy_nj + l2_dyn_energy_nj + dram_energy_nj
    edp = total_energy_nj * (sim_sec * 1e6)  # nJ * us

    return {
        "benchmark": bm,
        "policy": tag,
        "sim_us": sim_sec * 1e6,
        "avg_active_ways": avg_active_ways,
        "ipc_4core": total_ipc,
        "l2_accesses": l2_accesses,
        "l2_misses": l2_misses,
        "l2_miss_rate_pct": l2_miss_rate,
        "normal_wb": normal_wb,
        "dirty_flush_wb": dirty_flush_wb,
        "shutdown_events": shutdown_events,
        "wakeup_events": wakeup_events,
        "epochs_eval": epochs_eval,
        "l2_leakage_mw": leakage_mw,
        "l2_leakage_saving_pct": leakage_saving_pct,
        "l2_energy_nj": l2_leak_energy_nj + l2_dyn_energy_nj,
        "dram_energy_nj": dram_energy_nj,
        "total_energy_nj": total_energy_nj,
        "edp": edp,
    }


def main():
    rows = []
    baseline_map = {}

    for bm in BENCHMARKS:
        base_stats = parse_stats_file(os.path.join(LOGS_DIR, f"{bm}__static16", "stats.txt"))
        if base_stats:
            baseline_map[bm] = extract_metrics(bm, "static16", base_stats)

    for tag in TAGS:
        for bm in BENCHMARKS:
            stats_path = os.path.join(LOGS_DIR, f"{bm}__{tag}", "stats.txt")
            stats = parse_stats_file(stats_path)
            if not stats:
                continue
            m = extract_metrics(bm, tag, stats)
            base = baseline_map.get(bm)
            if base and base["ipc_4core"] > 0 and base["edp"] > 0:
                m["ipc_change_pct"] = (m["ipc_4core"] - base["ipc_4core"]) / base["ipc_4core"] * 100.0
                m["edp_improv_pct"] = (1.0 - m["edp"] / base["edp"]) * 100.0
            else:
                m["ipc_change_pct"] = 0.0
                m["edp_improv_pct"] = 0.0
            rows.append(m)

    if not rows:
        print("[WARN] Khong tim thay file stats.txt nao trong", LOGS_DIR)
        return

    fieldnames = [
        "benchmark", "policy", "sim_us", "avg_active_ways",
        "ipc_4core", "ipc_change_pct", "l2_accesses", "l2_misses",
        "l2_miss_rate_pct", "normal_wb", "dirty_flush_wb",
        "shutdown_events", "wakeup_events", "l2_leakage_mw",
        "l2_leakage_saving_pct", "l2_energy_nj", "dram_energy_nj",
        "total_energy_nj", "edp_improv_pct",
    ]
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # Aggregate summary per policy
    by_pol = defaultdict(list)
    for r in rows:
        by_pol[r["policy"]].append(r)

    summary = []
    for tag in TAGS:
        grp = by_pol.get(tag, [])
        if not grp:
            continue
        summary.append({
            "policy": tag,
            "n": len(grp),
            "avg_ways": np.mean([x["avg_active_ways"] for x in grp]),
            "ipc_delta": np.mean([x["ipc_change_pct"] for x in grp]),
            "miss_rate": np.mean([x["l2_miss_rate_pct"] for x in grp]),
            "dirty_flushes": np.sum([x["dirty_flush_wb"] for x in grp]),
            "leak_mw": np.mean([x["l2_leakage_mw"] for x in grp]),
            "leak_save": np.mean([x["l2_leakage_saving_pct"] for x in grp]),
            "edp_improv": np.mean([x["edp_improv_pct"] for x in grp]),
        })

    # Select winning dynamic policy (best EDP improvement among policies with IPC drop <= 2%)
    dynamic_cands = [s for s in summary if s["policy"] in ("selective_ways", "way_util", "atd_dirty_aware")]
    winner = None
    if dynamic_cands:
        feasible = [s for s in dynamic_cands if s["ipc_delta"] >= -2.0]
        pool = feasible if feasible else dynamic_cands
        winner = max(pool, key=lambda x: x["edp_improv"])

    # Write Markdown report
    lines = [
        "# Step 2 Report: gem5 4-Core CVA6 + 16-Way Shared L2 Way-Shutdown DSE",
        "",
        "## 1. Average Summary Across 12 Benchmarks (CACTI 7.0 22nm)",
        "",
        "| Policy | Benchmarks | Avg Active Ways (/16) | IPC Change (%) | Avg L2 Miss Rate (%) | Total Dirty Flushes | Avg L2 Leakage (mW) | L2 Leakage Saving (%) | Avg EDP Improvement (%) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for s in summary:
        lines.append(
            f"| `{s['policy']}` | {s['n']} | {s['avg_ways']:.2f} | {s['ipc_delta']:+.2f}% | "
            f"{s['miss_rate']:.2f}% | {int(s['dirty_flushes'])} | {s['leak_mw']:.2f} | "
            f"{s['leak_save']:.2f}% | {s['edp_improv']:+.2f}% |"
        )

    if winner:
        lines.extend([
            "",
            "## 2. Selected Design for Step 3 (SystemVerilog RTL)",
            "",
            f"- **Winning Policy:** `{winner['policy']}`",
            f"- **Avg Active L2 Ways:** {winner['avg_ways']:.2f} / 16",
            f"- **4-Core Aggregate IPC Change:** {winner['ipc_delta']:+.2f}%",
            f"- **L2 Leakage Power Saving:** {winner['leak_save']:.2f}%",
            f"- **L2 + DRAM EDP Improvement:** {winner['edp_improv']:+.2f}%",
        ])

    lines.extend([
        "",
        "## 3. Per-Benchmark Breakdown (Dynamic Policies vs Baseline 16-Way)",
        "",
        "| Benchmark | Policy | Active Ways | IPC 4-Core | IPC Change (%) | L2 Miss (%) | Dirty Flush | Leakage Save (%) | EDP Improv (%) |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for bm in BENCHMARKS:
        for tag in ("static16", "selective_ways", "way_util", "atd_dirty_aware"):
            match = [r for r in rows if r["benchmark"] == bm and r["policy"] == tag]
            if not match:
                continue
            r = match[0]
            lines.append(
                f"| `{bm}` | `{tag}` | {r['avg_active_ways']:.2f} | {r['ipc_4core']:.3f} | "
                f"{r['ipc_change_pct']:+.2f}% | {r['l2_miss_rate_pct']:.2f}% | "
                f"{int(r['dirty_flush_wb'])} | {r['l2_leakage_saving_pct']:.2f}% | {r['edp_improv_pct']:+.2f}% |"
            )

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    # Plot Pareto comparison
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    colors = {
        "static16": "#444444",
        "static12": "#888888",
        "static8": "#aaaaaa",
        "static4": "#cccccc",
        "static2": "#dddddd",
        "selective_ways": "#d95f02",
        "way_util": "#7570b3",
        "atd_dirty_aware": "#1b9e77",
    }

    ax = axes[0]
    for s in summary:
        c = colors.get(s["policy"], "#333333")
        sz = 140 if s["policy"] in ("selective_ways", "way_util", "atd_dirty_aware") else 80
        ax.scatter(s["leak_save"], s["ipc_delta"], s=sz, color=c, edgecolors="black", zorder=3)
        ax.annotate(s["policy"], (s["leak_save"], s["ipc_delta"]), xytext=(5, 4),
                    textcoords="offset points", fontsize=8)
    ax.axhline(-2.0, color="red", linestyle="--", linewidth=1, label="IPC Drop Limit (-2%)")
    ax.set_xlabel("L2 Leakage Power Saving (%)")
    ax.set_ylabel("4-Core Aggregate IPC Change (%)")
    ax.set_title("Pareto: L2 Leakage Saving vs 4-Core IPC Change")
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(fontsize=8)

    ax2 = axes[1]
    pol_names = [s["policy"] for s in summary]
    edp_vals = [s["edp_improv"] for s in summary]
    bar_colors = [colors.get(p, "#333333") for p in pol_names]
    ax2.bar(range(len(pol_names)), edp_vals, color=bar_colors, edgecolor="black")
    ax2.set_xticks(range(len(pol_names)))
    ax2.set_xticklabels(pol_names, rotation=30, ha="right", fontsize=8)
    ax2.axhline(0, color="black", linewidth=0.8)
    ax2.set_ylabel("Avg EDP Improvement (%)")
    ax2.set_title("L2 + DRAM EDP Improvement vs Baseline 16-Way")
    ax2.grid(True, axis="y", linestyle=":", alpha=0.6)

    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=150)
    plt.close(fig)
    print(f"[OK] Generated:\n  - {OUT_CSV}\n  - {OUT_MD}\n  - {OUT_PNG}")


if __name__ == "__main__":
    main()
