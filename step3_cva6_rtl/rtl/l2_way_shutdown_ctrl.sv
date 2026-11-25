// Copyright 2026 Gem5 x CVA6 Project
// Synthesizable SystemVerilog RTL: L2 Way-Shutdown Controller (atd_dirty_aware)
// Implements:
//   - 16-Set Sampled-Set Auxiliary Tag Directory (ATD, 16-way LRU stack)
//   - Epoch Decision Engine (2048 L2 accesses, Streaming Detector <5%, 98.5% hit retention)
//   - Write-Back Dirty-Flush Cost Guard (dirty_cnt[w] <= 96 lines)
//   - Power-Gating & Dirty-Way Flush Handshake FSM (T_wakeup = 6 cycles)

module l2_way_shutdown_ctrl
    import cva6_4core_l2_pkg::*;
#(
    parameter int unsigned EPOCH_ACCESSES     = 2048,
    parameter int unsigned MIN_ACTIVE_WAYS    = 2,
    parameter int unsigned WAKEUP_CYCLES      = 6,
    parameter int unsigned DIRTY_FLUSH_THRESH = 96,
    parameter int unsigned ATD_NUM_SETS       = 16
) (
    input  logic                        clk_i,
    input  logic                        rst_ni,
    input  logic                        ws_enable_i,

    // L2 Access Snoop Interface (off critical path)
    input  logic                        l2_req_valid_i,
    input  logic                        l2_req_is_write_i,
    input  logic [63:0]                 l2_req_addr_i,

    // Per-Way Dirty Line Counters from Shared L2
    input  logic [9:0]                  way_dirty_cnt_i [L2_WAYS],

    // Dirty-Way Flush Handshake with Shared L2
    output logic                        flush_req_o,
    output logic [3:0]                  flush_way_o,
    input  logic                        flush_done_i,

    // Way Enable & Power-Gating Outputs
    output logic [L2_WAYS-1:0]          way_en_o,
    output logic [L2_WAYS-1:0]          way_sd_o,
    output logic                        wakeup_stall_o,

    // Hardware Telemetry Counters
    output logic [63:0]                 cnt_epochs_o,
    output logic [63:0]                 cnt_shutdowns_o,
    output logic [63:0]                 cnt_wakeups_o,
    output logic [63:0]                 cnt_active_way_cycles_o
);

    typedef enum logic [1:0] {
        S_IDLE        = 2'd0,
        S_FLUSH_WAY   = 2'd1,
        S_WAKEUP_WAIT = 2'd2
    } ws_state_e;

    ws_state_e state_q;

    // Current & pending active way counts (1..16)
    logic [4:0]  cur_ways_q;
    logic [4:0]  target_ways_q;
    logic [3:0]  wakeup_cnt_q;
    logic [31:0] epoch_acc_q;

    // Sampled-Set ATD: 16 sampled sets x 16 LRU stack positions (Tag only, 20-bit compressed tag + valid)
    // Samples 1 in 32 L2 sets: set_idx[4:0] == 5'b00000
    logic [19:0] atd_tag_q   [ATD_NUM_SETS][L2_WAYS];
    logic        atd_val_q   [ATD_NUM_SETS][L2_WAYS];
    logic [31:0] atd_hits_q  [L2_WAYS];
    logic [31:0] atd_acc_q;

    wire [L2_SET_W-1:0] set_idx     = l2_req_addr_i[LINE_OFFSET_W + L2_SET_W - 1 : LINE_OFFSET_W];
    wire                atd_sampled = l2_req_valid_i && (set_idx[4:0] == 5'b00000);
    wire [3:0]          atd_set_idx = set_idx[8:5];
    wire [19:0]         atd_req_tag = l2_req_addr_i[34:15];

    // Combinational ATD Lookup
    logic       atd_hit_found;
    logic [3:0] atd_hit_depth;

    always_comb begin
        atd_hit_found = 1'b0;
        atd_hit_depth = 4'd0;
        for (int d = 0; d < L2_WAYS; d++) begin
            if (!atd_hit_found && atd_val_q[atd_set_idx][d] && (atd_tag_q[atd_set_idx][d] == atd_req_tag)) begin
                atd_hit_found = 1'b1;
                atd_hit_depth = d[3:0];
            end
        end
    end

    // Combinational Epoch Target Way Computation (ATD Utility + Streaming Detector)
    logic [31:0] total_atd_hits;
    logic [31:0] cum_atd_hits;
    logic [4:0]  calc_k_opt;
    logic [4:0]  calc_target_ways;
    logic        found_k;
    logic [4:0]  powered_way_count;

    always_comb begin
        total_atd_hits = 32'd0;
        for (int d = 0; d < L2_WAYS; d++) begin
            total_atd_hits = total_atd_hits + atd_hits_q[d];
        end

        cum_atd_hits = 32'd0;
        found_k      = 1'b0;
        calc_k_opt   = 5'(MIN_ACTIVE_WAYS);

        if ((total_atd_hits == 32'd0) || ((total_atd_hits * 32'd20) < atd_acc_q)) begin
            // Streaming / low-reuse phase (<5% ATD hit rate): shrink to 4 ways
            calc_target_ways = (MIN_ACTIVE_WAYS > 4) ? 5'(MIN_ACTIVE_WAYS) : 5'd4;
        end else begin
            for (int d = 0; d < L2_WAYS; d++) begin
                cum_atd_hits = cum_atd_hits + atd_hits_q[d];
                if (!found_k && ((cum_atd_hits * 32'd1000) >= (total_atd_hits * 32'd985))) begin
                    found_k    = 1'b1;
                    calc_k_opt = ((d + 1) < MIN_ACTIVE_WAYS) ? 5'(MIN_ACTIVE_WAYS) : 5'(d + 1);
                end
            end
            // Align up to even step (2, 4, 6, 8, 10, 12, 14, 16)
            if (calc_k_opt[0] == 1'b1) begin
                calc_k_opt = calc_k_opt + 5'd1;
            end
            if (calc_k_opt > 5'd16) begin
                calc_target_ways = 5'd16;
            end else if (calc_k_opt < 5'(MIN_ACTIVE_WAYS)) begin
                calc_target_ways = 5'(MIN_ACTIVE_WAYS);
            end else begin
                calc_target_ways = calc_k_opt;
            end
        end

        // Count currently powered-on ways (~way_sd_o) for cycle-accurate leakage accounting
        powered_way_count = 5'd0;
        for (int w = 0; w < L2_WAYS; w++) begin
            if (!way_sd_o[w]) begin
                powered_way_count = powered_way_count + 5'd1;
            end
        end
    end

    assign wakeup_stall_o = (state_q == S_WAKEUP_WAIT);

    // Helper function to generate contiguous low-way bitmask for k ways
    function automatic logic [L2_WAYS-1:0] ways_to_mask(input logic [4:0] k);
        logic [L2_WAYS-1:0] m;
        m = '0;
        for (int w = 0; w < L2_WAYS; w++) begin
            if (w < int'(k)) begin
                m[w] = 1'b1;
            end
        end
        return m;
    endfunction

    // Sequential State, ATD Update & Power-Gating FSM
    always_ff @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            state_q                 <= S_IDLE;
            cur_ways_q              <= 5'd16;
            target_ways_q           <= 5'd16;
            wakeup_cnt_q            <= 4'd0;
            epoch_acc_q             <= 32'd0;
            atd_acc_q               <= 32'd0;
            way_en_o                <= 16'hFFFF;
            way_sd_o                <= 16'h0000;
            flush_req_o             <= 1'b0;
            flush_way_o             <= 4'd0;
            cnt_epochs_o            <= 64'd0;
            cnt_shutdowns_o         <= 64'd0;
            cnt_wakeups_o           <= 64'd0;
            cnt_active_way_cycles_o <= 64'd0;

            for (int d = 0; d < L2_WAYS; d++) begin
                atd_hits_q[d] <= 32'd0;
            end
            for (int s = 0; s < ATD_NUM_SETS; s++) begin
                for (int d = 0; d < L2_WAYS; d++) begin
                    atd_tag_q[s][d] <= 20'd0;
                    atd_val_q[s][d] <= 1'b0;
                end
            end
        end else begin
            cnt_active_way_cycles_o <= cnt_active_way_cycles_o + {59'd0, powered_way_count};

            // 1. Update Sampled-Set ATD on sampled L2 accesses (filter redundant L1D WT MRU bursts)
            if (atd_sampled) begin
                if (!(l2_req_is_write_i && atd_hit_found && (atd_hit_depth == 4'd0))) begin
                    atd_acc_q <= atd_acc_q + 32'd1;
                    if (atd_hit_found) begin
                        atd_hits_q[atd_hit_depth] <= atd_hits_q[atd_hit_depth] + 32'd1;
                        for (int d = 1; d < L2_WAYS; d++) begin
                            if (d <= int'(atd_hit_depth)) begin
                                atd_tag_q[atd_set_idx][d] <= atd_tag_q[atd_set_idx][d - 1];
                                atd_val_q[atd_set_idx][d] <= atd_val_q[atd_set_idx][d - 1];
                            end
                        end
                        atd_tag_q[atd_set_idx][0] <= atd_req_tag;
                        atd_val_q[atd_set_idx][0] <= 1'b1;
                    end else begin
                        for (int d = 1; d < L2_WAYS; d++) begin
                            atd_tag_q[atd_set_idx][d] <= atd_tag_q[atd_set_idx][d - 1];
                            atd_val_q[atd_set_idx][d] <= atd_val_q[atd_set_idx][d - 1];
                        end
                        atd_tag_q[atd_set_idx][0] <= atd_req_tag;
                        atd_val_q[atd_set_idx][0] <= 1'b1;
                    end
                end
            end

            // 2. Count L2 accesses toward epoch boundary
            if (l2_req_valid_i && (state_q == S_IDLE)) begin
                epoch_acc_q <= epoch_acc_q + 32'd1;
            end

            // 3. Way-Shutdown & Power-Gating FSM
            case (state_q)
                S_IDLE: begin
                    flush_req_o <= 1'b0;
                    if (!ws_enable_i) begin
                        way_en_o   <= 16'hFFFF;
                        way_sd_o   <= 16'h0000;
                        cur_ways_q <= 5'd16;
                    end else if (epoch_acc_q >= EPOCH_ACCESSES) begin
                        epoch_acc_q  <= 32'd0;
                        cnt_epochs_o <= cnt_epochs_o + 64'd1;

                        // Exponential decay of ATD counters for smooth phase tracking
                        atd_acc_q <= atd_acc_q >> 1;
                        for (int d = 0; d < L2_WAYS; d++) begin
                            atd_hits_q[d] <= atd_hits_q[d] >> 1;
                        end

                        if (calc_target_ways > cur_ways_q) begin
                            // Wakeup transition (0 -> 1): deassert power-gate & wait T_wakeup
                            target_ways_q <= calc_target_ways;
                            way_sd_o      <= ~ways_to_mask(calc_target_ways);
                            wakeup_cnt_q  <= 4'(WAKEUP_CYCLES);
                            state_q       <= S_WAKEUP_WAIT;
                        end else if (calc_target_ways < cur_ways_q) begin
                            // Shutdown transition (1 -> 0) with Dirty-Flush Cost Guard
                            if (way_dirty_cnt_i[cur_ways_q - 5'd1] <= 10'(DIRTY_FLUSH_THRESH)) begin
                                target_ways_q                  <= calc_target_ways;
                                way_en_o[cur_ways_q - 5'd1]    <= 1'b0;
                                flush_req_o                    <= 1'b1;
                                flush_way_o                    <= 4'(cur_ways_q - 5'd1);
                                state_q                        <= S_FLUSH_WAY;
                            end
                        end
                    end
                end

                S_FLUSH_WAY: begin
                    if (flush_done_i) begin
                        // Complete power-gating of flushed way
                        way_sd_o[flush_way_o] <= 1'b1;
                        cnt_shutdowns_o       <= cnt_shutdowns_o + 64'd1;
                        cur_ways_q            <= cur_ways_q - 5'd1;

                        // Chain-flush next way if still above target and within dirty guard
                        if (((cur_ways_q - 5'd1) > target_ways_q) &&
                            (way_dirty_cnt_i[cur_ways_q - 5'd2] <= 10'(DIRTY_FLUSH_THRESH))) begin
                            way_en_o[cur_ways_q - 5'd2] <= 1'b0;
                            flush_req_o                 <= 1'b1;
                            flush_way_o                 <= 4'(cur_ways_q - 5'd2);
                            state_q                     <= S_FLUSH_WAY;
                        end else begin
                            flush_req_o <= 1'b0;
                            state_q     <= S_IDLE;
                        end
                    end
                end

                S_WAKEUP_WAIT: begin
                    if (wakeup_cnt_q <= 4'd1) begin
                        way_en_o      <= ways_to_mask(target_ways_q);
                        way_sd_o      <= ~ways_to_mask(target_ways_q);
                        cnt_wakeups_o <= cnt_wakeups_o + {59'd0, (target_ways_q - cur_ways_q)};
                        cur_ways_q    <= target_ways_q;
                        state_q       <= S_IDLE;
                    end else begin
                        wakeup_cnt_q <= wakeup_cnt_q - 4'd1;
                    end
                end

                default: state_q <= S_IDLE;
            endcase
        end
    end

endmodule
