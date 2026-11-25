#!/usr/bin/env python3
"""
Gem 5 x CVA6 — Step 2 gem5 Configuration:
4-Core CVA6 Cluster (4x RiscvMinorCPU + Private L1I 16KB 4w + Private L1D 32KB 8w)
+ L2XBar (128-bit Coherent Crossbar)
+ Shared L2 Cache (512 KiB, 16-Way, 64B Line, Write-Back) with WayShutdownSetAssoc
"""

import argparse
import os
import sys

import m5
from m5.objects import (
    AddrRange,
    BranchPredictor,
    Cache,
    L2XBar,
    LocalBP,
    LRURP,
    MinorDefaultFloatSimdFU,
    MinorDefaultIntDivFU,
    MinorDefaultIntFU,
    MinorDefaultIntMulFU,
    MinorDefaultMemFU,
    MinorDefaultMiscFU,
    MinorDefaultPredFU,
    MinorFUPool,
    Process,
    RandomRP,
    ReturnAddrStack,
    RiscvMinorCPU,
    Root,
    SEWorkload,
    SimpleBTB,
    SimpleMemory,
    SrcClockDomain,
    System,
    SystemXBar,
    TreePLRURP,
    VoltageDomain,
    WayShutdownSetAssoc,
)

POLICY_MAP = {
    "static": 0,
    "selective_ways": 1,
    "way_util": 2,
    "atd_dirty_aware": 3,
}


class CVA6FUPool(MinorFUPool):
    funcUnits = [
        MinorDefaultIntFU(opLat=1, issueLat=1),
        MinorDefaultIntMulFU(opLat=2, issueLat=1),
        MinorDefaultIntDivFU(opLat=12, issueLat=12),
        MinorDefaultFloatSimdFU(opLat=4, issueLat=1),
        MinorDefaultPredFU(),
        MinorDefaultMemFU(opLat=1, issueLat=1),
        MinorDefaultMiscFU(),
    ]


class CVA6L1ICache(Cache):
    size = "16kB"
    assoc = 4
    tag_latency = 1
    data_latency = 1
    response_latency = 1
    mshrs = 2
    tgts_per_mshr = 4
    is_read_only = True


class CVA6L1DCache(Cache):
    size = "32kB"
    assoc = 8
    tag_latency = 1
    data_latency = 1
    response_latency = 1
    mshrs = 8
    tgts_per_mshr = 4
    write_buffers = 8


class CVA6SharedL2Cache(Cache):
    size = "512kB"
    assoc = 16
    tag_latency = 1
    data_latency = 2
    response_latency = 1
    mshrs = 16
    tgts_per_mshr = 8
    write_buffers = 16
    writeback_clean = False


def build_4core_cva6_l2_system(args):
    system = System()
    system.clk_domain = SrcClockDomain(clock="1GHz", voltage_domain=VoltageDomain())
    system.mem_mode = "timing"
    system.mem_ranges = [AddrRange("512MB")]
    system.cache_line_size = 64

    # 4x OpenHW CVA6 (fpga_linux_cv64a6) In-Order Cores (Core 0 .. Core 3)
    system.cpu = [RiscvMinorCPU(cpu_id=i) for i in range(4)]
    # 64-bit (8B/cycle) AXI4 Crossbar matching OpenHW CVA6 axi_xbar (AxiDataWidth = 64)
    system.l2bus = L2XBar(width=8)

    for i, cpu in enumerate(system.cpu):
        cpu.decodeInputWidth = 1
        cpu.executeInputWidth = 1
        cpu.executeIssueLimit = 1
        cpu.executeCommitLimit = 2
        cpu.executeInputBufferSize = 8
        cpu.executeLSQStoreBufferSize = 7
        cpu.executeLSQTransfersQueueSize = 8
        cpu.mmu.itb.size = 16
        cpu.mmu.dtb.size = 16
        cpu.executeFuncUnits = CVA6FUPool()
        cpu.branchPred = BranchPredictor(
            conditionalBranchPred=LocalBP(localPredictorSize=128),
            btb=SimpleBTB(numEntries=32),
            ras=ReturnAddrStack(numEntries=2),
        )
        cpu.icache = CVA6L1ICache()
        cpu.dcache = CVA6L1DCache()
        cpu.icache.cpu_side = cpu.icache_port
        cpu.dcache.cpu_side = cpu.dcache_port
        cpu.icache.mem_side = system.l2bus.cpu_side_ports
        cpu.dcache.mem_side = system.l2bus.cpu_side_ports
        cpu.createInterruptController()

    # Shared 512 KiB, 16-Way, Write-Back L2 Cache with WayShutdownSetAssoc
    system.l2cache = CVA6SharedL2Cache()
    system.l2cache.replacement_policy = LRURP()
    system.l2cache.tags = WayShutdownSetAssoc(
        policy_mode=POLICY_MAP[args.policy],
        initial_active_ways=args.initial_ways,
        min_active_ways=args.min_ways,
        epoch_accesses=args.epoch_accesses,
        wakeup_latency=args.wakeup_lat,
    )
    system.l2cache.cpu_side = system.l2bus.mem_side_ports

    system.membus = SystemXBar(width=8)
    system.l2cache.mem_side = system.membus.cpu_side_ports
    system.system_port = system.membus.cpu_side_ports

    system.mem_ctrl = SimpleMemory(
        range=system.mem_ranges[0],
        latency="28ns",
        bandwidth="8GB/s",
    )
    system.mem_ctrl.port = system.membus.mem_side_ports

    binary = os.path.abspath(args.cmd)
    system.workload = SEWorkload.init_compatible(binary)
    proc = Process(pid=100)
    proc.cmd = [binary]
    for cpu in system.cpu:
        cpu.workload = proc
        cpu.createThreads()

    return system


def main():
    parser = argparse.ArgumentParser(description="gem5 4-Core CVA6 + 16-Way Shared L2 Way-Shutdown Model")
    parser.add_argument("--cmd", required=True, help="Path to RISC-V benchmark ELF")
    parser.add_argument("--policy", choices=list(POLICY_MAP.keys()), default="atd_dirty_aware",
                        help="L2 Way-Shutdown policy mode")
    parser.add_argument("--initial-ways", type=int, default=16, help="Initial active L2 ways (1..16)")
    parser.add_argument("--min-ways", type=int, default=2, help="Minimum active L2 ways (1..16)")
    parser.add_argument("--epoch-accesses", type=int, default=2048, help="L2 accesses per epoch")
    parser.add_argument("--wakeup-lat", type=int, default=6, help="Way wakeup latency in cycles")
    args = parser.parse_args()

    system = build_4core_cva6_l2_system(args)
    root = Root(full_system=False, system=system)
    m5.instantiate()
    exit_event = m5.simulate()
    print(f"[gem5-4Core-CVA6-L2] Exited @ tick {m5.curTick()} ({exit_event.getCause()})")


if __name__ == "__m5_main__":
    main()
