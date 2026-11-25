// Copyright 2026 Gem 5 x CVA6 Project
// Package: 4-Core CVA6 Cluster + Private L1 (I$/D$) + 512 KiB 16-Way Write-Back Shared L2 Cache

package cva6_4core_l2_pkg;

    localparam int unsigned NUM_CORES       = 4;
    localparam int unsigned DRAM_BASE       = 32'h8000_0000;
    localparam int unsigned DRAM_SIZE_BYTES = 32 * 1024 * 1024; // 32 MiB simulated DRAM
    localparam int unsigned DRAM_WORDS      = DRAM_SIZE_BYTES / 8;

    // Cache line size = 64 bytes (512 bits, 6-bit byte offset)
    localparam int unsigned LINE_BYTES      = 64;
    localparam int unsigned LINE_OFFSET_W   = 6;

    // Private L1 I-Cache: 16 KiB, 4-Way, 64B Line -> 64 Sets
    localparam int unsigned L1I_WAYS        = 4;
    localparam int unsigned L1I_SETS        = 64;
    localparam int unsigned L1I_SET_W       = 6;

    // Private L1 D-Cache: 32 KiB, 8-Way, 64B Line, Write-Through -> 64 Sets
    localparam int unsigned L1D_WAYS        = 8;
    localparam int unsigned L1D_SETS        = 64;
    localparam int unsigned L1D_SET_W       = 6;

    // Target Shared L2 Cache: 512 KiB, 16-Way, 64B Line, Write-Back -> 512 Sets (32 KiB/Way)
    localparam int unsigned L2_WAYS         = 16;
    localparam int unsigned L2_SETS         = 512;
    localparam int unsigned L2_SET_W        = 9;

    // Cycle Timing Parameters (calibrated to CVA6 + CACTI 7.0 22nm)
    localparam int unsigned L1_HIT_LAT      = 1;
    localparam int unsigned L2_HIT_LAT      = 4;
    localparam int unsigned DRAM_MISS_LAT   = 28;
    localparam int unsigned DRAM_WB_LAT     = 10;

endpackage
