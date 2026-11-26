// Copyright 2026 Gem5xCVA6 Project
// Synthesizable SystemVerilog RTL: 512 KiB, 16-Way, 64B-Line, Write-Back Shared L2 Cache
// Integrated into OpenHW CVA6 4-Core SoC with O(1) Dirty Counters & Background Dirty-Way Flush Engine

module cva6_shared_l2_16way_ws
    import cva6_l2_pkg::*;
(
    input  logic                        clk_i,
    input  logic                        rst_ni,

    // Way-Enable, Power-Gating & Wakeup Interface from l2_way_shutdown_ctrl
    input  logic [L2_WAYS-1:0]          way_en_i,
    input  logic [L2_WAYS-1:0]          way_sd_i,
    input  logic                        wakeup_stall_i,

    // Dirty-Way Flush Handshake
    input  logic                        flush_req_i,
    input  logic [3:0]                  flush_way_i,
    output logic                        flush_done_o,
    output logic [9:0]                  way_dirty_cnt_o          [L2_WAYS],

    // Request Interface from AXI4 L2 Wrapper
    input  logic                        req_valid_i,
    input  logic [1:0]                  req_core_id_i,
    input  logic                        req_is_write_i,
    input  logic [63:0]                 req_addr_i,
    output logic                        resp_valid_o,
    output logic                        resp_is_hit_o,
    output logic [5:0]                  resp_latency_o,

    // Hardware Performance & Power Counters
    output logic [63:0]                 cnt_l2_accesses_o,
    output logic [63:0]                 cnt_l2_hits_o,
    output logic [63:0]                 cnt_l2_misses_o,
    output logic [63:0]                 cnt_l2_read_acc_o,
    output logic [63:0]                 cnt_l2_write_acc_o,
    output logic [63:0]                 cnt_l2_writebacks_o,
    output logic [63:0]                 cnt_l2_shutdown_flushes_o,
    output logic [63:0]                 cnt_l2_tag_lookups_o
);

    logic              valid_arr [L2_SETS][L2_WAYS];
    logic              dirty_arr [L2_SETS][L2_WAYS];
    logic [48:0]       tag_arr   [L2_SETS][L2_WAYS];
    logic [3:0]        rr_ptr    [L2_SETS];

    logic [5:0]        flush_chunk_q;
    logic              flush_active_q;
    logic [3:0]        flush_way_q;
    logic [4:0]        chunk_dirty_cnt;

    wire [L2_SET_W-1:0] set_idx = req_addr_i[LINE_OFFSET_W + L2_SET_W - 1 : LINE_OFFSET_W];
    wire [48:0]         req_tag = req_addr_i[63 : LINE_OFFSET_W + L2_SET_W];

    logic       hit_found;
    logic [3:0] hit_way;
    logic       free_found;
    logic [3:0] free_way;
    logic [3:0] victim_way;
    logic [4:0] active_way_count;
    logic [3:0] cand_way;
    logic       victim_found;

    always_comb begin
        hit_found        = 1'b0;
        hit_way          = 4'd0;
        free_found       = 1'b0;
        free_way         = 4'd0;
        active_way_count = 5'd0;
        cand_way         = 4'd0;
        victim_found     = 1'b0;

        for (int w = 0; w < L2_WAYS; w++) begin
            if (way_en_i[w]) begin
                active_way_count = active_way_count + 5'd1;
                if (valid_arr[set_idx][w] && (tag_arr[set_idx][w] == req_tag) && !hit_found) begin
                    hit_found = 1'b1;
                    hit_way   = w[3:0];
                end
                if (!valid_arr[set_idx][w] && !free_found) begin
                    free_found = 1'b1;
                    free_way   = w[3:0];
                end
            end
        end

        if (free_found) begin
            victim_way = free_way;
        end else begin
            victim_way = 4'd0;
            for (int k = 0; k < L2_WAYS; k++) begin
                cand_way = rr_ptr[set_idx] + k[3:0];
                if (!victim_found && way_en_i[cand_way]) begin
                    victim_way   = cand_way;
                    victim_found = 1'b1;
                end
            end
        end

        chunk_dirty_cnt = 5'd0;
        if (flush_active_q) begin
            for (int j = 0; j < 16; j++) begin
                if (valid_arr[{flush_chunk_q[4:0], j[3:0]}][flush_way_q] &&
                    dirty_arr[{flush_chunk_q[4:0], j[3:0]}][flush_way_q]) begin
                    chunk_dirty_cnt = chunk_dirty_cnt + 5'd1;
                end
            end
        end
    end

    always_ff @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            resp_valid_o              <= 1'b0;
            resp_is_hit_o             <= 1'b0;
            resp_latency_o            <= 6'd0;
            flush_done_o              <= 1'b0;
            flush_active_q            <= 1'b0;
            flush_chunk_q             <= 6'd0;
            flush_way_q               <= 4'd0;

            cnt_l2_accesses_o         <= 64'd0;
            cnt_l2_hits_o             <= 64'd0;
            cnt_l2_misses_o           <= 64'd0;
            cnt_l2_read_acc_o         <= 64'd0;
            cnt_l2_write_acc_o        <= 64'd0;
            cnt_l2_writebacks_o       <= 64'd0;
            cnt_l2_shutdown_flushes_o <= 64'd0;
            cnt_l2_tag_lookups_o      <= 64'd0;

            for (int w = 0; w < L2_WAYS; w++) begin
                way_dirty_cnt_o[w] <= 10'd0;
            end
            for (int s = 0; s < L2_SETS; s++) begin
                rr_ptr[s] <= 4'd0;
                for (int w = 0; w < L2_WAYS; w++) begin
                    valid_arr[s][w] <= 1'b0;
                    dirty_arr[s][w] <= 1'b0;
                    tag_arr[s][w]   <= 49'd0;
                end
            end
        end else begin
            resp_valid_o <= 1'b0;
            flush_done_o <= 1'b0;

            // 1. Background Dirty-Way Flush Scanner (16 sets/cycle = 32 cycles/way)
            if (!flush_active_q && flush_req_i && !flush_done_o) begin
                flush_active_q <= 1'b1;
                flush_way_q    <= flush_way_i;
                flush_chunk_q  <= 6'd0;
            end else if (flush_active_q) begin
                for (int j = 0; j < 16; j++) begin
                    valid_arr[{flush_chunk_q[4:0], j[3:0]}][flush_way_q] <= 1'b0;
                    dirty_arr[{flush_chunk_q[4:0], j[3:0]}][flush_way_q] <= 1'b0;
                end
                cnt_l2_shutdown_flushes_o <= cnt_l2_shutdown_flushes_o + {59'd0, chunk_dirty_cnt};
                if (way_dirty_cnt_o[flush_way_q] >= {5'd0, chunk_dirty_cnt}) begin
                    way_dirty_cnt_o[flush_way_q] <= way_dirty_cnt_o[flush_way_q] - {5'd0, chunk_dirty_cnt};
                end else begin
                    way_dirty_cnt_o[flush_way_q] <= 10'd0;
                end

                if (flush_chunk_q == 6'd31) begin
                    flush_active_q               <= 1'b0;
                    flush_done_o                 <= 1'b1;
                    way_dirty_cnt_o[flush_way_q] <= 10'd0;
                end else begin
                    flush_chunk_q <= flush_chunk_q + 6'd1;
                end
            end

            // 2. Normal L2 Access Handling
            if (req_valid_i) begin
                resp_valid_o         <= 1'b1;
                resp_is_hit_o        <= hit_found;
                cnt_l2_accesses_o    <= cnt_l2_accesses_o + 64'd1;
                cnt_l2_tag_lookups_o <= cnt_l2_tag_lookups_o + {59'd0, active_way_count};

                if (req_is_write_i) begin
                    cnt_l2_write_acc_o <= cnt_l2_write_acc_o + 64'd1;
                end else begin
                    cnt_l2_read_acc_o  <= cnt_l2_read_acc_o + 64'd1;
                end

                if (hit_found) begin
                    cnt_l2_hits_o  <= cnt_l2_hits_o + 64'd1;
                    resp_latency_o <= 6'(L2_HIT_LAT) + (wakeup_stall_i ? 6'd6 : 6'd0);
                    if (req_is_write_i && !dirty_arr[set_idx][hit_way]) begin
                        dirty_arr[set_idx][hit_way] <= 1'b1;
                        way_dirty_cnt_o[hit_way]    <= way_dirty_cnt_o[hit_way] + 10'd1;
                    end
                end else begin
                    cnt_l2_misses_o <= cnt_l2_misses_o + 64'd1;
                    if (valid_arr[set_idx][victim_way] && dirty_arr[set_idx][victim_way]) begin
                        cnt_l2_writebacks_o <= cnt_l2_writebacks_o + 64'd1;
                        resp_latency_o      <= 6'(L2_HIT_LAT + DRAM_MISS_LAT + DRAM_WB_LAT)
                                             + (wakeup_stall_i ? 6'd6 : 6'd0);
                        if (!req_is_write_i && (way_dirty_cnt_o[victim_way] > 10'd0)) begin
                            way_dirty_cnt_o[victim_way] <= way_dirty_cnt_o[victim_way] - 10'd1;
                        end
                    end else begin
                        resp_latency_o <= 6'(L2_HIT_LAT + DRAM_MISS_LAT)
                                        + (wakeup_stall_i ? 6'd6 : 6'd0);
                        if (req_is_write_i) begin
                            way_dirty_cnt_o[victim_way] <= way_dirty_cnt_o[victim_way] + 10'd1;
                        end
                    end
                    valid_arr[set_idx][victim_way] <= 1'b1;
                    tag_arr[set_idx][victim_way]   <= req_tag;
                    dirty_arr[set_idx][victim_way] <= req_is_write_i;
                    rr_ptr[set_idx]                <= victim_way + 4'd1;
                end
            end
        end
    end

endmodule
