// Copyright 2026 Gem5xCVA6 Project
// Shared L2 Cache Geometry & Timing Parameters (512 KiB, 16-Way, 64B Line, Write-Back)

package cva6_l2_pkg;

    localparam int unsigned NUM_CORES     = 4;
    localparam int unsigned L2_WAYS       = 16;
    localparam int unsigned L2_SETS       = 512;
    localparam int unsigned L2_SET_W      = 9;   // log2(512)
    localparam int unsigned LINE_OFFSET_W = 6;   // 64B cache line

    // Timing latencies (in cycles @ 1 GHz)
    localparam int unsigned L2_HIT_LAT    = 4;
    localparam int unsigned DRAM_MISS_LAT = 28;
    localparam int unsigned DRAM_WB_LAT   = 12;

endpackage
