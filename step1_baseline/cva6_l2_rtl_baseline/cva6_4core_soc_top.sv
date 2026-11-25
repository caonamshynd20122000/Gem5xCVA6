// Copyright 2026 Gem 5 x CVA6 Project
// Top-Level SystemVerilog RTL: 4-Core CVA6 Cluster + L2XBar + 512 KiB 16-Way Write-Back Shared L2 Cache

module cva6_4core_soc_top
    import cva6_4core_l2_pkg::*;
(
    input  logic                 clk_i,
    input  logic                 rst_ni,
    input  logic [L2_WAYS-1:0]   l2_way_en_i,

    // Status & HTIF tohost outputs
    output logic [63:0]          tohost_o,
    output logic [63:0]          tohost_checksum_o,
    output logic [63:0]          soc_cycles_o,

    // Per-Core Counters
    output logic [63:0]          core_cycles_o      [NUM_CORES],
    output logic [63:0]          core_instret_o     [NUM_CORES],
    output logic [63:0]          core_l1i_acc_o     [NUM_CORES],
    output logic [63:0]          core_l1i_miss_o    [NUM_CORES],
    output logic [63:0]          core_l1d_acc_o     [NUM_CORES],
    output logic [63:0]          core_l1d_hits_o    [NUM_CORES],
    output logic [63:0]          core_l1d_miss_o    [NUM_CORES],

    // Shared L2 Cache Counters
    output logic [63:0]          l2_accesses_o,
    output logic [63:0]          l2_hits_o,
    output logic [63:0]          l2_misses_o,
    output logic [63:0]          l2_read_acc_o,
    output logic [63:0]          l2_write_acc_o,
    output logic [63:0]          l2_writebacks_o,
    output logic [63:0]          l2_tag_lookups_o,
    output logic [63:0]          l2_way_hits_o      [L2_WAYS],
    output logic [63:0]          l2_core_acc_o      [NUM_CORES],
    output logic [63:0]          l2_core_hits_o     [NUM_CORES],
    output logic [63:0]          l2_core_misses_o   [NUM_CORES]
);

    // Backing Main Memory Array (32 MiB = 4M x 64-bit words starting at 0x8000_0000)
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

    // Instantiate 4x CVA6 Core Tiles (Core 0 .. Core 3)
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
    always_comb begin
        for (int i = 0; i < NUM_CORES; i++) begin
            automatic logic [31:0] i_idx = (core_imem_addr[i][31:0] - DRAM_BASE) >> 3;
            automatic logic [63:0] i_dw  = (i_idx < DRAM_WORDS) ? dram_mem[i_idx] : 64'd0;
            automatic logic [31:0] d_idx = (core_dmem_addr[i][31:0] - DRAM_BASE) >> 3;
            core_imem_rdata[i] = core_imem_addr[i][2] ? i_dw[63:32] : i_dw[31:0];
            core_dmem_rdata[i] = (d_idx < DRAM_WORDS) ? dram_mem[d_idx] : 64'd0;
        end
    end

    // 4-Port Round-Robin L1-to-L2 Coherent Crossbar (L2XBar)
    logic [1:0]  arb_rr_q;
    logic [1:0]  arb_grant_id_q;
    logic        arb_req_valid;
    logic [1:0]  arb_req_core;
    logic        arb_req_write;
    logic [63:0] arb_req_addr;

    logic        l2_resp_valid;
    logic        l2_resp_hit;
    logic [5:0]  l2_resp_latency;

    always_comb begin
        arb_req_valid = 1'b0;
        arb_req_core  = 2'd0;
        arb_req_write = 1'b0;
        arb_req_addr  = 64'd0;

        for (int k = 0; k < NUM_CORES; k++) begin
            automatic logic [1:0] cid = arb_rr_q + k[1:0];
            if (core_l2_req_val[cid]) begin
                arb_req_valid = 1'b1;
                arb_req_core  = cid;
                arb_req_write = core_l2_req_wr[cid];
                arb_req_addr  = core_l2_req_addr[cid];
                break;
            end
        end

        for (int i = 0; i < NUM_CORES; i++) begin
            core_l2_resp_val[i] = l2_resp_valid && (arb_grant_id_q == i[1:0]);
            core_l2_resp_lat[i] = l2_resp_latency;
        end
    end

    // Instantiate Target 512 KiB, 16-Way, Write-Back Shared L2 Cache
    cva6_shared_l2_16way i_shared_l2 (
        .clk_i               (clk_i),
        .rst_ni              (rst_ni),
        .way_en_i            (l2_way_en_i),
        .req_valid_i         (arb_req_valid),
        .req_core_id_i       (arb_req_core),
        .req_is_write_i      (arb_req_write),
        .req_addr_i          (arb_req_addr),
        .resp_valid_o        (l2_resp_valid),
        .resp_is_hit_o       (l2_resp_hit),
        .resp_latency_o      (l2_resp_latency),
        .l1_inval_valid_o    (l1_inval_valid),
        .l1_inval_src_core_o (l1_inval_src_core),
        .l1_inval_addr_o     (l1_inval_addr),
        .cnt_l2_accesses_o   (l2_accesses_o),
        .cnt_l2_hits_o       (l2_hits_o),
        .cnt_l2_misses_o     (l2_misses_o),
        .cnt_l2_read_acc_o   (l2_read_acc_o),
        .cnt_l2_write_acc_o  (l2_write_acc_o),
        .cnt_l2_writebacks_o (l2_writebacks_o),
        .cnt_l2_tag_lookups_o(l2_tag_lookups_o),
        .cnt_l2_way_hits_o   (l2_way_hits_o),
        .cnt_l2_core_acc_o   (l2_core_acc_o),
        .cnt_l2_core_hits_o  (l2_core_hits_o),
        .cnt_l2_core_misses_o(l2_core_misses_o)
    );

    // Sequential DRAM Store Update, Crossbar Round-Robin Pointer, and HTIF tohost Monitor
    // (.tohost is placed at 0x8000_1000 by common/link_4core.ld:
    //  0x8000_1000 = tohost, 0x8000_1040 = fromhost, 0x8000_1080 = tohost_checksum)
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
                    automatic logic [31:0] w_idx = (core_dmem_addr[i][31:0] - DRAM_BASE) >> 3;
                    if (w_idx < DRAM_WORDS) begin
                        for (int b = 0; b < 8; b++) begin
                            if (core_dmem_wstrb[i][b]) begin
                                dram_mem[w_idx][b*8 +: 8] <= core_dmem_wdata[i][b*8 +: 8];
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
