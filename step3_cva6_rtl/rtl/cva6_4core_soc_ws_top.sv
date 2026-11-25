// Copyright 2026 Gem5 x CVA6 Project
// Top-Level SystemVerilog RTL (Step 3):
// 4-Core CVA6 Cluster + L2XBar + 512 KiB 16-Way Write-Back Shared L2 + atd_dirty_aware Way-Shutdown Controller

module cva6_4core_soc_ws_top
    import cva6_4core_l2_pkg::*;
(
    input  logic                 clk_i,
    input  logic                 rst_ni,
    input  logic                 ws_enable_i,

    // Status & HTIF tohost outputs
    output logic [63:0]          tohost_o,
    output logic [63:0]          tohost_checksum_o,
    output logic [63:0]          soc_cycles_o,

    // Per-Core Counters
    output logic [63:0]          core_cycles_o         [NUM_CORES],
    output logic [63:0]          core_instret_o        [NUM_CORES],
    output logic [63:0]          core_l1i_acc_o        [NUM_CORES],
    output logic [63:0]          core_l1i_miss_o       [NUM_CORES],
    output logic [63:0]          core_l1d_acc_o        [NUM_CORES],
    output logic [63:0]          core_l1d_hits_o       [NUM_CORES],
    output logic [63:0]          core_l1d_miss_o       [NUM_CORES],

    // Shared L2 Cache & Way-Shutdown Counters
    output logic [L2_WAYS-1:0]   l2_way_en_o,
    output logic [L2_WAYS-1:0]   l2_way_sd_o,
    output logic [63:0]          l2_accesses_o,
    output logic [63:0]          l2_hits_o,
    output logic [63:0]          l2_misses_o,
    output logic [63:0]          l2_read_acc_o,
    output logic [63:0]          l2_write_acc_o,
    output logic [63:0]          l2_writebacks_o,
    output logic [63:0]          l2_shutdown_flushes_o,
    output logic [63:0]          l2_tag_lookups_o,
    output logic [63:0]          l2_way_hits_o         [L2_WAYS],
    output logic [63:0]          l2_core_acc_o         [NUM_CORES],
    output logic [63:0]          l2_core_hits_o        [NUM_CORES],
    output logic [63:0]          l2_core_misses_o      [NUM_CORES],
    output logic [63:0]          ws_epochs_o,
    output logic [63:0]          ws_shutdowns_o,
    output logic [63:0]          ws_wakeups_o,
    output logic [63:0]          ws_active_way_cycles_o
);

    // Backing Main Memory Array (32 MiB starting at 0x8000_0000)
    logic [63:0] dram_mem [DRAM_WORDS] /* verilator public_flat_rw */;

    // Core <-> Memory & L2XBar wires
    logic [63:0] core_imem_addr   [NUM_CORES];
    logic [31:0] core_imem_rdata  [NUM_CORES];
    logic        core_dmem_we     [NUM_CORES];
    logic [63:0] core_dmem_addr   [NUM_CORES];
    logic [63:0] core_dmem_wdata  [NUM_CORES];
    logic [7:0]  core_dmem_wstrb  [NUM_CORES];
    logic [63:0] core_dmem_rdata  [NUM_CORES];

    logic        core_l2_req_val  [NUM_CORES];
    logic        core_l2_req_wr   [NUM_CORES];
    logic [63:0] core_l2_req_addr [NUM_CORES];
    logic        core_l2_resp_val [NUM_CORES];
    logic [5:0]  core_l2_resp_lat [NUM_CORES];

    logic        l1_inval_valid;
    logic [1:0]  l1_inval_src_core;
    logic [63:0] l1_inval_addr;

    // Instantiate 4x CVA6 Core Tiles (reused verbatim from Step 1)
    genvar c;
    generate
        for (c = 0; c < NUM_CORES; c++) begin : gen_cva6_tiles
            cva6_core_tile_l1 #(
                .HART_ID(c)
            ) i_cva6_tile (
                .clk_i              (clk_i),
                .rst_ni             (rst_ni),
                .imem_addr_o        (core_imem_addr[c]),
                .imem_rdata_i       (core_imem_rdata[c]),
                .dmem_we_o          (core_dmem_we[c]),
                .dmem_addr_o        (core_dmem_addr[c]),
                .dmem_wdata_o       (core_dmem_wdata[c]),
                .dmem_wstrb_o       (core_dmem_wstrb[c]),
                .dmem_rdata_i       (core_dmem_rdata[c]),
                .l2_req_valid_o     (core_l2_req_val[c]),
                .l2_req_is_write_o  (core_l2_req_wr[c]),
                .l2_req_addr_o      (core_l2_req_addr[c]),
                .l2_resp_valid_i    (core_l2_resp_val[c]),
                .l2_resp_latency_i  (core_l2_resp_lat[c]),
                .l1_inval_valid_i   (l1_inval_valid),
                .l1_inval_src_core_i(l1_inval_src_core),
                .l1_inval_addr_i    (l1_inval_addr),
                .cnt_cycles_o       (core_cycles_o[c]),
                .cnt_instret_o      (core_instret_o[c]),
                .cnt_l1i_access_o   (core_l1i_acc_o[c]),
                .cnt_l1i_misses_o   (core_l1i_miss_o[c]),
                .cnt_l1d_access_o   (core_l1d_acc_o[c]),
                .cnt_l1d_hits_o     (core_l1d_hits_o[c]),
                .cnt_l1d_misses_o   (core_l1d_miss_o[c])
            );
        end
    endgenerate

    // Functional DRAM instruction/data read
    logic [31:0] imem_idx_tmp;
    logic [63:0] imem_dw_tmp;
    logic [31:0] dmem_idx_tmp;

    always_comb begin
        imem_idx_tmp = 32'd0;
        imem_dw_tmp  = 64'd0;
        dmem_idx_tmp = 32'd0;
        for (int i = 0; i < NUM_CORES; i++) begin
            imem_idx_tmp       = (core_imem_addr[i][31:0] - DRAM_BASE) >> 3;
            imem_dw_tmp        = (imem_idx_tmp < DRAM_WORDS) ? dram_mem[imem_idx_tmp] : 64'd0;
            dmem_idx_tmp       = (core_dmem_addr[i][31:0] - DRAM_BASE) >> 3;
            core_imem_rdata[i] = core_imem_addr[i][2] ? imem_dw_tmp[63:32] : imem_dw_tmp[31:0];
            core_dmem_rdata[i] = (dmem_idx_tmp < DRAM_WORDS) ? dram_mem[dmem_idx_tmp] : 64'd0;
        end
    end

    // 4-Port Round-Robin L1-to-L2 Coherent Crossbar (L2XBar)
    logic [1:0]  arb_rr_q;
    logic [1:0]  arb_grant_id_q;
    logic        arb_req_valid;
    logic [1:0]  arb_req_core;
    logic        arb_req_write;
    logic [63:0] arb_req_addr;
    logic [1:0]  arb_cid_tmp;

    logic        l2_resp_valid;
    logic        l2_resp_hit;
    logic [5:0]  l2_resp_latency;

    always_comb begin
        arb_req_valid = 1'b0;
        arb_req_core  = 2'd0;
        arb_req_write = 1'b0;
        arb_req_addr  = 64'd0;
        arb_cid_tmp   = 2'd0;

        for (int k = 0; k < NUM_CORES; k++) begin
            arb_cid_tmp = arb_rr_q + k[1:0];
            if (!arb_req_valid && core_l2_req_val[arb_cid_tmp]) begin
                arb_req_valid = 1'b1;
                arb_req_core  = arb_cid_tmp;
                arb_req_write = core_l2_req_wr[arb_cid_tmp];
                arb_req_addr  = core_l2_req_addr[arb_cid_tmp];
            end
        end

        for (int i = 0; i < NUM_CORES; i++) begin
            core_l2_resp_val[i] = l2_resp_valid && (arb_grant_id_q == i[1:0]);
            core_l2_resp_lat[i] = l2_resp_latency;
        end
    end

    // Way-Shutdown Controller <-> Shared L2 Wires
    logic [L2_WAYS-1:0] ws_way_en;
    logic [L2_WAYS-1:0] ws_way_sd;
    logic               ws_wakeup_stall;
    logic               ws_flush_req;
    logic [3:0]         ws_flush_way;
    logic               ws_flush_done;
    logic [9:0]         l2_way_dirty_cnt [L2_WAYS];

    assign l2_way_en_o = ws_way_en;
    assign l2_way_sd_o = ws_way_sd;

    // Instantiate atd_dirty_aware Way-Shutdown Controller
    l2_way_shutdown_ctrl #(
        .EPOCH_ACCESSES     (2048),
        .MIN_ACTIVE_WAYS    (2),
        .WAKEUP_CYCLES      (6),
        .DIRTY_FLUSH_THRESH (96),
        .ATD_NUM_SETS       (16)
    ) i_l2_ws_ctrl (
        .clk_i                  (clk_i),
        .rst_ni                 (rst_ni),
        .ws_enable_i            (ws_enable_i),
        .l2_req_valid_i         (arb_req_valid),
        .l2_req_is_write_i      (arb_req_write),
        .l2_req_addr_i          (arb_req_addr),
        .way_dirty_cnt_i        (l2_way_dirty_cnt),
        .flush_req_o            (ws_flush_req),
        .flush_way_o            (ws_flush_way),
        .flush_done_i           (ws_flush_done),
        .way_en_o               (ws_way_en),
        .way_sd_o               (ws_way_sd),
        .wakeup_stall_o         (ws_wakeup_stall),
        .cnt_epochs_o           (ws_epochs_o),
        .cnt_shutdowns_o        (ws_shutdowns_o),
        .cnt_wakeups_o          (ws_wakeups_o),
        .cnt_active_way_cycles_o(ws_active_way_cycles_o)
    );

    // Instantiate 512 KiB, 16-Way, Write-Back Shared L2 Cache with Dirty-Way Flush Engine
    cva6_shared_l2_16way_ws i_shared_l2_ws (
        .clk_i                    (clk_i),
        .rst_ni                   (rst_ni),
        .way_en_i                 (ws_way_en),
        .way_sd_i                 (ws_way_sd),
        .wakeup_stall_i           (ws_wakeup_stall),
        .flush_req_i              (ws_flush_req),
        .flush_way_i              (ws_flush_way),
        .flush_done_o             (ws_flush_done),
        .way_dirty_cnt_o          (l2_way_dirty_cnt),
        .req_valid_i              (arb_req_valid),
        .req_core_id_i            (arb_req_core),
        .req_is_write_i           (arb_req_write),
        .req_addr_i               (arb_req_addr),
        .resp_valid_o             (l2_resp_valid),
        .resp_is_hit_o            (l2_resp_hit),
        .resp_latency_o           (l2_resp_latency),
        .l1_inval_valid_o         (l1_inval_valid),
        .l1_inval_src_core_o      (l1_inval_src_core),
        .l1_inval_addr_o          (l1_inval_addr),
        .cnt_l2_accesses_o        (l2_accesses_o),
        .cnt_l2_hits_o            (l2_hits_o),
        .cnt_l2_misses_o          (l2_misses_o),
        .cnt_l2_read_acc_o        (l2_read_acc_o),
        .cnt_l2_write_acc_o       (l2_write_acc_o),
        .cnt_l2_writebacks_o      (l2_writebacks_o),
        .cnt_l2_shutdown_flushes_o(l2_shutdown_flushes_o),
        .cnt_l2_tag_lookups_o     (l2_tag_lookups_o),
        .cnt_l2_way_hits_o        (l2_way_hits_o),
        .cnt_l2_core_acc_o        (l2_core_acc_o),
        .cnt_l2_core_hits_o       (l2_core_hits_o),
        .cnt_l2_core_misses_o     (l2_core_misses_o)
    );

    // Sequential DRAM Store Update, Crossbar Round-Robin Pointer, and HTIF tohost Monitor
    always_ff @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            arb_rr_q          <= 2'd0;
            arb_grant_id_q    <= 2'd0;
            soc_cycles_o      <= 64'd0;
            tohost_o          <= 64'd0;
            tohost_checksum_o <= 64'd0;
        end else begin
            soc_cycles_o <= soc_cycles_o + 64'd1;
            if (arb_req_valid) begin
                arb_grant_id_q <= arb_req_core;
                arb_rr_q       <= arb_req_core + 2'd1;
            end

            for (int i = 0; i < NUM_CORES; i++) begin
                if (core_dmem_we[i]) begin
                    if (((core_dmem_addr[i][31:0] - DRAM_BASE) >> 3) < DRAM_WORDS) begin
                        for (int b = 0; b < 8; b++) begin
                            if (core_dmem_wstrb[i][b]) begin
                                dram_mem[(core_dmem_addr[i][31:0] - DRAM_BASE) >> 3][b*8 +: 8]
                                    <= core_dmem_wdata[i][b*8 +: 8];
                            end
                        end
                    end
                    if (core_dmem_addr[i][31:0] == 32'h8000_1000) begin
                        tohost_o          <= core_dmem_wdata[i];
                        tohost_checksum_o <= (core_dmem_wdata[i] >> 1);
                    end
                end
            end
        end
    end

endmodule
