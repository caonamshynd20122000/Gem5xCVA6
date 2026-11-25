#!/usr/bin/env python3
"""
Apply WayShutdownSetAssoc C++ & SimObject patch into gem5/src/mem/cache/tags/.
Copies way_shutdown_tags.{hh,cc} and registers WayShutdownSetAssoc in Tags.py and SConscript.
"""

import os
import shutil

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC_DIR = os.path.join(ROOT_DIR, "step2_gem5_model", "src")
GEM5_TAGS_DIR = os.path.join(ROOT_DIR, "gem5", "src", "mem", "cache", "tags")

SIMOBJECT_DEF = """

class WayShutdownSetAssoc(BaseSetAssoc):
    type = "WayShutdownSetAssoc"
    cxx_header = "mem/cache/tags/way_shutdown_tags.hh"
    cxx_class = "gem5::WayShutdownSetAssoc"

    policy_mode = Param.Int(
        3,
        "Way-Shutdown policy (0=static, 1=selective_ways, 2=way_util, 3=atd_dirty_aware)",
    )
    initial_active_ways = Param.Unsigned(
        16, "Initial number of active ways in Shared L2 (1..16)"
    )
    min_active_ways = Param.Unsigned(
        2, "Minimum active ways preserved during Way-Shutdown"
    )
    epoch_accesses = Param.Unsigned(
        2048, "Number of L2 accesses per Way-Shutdown evaluation epoch"
    )
    wakeup_latency = Param.Cycles(
        6, "SRAM power-gate wakeup latency in cycles when enabling a way"
    )
"""


def main():
    for fname in ("way_shutdown_tags.hh", "way_shutdown_tags.cc"):
        src = os.path.join(SRC_DIR, fname)
        dst = os.path.join(GEM5_TAGS_DIR, fname)
        shutil.copy2(src, dst)
        print(f"[PATCH] Copied {src} -> {dst}")

    tags_py = os.path.join(GEM5_TAGS_DIR, "Tags.py")
    with open(tags_py, "r", encoding="utf-8") as f:
        content = f.read()
    if "class WayShutdownSetAssoc" not in content:
        with open(tags_py, "a", encoding="utf-8") as f:
            f.write(SIMOBJECT_DEF)
        print(f"[PATCH] Registered WayShutdownSetAssoc in {tags_py}")
    else:
        print(f"[PATCH] WayShutdownSetAssoc already present in {tags_py}")

    sconscript = os.path.join(GEM5_TAGS_DIR, "SConscript")
    with open(sconscript, "r", encoding="utf-8") as f:
        sc = f.read()
    if '"WayShutdownSetAssoc"' not in sc:
        sc = sc.replace('"BaseSetAssoc",', '"BaseSetAssoc",\n        "WayShutdownSetAssoc",')
    if 'Source("way_shutdown_tags.cc")' not in sc:
        sc = sc.replace('Source("base_set_assoc.cc")', 'Source("base_set_assoc.cc")\nSource("way_shutdown_tags.cc")')
    with open(sconscript, "w", encoding="utf-8") as f:
        f.write(sc)
    print(f"[PATCH] Updated {sconscript}")


if __name__ == "__main__":
    main()
