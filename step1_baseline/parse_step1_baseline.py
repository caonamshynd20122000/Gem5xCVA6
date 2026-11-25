#!/usr/bin/env python3
"""Parse Step 1 CVA6 4-Core + 16-Way Shared L2 RTL Verilator logs into CSV & Markdown reports."""

import csv
import glob
import os

STEP1_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(STEP1_DIR, "results")
LOG_DIR = os.path.join(RESULTS_DIR, "logs")


def main():
    rows = []
    for log_path in sorted(glob.glob(os.path.join(LOG_DIR, "*.log"))):
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("CSV_LINE,"):
                    parts = line.strip().split(",")
                    if len(parts) >= 16:
                        elf_name = os.path.basename(parts[1]).replace(".elf", "")
                        rows.append({
                            "benchmark": elf_name,
                            "l2_active_ways": int(parts[2]),
                            "soc_cycles": int(parts[3]),
                            "total_insts": int(parts[4]),
                            "agg_ipc": float(parts[5]),
                            "l2_accesses": int(parts[6]),
                            "l2_hits": int(parts[7]),
                            "l2_misses": int(parts[8]),
                            "l2_miss_rate_pct": float(parts[9]),
                            "l2_dirty_writebacks": int(parts[10]),
                            "l2_leak_power_mw": float(parts[11]),
                            "l2_dyn_energy_nj": float(parts[12]),
                            "l2_leak_energy_nj": float(parts[13]),
                            "dram_energy_nj": float(parts[14]),
                            "total_energy_nj": float(parts[15]),
                            "checksum": parts[16],
                        })

    if not rows:
        print("No CSV_LINE records found in logs.")
        return

    rows.sort(key=lambda r: (r["benchmark"], -r["l2_active_ways"]))

    csv_path = os.path.join(RESULTS_DIR, "step1_baseline_summary.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved CSV: {csv_path}")

    md_path = os.path.join(RESULTS_DIR, "step1_baseline_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Bước 1 — Kết quả Mô phỏng CVA6 4-Core + 16-Way Shared L2 Baseline (Verilator RTL)\n\n")
        f.write("| Benchmark | L2 Ways | SoC Cycles | 4-Core Insts | Agg. IPC | L2 Accesses | L2 Hits | L2 Misses | L2 Miss Rate | L2 Dirty WB | L2 Leak (mW) | L2 Dyn+Leak (nJ) | Total L2+DRAM (nJ) | Checksum |\n")
        f.write("| :--- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |\n")
        for r in rows:
            l2_en = r["l2_dyn_energy_nj"] + r["l2_leak_energy_nj"]
            f.write(
                f"| `{r['benchmark']}` | **{r['l2_active_ways']}/16** | {r['soc_cycles']:,} | "
                f"{r['total_insts']:,} | {r['agg_ipc']:.4f} | {r['l2_accesses']:,} | "
                f"{r['l2_hits']:,} | {r['l2_misses']:,} | {r['l2_miss_rate_pct']:.2f}% | "
                f"{r['l2_dirty_writebacks']:,} | {r['l2_leak_power_mw']:.2f} | "
                f"{l2_en:,.1f} | {r['total_energy_nj']:,.1f} | `{r['checksum']}` |\n"
            )
    print(f"Saved Markdown Report: {md_path}")


if __name__ == "__main__":
    main()
