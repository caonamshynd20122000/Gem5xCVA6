// Copyright 2026 Gem 5 x CVA6 Project
// Synthesizable SystemVerilog RTL: 512 KiB, 16-Way, 64B-Line, Write-Back Shared L2 Cache
// Supports 16-bit way_en_i[15:0] mask (16'hFFFF for Baseline, dynamic mask in Step 3)

module cva6_shared_l2_16way
    import cva6_4core_l2_pkg::*;
(
    input  logic                        clk_i,
    input  logic                        rst_ni,

    // Way-Enable & Power-Gating Interface (Baseline: way_en_i = 16'hFFFF)
    input  logic [L2_WAYS-1:0]          way_en_i,

    // Request from 4-Core L1-to-L2 Coherent Crossbar (L2XBar)
    input  logic                        req_valid_i,
    input  logic [1:0]                  req_core_id_i,
    input  logic                        req_is_write_i,
    input  logic [63:0]                 req_addr_i,
    output logic                        resp_valid_o,
    output logic                        resp_is_hit_o,
    output logic [5:0]                  resp_latency_o,

    // Broadcast L1D Coherence Invalidation on Shared Write
    output logic                        l1_inval_valid_o,
    output logic [1:0]                  l1_inval_src_core_o,
    output logic [63:0]                 l1_inval_addr_o,

    // Hardware Performance & Power Counters
    output logic [63:0]                 cnt_l2_accesses_o,
    output logic [63:0]                 cnt_l2_hits_o,
    output logic [63:0]                 cnt_l2_misses_o,
    output logic [63:0]                 cnt_l2_read_acc_o,
    output logic [63:0]                 cnt_l2_write_acc_o,
    output logic [63:0]                 cnt_l2_writebacks_o,
    output logic [63:0]                 cnt_l2_tag_lookups_o,
    output logic [63:0]                 cnt_l2_way_hits_o   [L2_WAYS],
    output logic [63:0]                 cnt_l2_core_acc_o   [NUM_CORES],
    output logic [63:0]                 cnt_l2_core_hits_o  [NUM_CORES],
    output logic [63:0]                 cnt_l2_core_misses_o[NUM_CORES]
);

    // Tag + State Directory Arrays: 512 Sets x 16 Ways
    logic              valid_arr [L2_SETS][L2_WAYS];
    logic              dirty_arr [L2_SETS][L2_WAYS];
    logic [48:0]       tag_arr   [L2_SETS][L2_WAYS];
    logic [3:0]        rr_ptr    [L2_SETS];

    // Address decomposition: [63:15] Tag (49b), [14:6] Set Index (9b = 512 sets), [5:0] Offset (6b = 64B)
    wire [L2_SET_W-1:0] set_idx = req_addr_i[LINE_OFFSET_W + L2_SET_W - 1 : LINE_OFFSET_W];
    wire [48:0]         req_tag = req_addr_i[63 : LINE_OFFSET_W + L2_SET_W];

    // Combinational Parallel Tag Lookup (Gated by way_en_i[w])
    logic               hit_found;
    logic [3:0]         hit_way;
    logic               free_found;
    logic [3:0]         free_way;
    logic [3:0]         victim_way;
    logic [4:0]         active_way_count;

    always_comb begin
        hit_found        = 1'b0;
        hit_way          = 4'd0;
        free_found       = 1'b0;
        free_way         = 4'd0;
        active_way_count = 5'd0;

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

        // Select replacement victim among enabled ways (way_en_i)
        if (free_found) begin
            victim_way = free_way;
        end else begin
            victim_way = 4'd0;
            for (int k = 0; k < L2_WAYS; k++) begin
                automatic logic [3:0] cand = rr_ptr[set_idx] + k[3:0];
                if (way_en_i[cand]) begin
                    victim_way = cand;
                    break;
                end
            end
        end
    end

    // Sequential State & Counter Update
    always_ff @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            resp_valid_o        <= 1'b0;
            resp_is_hit_o       <= 1'b0;
            resp_latency_o      <= 6'd0;
            l1_inval_valid_o    <= 1'b0;
            l1_inval_src_core_o <= 2'd0;
            l1_inval_addr_o     <= 64'd0;

            cnt_l2_accesses_o    <= 64'd0;
            cnt_l2_hits_o        <= 64'd0;
            cnt_l2_misses_o      <= 64'd0;
            cnt_l2_read_acc_o    <= 64'd0;
            cnt_l2_write_acc_o   <= 64'd0;
            cnt_l2_writebacks_o  <= 64'd0;
            cnt_l2_tag_lookups_o <= 64'd0;

            for (int w = 0; w < L2_WAYS; w++) begin
                cnt_l2_way_hits_o[w] <= 64'd0;
            end
            for (int c = 0; c < NUM_CORES; c++) begin
                cnt_l2_core_acc_o[c]    <= 64'd0;
                cnt_l2_core_hits_o[c]   <= 64'd0;
                cnt_l2_core_misses_o[c] <= 64'd0;
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
            resp_valid_o     <= 1'b0;
            l1_inval_valid_o <= 1'b0;

            if (req_valid_i) begin
                resp_valid_o         <= 1'b1;
                resp_is_hit_o        <= hit_found;
                cnt_l2_accesses_o    <= cnt_l2_accesses_o + 64'd1;
                cnt_l2_tag_lookups_o <= cnt_l2_tag_lookups_o + {59'd0, active_way_count};
                cnt_l2_core_acc_o[req_core_id_i] <= cnt_l2_core_acc_o[req_core_id_i] + 64'd1;

                if (req_is_write_i) begin
                    cnt_l2_write_acc_o  <= cnt_l2_write_acc_o + 64'd1;
                    // Broadcast coherence invalidation to remote cores' L1D
                    l1_inval_valid_o    <= 1'b1;
                    l1_inval_src_core_o <= req_core_id_i;
                    l1_inval_addr_o     <= req_addr_i;
                end else begin
                    cnt_l2_read_acc_o <= cnt_l2_read_acc_o + 64'd1;
                end

                if (hit_found) begin
                    cnt_l2_hits_o                    <= cnt_l2_hits_o + 64'd1;
                    cnt_l2_way_hits_o[hit_way]       <= cnt_l2_way_hits_o[hit_way] + 64'd1;
                    cnt_l2_core_hits_o[req_core_id_i]<= cnt_l2_core_hits_o[req_core_id_i] + 64'd1;
                    resp_latency_o                   <= 6'(L2_HIT_LAT);

                    if (req_is_write_i) begin
                        // Write-Back L2 marks line dirty on L1 Write-Through hit
                        dirty_arr[set_idx][hit_way] <= 1'b1;
                    end
                end else begin
                    // L2 Cache Miss -> Allocate in victim_way (Write-Allocate, Write-Back)
                    cnt_l2_misses_o                    <= cnt_l2_misses_o + 64'd1;
                    cnt_l2_core_misses_o[req_core_id_i]<= cnt_l2_core_misses_o[req_core_id_i] + 64'd1;

                    if (valid_arr[set_idx][victim_way] && dirty_arr[set_idx][victim_way]) begin
                        // Dirty victim eviction -> Writeback to DRAM
                        cnt_l2_writebacks_o <= cnt_l2_writebacks_o + 64'd1;
                        resp_latency_o      <= 6'(L2_HIT_LAT + DRAM_MISS_LAT + DRAM_WB_LAT);
                    end else begin
                        resp_latency_o      <= 6'(L2_HIT_LAT + DRAM_MISS_LAT);
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
