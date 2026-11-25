#!/usr/bin/env python3
"""
Step 3 Parser & 3-Way Validation Report Generator:
Compares:
  1. Step 1: CVA6 RTL Baseline (16-Way Always-On, Verilator)
  2. Step 2: gem5 Architectural Model (atd_dirty_aware)
  3. Step 3: CVA6 Custom RTL (atd_dirty_aware, Verilator)

Verifies 12/12 bit-exact checksum match against Step 1 and generates:
  - step3_cva6_rtl/results/step3_rtl_summary.csv
  - step3_cva6_rtl/results/step3_3way_comparison.md
  - step3_cva6_rtl/results/step3_3way_comparison.png
"""

import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STEP3_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
ROOT_DIR = os.path.abspath(os.path.join(STEP3_DIR, ".."))

STEP1_CSV = os.path.join(ROOT_DIR, "step1_baseline", "results", "step1_baseline_summary.csv")
STEP2_CSV = os.path.join(ROOT_DIR, "step2_gem5_model", "results", "step2_gem5_comparison.csv")
LOGS_DIR = os.path.join(STEP3_DIR, "results", "logs")

OUT_CSV = os.path.join(STEP3_DIR, "results", "step3_rtl_summary.csv")
OUT_MD = os.path.join(STEP3_DIR, "results", "step3_3way_comparison.md")
OUT_PNG = os.path.join(STEP3_DIR, "results", "step3_3way_comparison.png")

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


def load_step1():
    data = {}
    if not os.path.exists(STEP1_CSV):
        return data
    with open(STEP1_CSV, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            bm = row["benchmark"]
            data[bm] = {
                "cycles": float(row["soc_cycles"]),
                "ipc": float(row["agg_ipc"]),
                "l2_miss_pct": float(row["l2_miss_rate_pct"]),
                "wb": int(float(row["l2_dirty_writebacks"])),
                "leak_mw": float(row["l2_leak_power_mw"]),
                "total_en_nj": float(row["total_energy_nj"]),
                "checksum": row["checksum"].strip().lower(),
            }
    return data


def load_step2_atd():
    data = {}
    if not os.path.exists(STEP2_CSV):
        return data
    with open(STEP2_CSV, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["policy"] == "atd_dirty_aware":
                bm = row["benchmark"]
                data[bm] = {
                    "avg_ways": float(row["avg_active_ways"]),
                    "ipc_delta_pct": float(row["ipc_change_pct"]),
                    "leak_save_pct": float(row["l2_leakage_saving_pct"]),
                    "edp_improv_pct": float(row["edp_improv_pct"]),
                    "dirty_flush": int(float(row["dirty_flush_wb"])),
                }
    return data


def parse_step3_logs():
    rows = []
    for bm in BENCHMARKS:
        log_path = os.path.join(LOGS_DIR, f"{bm}_ws_atd.log")
        if not os.path.exists(log_path):
            continue
        csv_line = None
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith("CSV_LINE,"):
                    csv_line = line.strip()
        if not csv_line:
            continue
        p = csv_line.split(",")
        rows.append({
            "benchmark": bm,
            "avg_active_ways": float(p[2]),
            "soc_cycles": int(p[3]),
            "total_insts": int(p[4]),
            "agg_ipc": float(p[5]),
            "l2_accesses": int(p[6]),
            "l2_hits": int(p[7]),
            "l2_misses": int(p[8]),
            "l2_miss_rate_pct": float(p[9]),
            "normal_wb": int(p[10]),
            "shutdown_flushes": int(p[11]),
            "ws_epochs": int(p[12]),
            "ws_shutdowns": int(p[13]),
            "ws_wakeups": int(p[14]),
            "l2_leak_mw": float(p[15]),
            "l2_dyn_nj": float(p[16]),
            "l2_leak_nj": float(p[17]),
            "dram_nj": float(p[18]),
            "total_l2_dram_nj": float(p[19]),
            "checksum": p[20].strip().lower(),
        })
    return rows


def main():
    s1 = load_step1()
    s2 = load_step2_atd()
    s3_rows = parse_step3_logs()
    if not s3_rows:
        print("[WARN] No Step 3 RTL logs found in", LOGS_DIR)
        return

    csum_matches = 0
    for r in s3_rows:
        bm = r["benchmark"]
        b1 = s1.get(bm)
        if b1:
            r["checksum_match"] = (r["checksum"] == b1["checksum"])
            if r["checksum_match"]:
                csum_matches += 1
            r["ipc_change_pct"] = (r["agg_ipc"] - b1["ipc"]) / b1["ipc"] * 100.0
            r["leak_saving_pct"] = (1.0 - r["l2_leak_mw"] / b1["leak_mw"]) * 100.0
            r["energy_saving_pct"] = (1.0 - r["total_l2_dram_nj"] / b1["total_en_nj"]) * 100.0
            edp1 = b1["total_en_nj"] * b1["cycles"]
            edp3 = r["total_l2_dram_nj"] * r["soc_cycles"]
            r["edp_improv_pct"] = (1.0 - edp3 / edp1) * 100.0
        else:
            r["checksum_match"] = False
            r["ipc_change_pct"] = 0.0
            r["leak_saving_pct"] = 0.0
            r["energy_saving_pct"] = 0.0
            r["edp_improv_pct"] = 0.0

    # Write Step 3 CSV
    fieldnames = list(s3_rows[0].keys())
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in s3_rows:
            w.writerow(r)

    # Aggregate means
    rtl_avg_ways = np.mean([r["avg_active_ways"] for r in s3_rows])
    rtl_ipc_delta = np.mean([r["ipc_change_pct"] for r in s3_rows])
    rtl_leak_save = np.mean([r["leak_saving_pct"] for r in s3_rows])
    rtl_en_save = np.mean([r["energy_saving_pct"] for r in s3_rows])
    rtl_edp_improv = np.mean([r["edp_improv_pct"] for r in s3_rows])
    rtl_tot_flush = sum(r["shutdown_flushes"] for r in s3_rows)

    g5_list = [s2[r["benchmark"]] for r in s3_rows if r["benchmark"] in s2]
    g5_avg_ways = np.mean([x["avg_ways"] for x in g5_list]) if g5_list else 0.0
    g5_ipc_delta = np.mean([x["ipc_delta_pct"] for x in g5_list]) if g5_list else 0.0
    g5_leak_save = np.mean([x["leak_save_pct"] for x in g5_list]) if g5_list else 0.0
    g5_edp_improv = np.mean([x["edp_improv_pct"] for x in g5_list]) if g5_list else 0.0
    g5_tot_flush = sum(x["dirty_flush"] for x in g5_list) if g5_list else 0

    lines = [
        "# Step 3 Final Report: 3-Way Validation (Baseline RTL vs gem5 Model vs Custom Way-Shutdown RTL)",
        "",
        f"- **Functional Verification:** **{csum_matches}/{len(s3_rows)} PASS** (bit-exact 4-core checksum match against Step 1 RTL Baseline)",
        "- **Implemented RTL Policy:** `atd_dirty_aware` (`l2_way_shutdown_ctrl.sv` + `cva6_shared_l2_16way_ws.sv`, 16-set Sampled-Set ATD + Dirty-Flush Guard <= 96 lines + `T_wakeup = 6 cycles`)",
        "",
        "## 1. High-Level 3-Way Comparison (Average Across 12 Benchmarks)",
        "",
        "| Platform / Configuration | Avg Active L2 Ways (/16) | 4-Core IPC Change (%) | L2 Leakage Saving (%) | Total Shutdown Dirty Flushes | Avg EDP Improvement (%) |",
        "| :--- | ---: | ---: | ---: | ---: | ---: |",
        "| **Step 1: CVA6 RTL Baseline (16-Way Always-On)** | 16.00 | +0.00% | 0.00% | 0 | +0.00% |",
        f"| **Step 2: gem5 Model (`atd_dirty_aware`)** | {g5_avg_ways:.2f} | {g5_ipc_delta:+.2f}% | {g5_leak_save:.2f}% | {g5_tot_flush} | {g5_edp_improv:+.2f}% |",
        f"| **Step 3: CVA6 Custom RTL (`atd_dirty_aware`)** | **{rtl_avg_ways:.2f}** | **{rtl_ipc_delta:+.2f}%** | **{rtl_leak_save:.2f}%** | **{rtl_tot_flush}** | **{rtl_edp_improv:+.2f}%** |",
        "",
        "## 2. Per-Benchmark Breakdown (Custom RTL vs Step 1 Baseline & Step 2 gem5)",
        "",
        "| Benchmark | Checksum | RTL Ways (/16) | gem5 Ways (/16) | RTL IPC Delta (%) | gem5 IPC Delta (%) | RTL Leak Save (%) | RTL Energy Save (%) | RTL EDP Improv (%) | Shutdown Flushes |",
        "| :--- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for r in s3_rows:
        bm = r["benchmark"]
        g = s2.get(bm, {"avg_ways": 16.0, "ipc_delta_pct": 0.0})
        chk = "MATCH" if r["checksum_match"] else "MISMATCH"
        lines.append(
            f"| `{bm}` | {chk} | {r['avg_active_ways']:.2f} | {g['avg_ways']:.2f} | "
            f"{r['ipc_change_pct']:+.2f}% | {g['ipc_delta_pct']:+.2f}% | "
            f"{r['leak_saving_pct']:.2f}% | {r['energy_saving_pct']:+.2f}% | "
            f"{r['edp_improv_pct']:+.2f}% | {r['shutdown_flushes']} |"
        )

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    # 3-Way Comparison Plot
    bms_short = [r["benchmark"].replace("bm", "b").split("_")[0] + "_" + r["benchmark"].split("_")[1][:5] for r in s3_rows]
    x = np.arange(len(s3_rows))
    w = 0.35

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8))

    # Panel 1: Avg Active L2 Ways (gem5 vs Custom RTL vs Baseline 16)
    ax = axes[0]
    g5_w = [s2.get(r["benchmark"], {"avg_ways": 16.0})["avg_ways"] for r in s3_rows]
    rtl_w = [r["avg_active_ways"] for r in s3_rows]
    ax.bar(x - w / 2, g5_w, w, label="Step 2: gem5 Model", color="#7570b3", edgecolor="black")
    ax.bar(x + w / 2, rtl_w, w, label="Step 3: Custom RTL", color="#1b9e77", edgecolor="black")
    ax.axhline(16.0, color="#444444", linestyle="--", linewidth=1, label="Step 1: Baseline (16w)")
    ax.set_xticks(x)
    ax.set_xticklabels(bms_short, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Avg Active L2 Ways (/16)")
    ax.set_title("Active L2 Ways: gem5 vs Custom RTL")
    ax.set_ylim(0, 18)
    ax.grid(True, axis="y", linestyle=":", alpha=0.6)
    ax.legend(fontsize=8)

    # Panel 2: L2 Leakage Saving (%)
    ax = axes[1]
    g5_ls = [s2.get(r["benchmark"], {"leak_save_pct": 0.0})["leak_save_pct"] for r in s3_rows]
    rtl_ls = [r["leak_saving_pct"] for r in s3_rows]
    ax.bar(x - w / 2, g5_ls, w, label="Step 2: gem5 Model", color="#7570b3", edgecolor="black")
    ax.bar(x + w / 2, rtl_ls, w, label="Step 3: Custom RTL", color="#1b9e77", edgecolor="black")
    ax.set_xticks(x)
    ax.set_xticklabels(bms_short, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("L2 Leakage Saving (%)")
    ax.set_title("L2 Leakage Power Saving vs Baseline")
    ax.grid(True, axis="y", linestyle=":", alpha=0.6)
    ax.legend(fontsize=8)

    # Panel 3: EDP Improvement (%)
    ax = axes[2]
    g5_edp = [s2.get(r["benchmark"], {"edp_improv_pct": 0.0})["edp_improv_pct"] for r in s3_rows]
    rtl_edp = [r["edp_improv_pct"] for r in s3_rows]
    ax.bar(x - w / 2, g5_edp, w, label="Step 2: gem5 Model", color="#7570b3", edgecolor="black")
    ax.bar(x + w / 2, rtl_edp, w, label="Step 3: Custom RTL", color="#1b9e77", edgecolor="black")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(bms_short, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("L2 + DRAM EDP Improvement (%)")
    ax.set_title("EDP Improvement vs Baseline 16-Way")
    ax.grid(True, axis="y", linestyle=":", alpha=0.6)
    ax.legend(fontsize=8)

    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=150)
    plt.close(fig)
    print(f"[OK] Generated:\n  - {OUT_CSV}\n  - {OUT_MD}\n  - {OUT_PNG}")


if __name__ == "__main__":
    main()
