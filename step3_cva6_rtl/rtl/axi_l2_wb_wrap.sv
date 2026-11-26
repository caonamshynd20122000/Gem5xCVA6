// Copyright 2026 Gem5xCVA6 Project
// AXI4 Wrapper around 512 KiB 16-Way Write-Back Shared L2 Cache + atd_dirty_aware Way-Shutdown Controller
// Connects directly between axi_xbar (master[DRAM]) and dram_delayed -> i_axi2mem in ariane_testharness.sv.

module axi_l2_wb_wrap
    import cva6_l2_pkg::*;
#(
    parameter int unsigned AXI_ID_WIDTH   = 8,
    parameter int unsigned AXI_ADDR_WIDTH = 64,
    parameter int unsigned AXI_DATA_WIDTH = 64,
    parameter int unsigned AXI_USER_WIDTH = 64
) (
    input  logic                        clk_i,
    input  logic                        rst_ni,
    input  logic                        ws_enable_i,

    AXI_BUS.Slave                       slv,
    AXI_BUS.Master                      mst,

    output logic [L2_WAYS-1:0]          way_en_o,
    output logic [L2_WAYS-1:0]          way_sd_o,
    output logic [63:0]                 cnt_l2_accesses_o,
    output logic [63:0]                 cnt_l2_hits_o,
    output logic [63:0]                 cnt_l2_misses_o,
    output logic [63:0]                 cnt_l2_read_acc_o,
    output logic [63:0]                 cnt_l2_write_acc_o,
    output logic [63:0]                 cnt_l2_writebacks_o,
    output logic [63:0]                 cnt_l2_shutdown_flushes_o,
    output logic [63:0]                 cnt_l2_tag_lookups_o,
    output logic [63:0]                 cnt_ws_epochs_o,
    output logic [63:0]                 cnt_ws_shutdowns_o,
    output logic [63:0]                 cnt_ws_wakeups_o,
    output logic [63:0]                 cnt_ws_active_way_cycles_o
);

    logic        ar_fire;
    logic        aw_fire;
    logic        l2_req_valid;
    logic        l2_req_is_write;
    logic [63:0] l2_req_addr;
    logic [1:0]  l2_req_core_id;

    logic        pend_aw_q;
    logic [63:0] pend_aw_addr_q;
    logic [1:0]  pend_aw_cid_q;

    logic [5:0]  r_stall_cnt_q;
    logic [5:0]  b_stall_cnt_q;
    logic        last_req_wr_q;

    logic        l2_resp_valid;
    logic        l2_resp_hit;
    logic [5:0]  l2_resp_lat;

    // Way-Shutdown Controller <-> Shared L2 Wires
    logic [L2_WAYS-1:0] ws_way_en;
    logic [L2_WAYS-1:0] ws_way_sd;
    logic               ws_wakeup_stall;
    logic               ws_flush_req;
    logic [3:0]         ws_flush_way;
    logic               ws_flush_done;
    logic [9:0]         l2_way_dirty_cnt [L2_WAYS];

    assign way_en_o = ws_way_en;
    assign way_sd_o = ws_way_sd;
    assign ar_fire  = slv.ar_valid && slv.ar_ready;
    assign aw_fire  = slv.aw_valid && slv.aw_ready;

    // Forward AW, W, AR channels
    assign mst.aw_id     = slv.aw_id;
    assign mst.aw_addr   = slv.aw_addr;
    assign mst.aw_len    = slv.aw_len;
    assign mst.aw_size   = slv.aw_size;
    assign mst.aw_burst  = slv.aw_burst;
    assign mst.aw_lock   = slv.aw_lock;
    assign mst.aw_cache  = slv.aw_cache;
    assign mst.aw_prot   = slv.aw_prot;
    assign mst.aw_qos    = slv.aw_qos;
    assign mst.aw_region = slv.aw_region;
    assign mst.aw_atop   = slv.aw_atop;
    assign mst.aw_user   = slv.aw_user;
    assign mst.aw_valid  = slv.aw_valid;
    assign slv.aw_ready  = mst.aw_ready;

    assign mst.w_data    = slv.w_data;
    assign mst.w_strb    = slv.w_strb;
    assign mst.w_last    = slv.w_last;
    assign mst.w_user    = slv.w_user;
    assign mst.w_valid   = slv.w_valid;
    assign slv.w_ready   = mst.w_ready;

    assign mst.ar_id     = slv.ar_id;
    assign mst.ar_addr   = slv.ar_addr;
    assign mst.ar_len    = slv.ar_len;
    assign mst.ar_size   = slv.ar_size;
    assign mst.ar_burst  = slv.ar_burst;
    assign mst.ar_lock   = slv.ar_lock;
    assign mst.ar_cache  = slv.ar_cache;
    assign mst.ar_prot   = slv.ar_prot;
    assign mst.ar_qos    = slv.ar_qos;
    assign mst.ar_region = slv.ar_region;
    assign mst.ar_user   = slv.ar_user;
    assign mst.ar_valid  = slv.ar_valid;
    assign slv.ar_ready  = mst.ar_ready;

    // Gate R and B channels by L2 hit/miss/WB/wakeup latency countdown
    assign slv.r_id      = mst.r_id;
    assign slv.r_data    = mst.r_data;
    assign slv.r_resp    = mst.r_resp;
    assign slv.r_last    = mst.r_last;
    assign slv.r_user    = mst.r_user;
    assign slv.r_valid   = mst.r_valid && (r_stall_cnt_q == 6'd0);
    assign mst.r_ready   = slv.r_ready && (r_stall_cnt_q == 6'd0);

    assign slv.b_id      = mst.b_id;
    assign slv.b_resp    = mst.b_resp;
    assign slv.b_user    = mst.b_user;
    assign slv.b_valid   = mst.b_valid && (b_stall_cnt_q == 6'd0);
    assign mst.b_ready   = slv.b_ready && (b_stall_cnt_q == 6'd0);

    always_comb begin
        l2_req_valid    = 1'b0;
        l2_req_is_write = 1'b0;
        l2_req_addr     = 64'd0;
        l2_req_core_id  = 2'd0;

        if (ar_fire) begin
            l2_req_valid    = 1'b1;
            l2_req_is_write = 1'b0;
            l2_req_addr     = slv.ar_addr;
            l2_req_core_id  = slv.ar_id[AXI_ID_WIDTH-1 -: 2];
        end else if (aw_fire) begin
            l2_req_valid    = 1'b1;
            l2_req_is_write = 1'b1;
            l2_req_addr     = slv.aw_addr;
            l2_req_core_id  = slv.aw_id[AXI_ID_WIDTH-1 -: 2];
        end else if (pend_aw_q) begin
            l2_req_valid    = 1'b1;
            l2_req_is_write = 1'b1;
            l2_req_addr     = pend_aw_addr_q;
            l2_req_core_id  = pend_aw_cid_q;
        end
    end

    l2_way_shutdown_ctrl #(
        .EPOCH_ACCESSES     ( 2048 ),
        .MIN_ACTIVE_WAYS    ( 2    ),
        .WAKEUP_CYCLES      ( 6    ),
        .DIRTY_FLUSH_THRESH ( 96   ),
        .ATD_NUM_SETS       ( 16   )
    ) i_l2_ws_ctrl (
        .clk_i                  ( clk_i                      ),
        .rst_ni                 ( rst_ni                     ),
        .ws_enable_i            ( ws_enable_i                ),
        .l2_req_valid_i         ( l2_req_valid               ),
        .l2_req_is_write_i      ( l2_req_is_write            ),
        .l2_req_addr_i          ( l2_req_addr                ),
        .l2_resp_valid_i        ( l2_resp_valid              ),
        .l2_resp_is_hit_i       ( l2_resp_hit                ),
        .way_dirty_cnt_i        ( l2_way_dirty_cnt           ),
        .flush_req_o            ( ws_flush_req               ),
        .flush_way_o            ( ws_flush_way               ),
        .flush_done_i           ( ws_flush_done              ),
        .way_en_o               ( ws_way_en                  ),
        .way_sd_o               ( ws_way_sd                  ),
        .wakeup_stall_o         ( ws_wakeup_stall            ),
        .cnt_epochs_o           ( cnt_ws_epochs_o            ),
        .cnt_shutdowns_o        ( cnt_ws_shutdowns_o         ),
        .cnt_wakeups_o          ( cnt_ws_wakeups_o           ),
        .cnt_active_way_cycles_o( cnt_ws_active_way_cycles_o )
    );

    cva6_shared_l2_16way_ws i_l2_core (
        .clk_i                    ( clk_i                     ),
        .rst_ni                   ( rst_ni                    ),
        .way_en_i                 ( ws_way_en                 ),
        .way_sd_i                 ( ws_way_sd                 ),
        .wakeup_stall_i           ( ws_wakeup_stall           ),
        .flush_req_i              ( ws_flush_req              ),
        .flush_way_i              ( ws_flush_way              ),
        .flush_done_o             ( ws_flush_done             ),
        .way_dirty_cnt_o          ( l2_way_dirty_cnt          ),
        .req_valid_i              ( l2_req_valid              ),
        .req_core_id_i            ( l2_req_core_id            ),
        .req_is_write_i           ( l2_req_is_write           ),
        .req_addr_i               ( l2_req_addr               ),
        .resp_valid_o             ( l2_resp_valid             ),
        .resp_is_hit_o            ( l2_resp_hit               ),
        .resp_latency_o           ( l2_resp_lat               ),
        .cnt_l2_accesses_o        ( cnt_l2_accesses_o         ),
        .cnt_l2_hits_o            ( cnt_l2_hits_o             ),
        .cnt_l2_misses_o          ( cnt_l2_misses_o           ),
        .cnt_l2_read_acc_o        ( cnt_l2_read_acc_o         ),
        .cnt_l2_write_acc_o       ( cnt_l2_write_acc_o        ),
        .cnt_l2_writebacks_o      ( cnt_l2_writebacks_o       ),
        .cnt_l2_shutdown_flushes_o( cnt_l2_shutdown_flushes_o ),
        .cnt_l2_tag_lookups_o     ( cnt_l2_tag_lookups_o      )
    );

    always_ff @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            pend_aw_q      <= 1'b0;
            pend_aw_addr_q <= 64'd0;
            pend_aw_cid_q  <= 2'd0;
            r_stall_cnt_q  <= 6'd0;
            b_stall_cnt_q  <= 6'd0;
            last_req_wr_q  <= 1'b0;
        end else begin
            if (ar_fire && aw_fire) begin
                pend_aw_q      <= 1'b1;
                pend_aw_addr_q <= slv.aw_addr;
                pend_aw_cid_q  <= slv.aw_id[AXI_ID_WIDTH-1 -: 2];
            end else if (!ar_fire && !aw_fire && pend_aw_q) begin
                pend_aw_q <= 1'b0;
            end

            if (l2_req_valid) begin
                last_req_wr_q <= l2_req_is_write;
            end

            if (l2_resp_valid && !last_req_wr_q) begin
                r_stall_cnt_q <= l2_resp_lat;
            end else if (r_stall_cnt_q > 6'd0) begin
                r_stall_cnt_q <= r_stall_cnt_q - 6'd1;
            end

            if (l2_resp_valid && last_req_wr_q) begin
                b_stall_cnt_q <= l2_resp_lat;
            end else if (b_stall_cnt_q > 6'd0) begin
                b_stall_cnt_q <= b_stall_cnt_q - 6'd1;
            end
        end
    end

endmodule
