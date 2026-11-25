// Copyright 2026 Gem 5 x CVA6 Project
// Synthesizable SystemVerilog RTL: CVA6 RV64IM_Zicsr Core Tile + Private L1I (16KB, 4w) + L1D (32KB, 8w, WT+Inval)

module cva6_core_tile_l1
    import cva6_4core_l2_pkg::*;
#(
    parameter int unsigned HART_ID = 0
) (
    input  logic        clk_i,
    input  logic        rst_ni,

    // Instruction Fetch Memory Port (backed by shared DRAM array in SoC top)
    output logic [63:0] imem_addr_o,
    input  logic [31:0] imem_rdata_i,

    // Data Memory Read/Write Port
    output logic        dmem_we_o,
    output logic [63:0] dmem_addr_o,
    output logic [63:0] dmem_wdata_o,
    output logic [7:0]  dmem_wstrb_o,
    input  logic [63:0] dmem_rdata_i,

    // L1 -> Shared L2 Request Interface (via L2XBar)
    output logic        l2_req_valid_o,
    output logic        l2_req_is_write_o,
    output logic [63:0] l2_req_addr_o,
    input  logic        l2_resp_valid_i,
    input  logic [5:0]  l2_resp_latency_i,

    // L2 -> L1D Coherence Invalidation Port
    input  logic        l1_inval_valid_i,
    input  logic [1:0]  l1_inval_src_core_i,
    input  logic [63:0] l1_inval_addr_i,

    // Per-Core Hardware Performance Counters
    output logic [63:0] cnt_cycles_o,
    output logic [63:0] cnt_instret_o,
    output logic [63:0] cnt_l1i_access_o,
    output logic [63:0] cnt_l1i_misses_o,
    output logic [63:0] cnt_l1d_access_o,
    output logic [63:0] cnt_l1d_hits_o,
    output logic [63:0] cnt_l1d_misses_o
);

    // Architectural State
    logic [63:0] pc_q;
    logic [63:0] rf_q [32];
    logic [5:0]  stall_cnt_q;
    logic        wfi_halted_q;

    // Private L1 I-Cache Tag Directory: 64 Sets x 4 Ways (16 KiB, 64B line)
    logic        l1i_valid [L1I_SETS][L1I_WAYS];
    logic [51:0] l1i_tag   [L1I_SETS][L1I_WAYS];
    logic [1:0]  l1i_rr    [L1I_SETS];

    // Private L1 D-Cache Tag Directory: 64 Sets x 8 Ways (32 KiB, 64B line, Write-Through)
    logic        l1d_valid [L1D_SETS][L1D_WAYS];
    logic [51:0] l1d_tag   [L1D_SETS][L1D_WAYS];
    logic [2:0]  l1d_rr    [L1D_SETS];

    // Pending L2 Transaction Queue (from L1I miss or L1D miss/write-through)
    logic        pend_l2_valid_q;
    logic        pend_l2_write_q;
    logic [63:0] pend_l2_addr_q;

    assign imem_addr_o       = pc_q;
    assign l2_req_valid_o    = pend_l2_valid_q;
    assign l2_req_is_write_o = pend_l2_write_q;
    assign l2_req_addr_o     = pend_l2_addr_q;

    // Decode fields
    wire [31:0] inst   = imem_rdata_i;
    wire [6:0]  opcode = inst[6:0];
    wire [4:0]  rd     = inst[11:7];
    wire [2:0]  funct3 = inst[14:12];
    wire [4:0]  rs1    = inst[19:15];
    wire [4:0]  rs2    = inst[24:20];
    wire [6:0]  funct7 = inst[31:25];

    wire [63:0] rs1_val = (rs1 == 5'd0) ? 64'd0 : rf_q[rs1];
    wire [63:0] rs2_val = (rs2 == 5'd0) ? 64'd0 : rf_q[rs2];

    // Immediates
    wire [63:0] imm_i = {{52{inst[31]}}, inst[31:20]};
    wire [63:0] imm_s = {{52{inst[31]}}, inst[31:25], inst[11:7]};
    wire [63:0] imm_b = {{51{inst[31]}}, inst[31], inst[7], inst[30:25], inst[11:8], 1'b0};
    wire [63:0] imm_u = {{32{inst[31]}}, inst[31:12], 12'b0};
    wire [63:0] imm_j = {{43{inst[31]}}, inst[31], inst[19:12], inst[20], inst[30:21], 1'b0};

    // Effective load/store address
    wire        is_load  = (opcode == 7'b0000011);
    wire        is_store = (opcode == 7'b0100011);
    wire [63:0] ls_addr  = rs1_val + (is_store ? imm_s : imm_i);

    // L1I Lookup
    wire [L1I_SET_W-1:0] l1i_set = pc_q[LINE_OFFSET_W + L1I_SET_W - 1 : LINE_OFFSET_W];
    wire [51:0]          l1i_t   = pc_q[63 : LINE_OFFSET_W + L1I_SET_W];
    logic                l1i_hit;
    always_comb begin
        l1i_hit = 1'b0;
        for (int w = 0; w < L1I_WAYS; w++) begin
            if (l1i_valid[l1i_set][w] && (l1i_tag[l1i_set][w] == l1i_t)) begin
                l1i_hit = 1'b1;
            end
        end
    end

    // L1D Lookup
    wire [L1D_SET_W-1:0] l1d_set = ls_addr[LINE_OFFSET_W + L1D_SET_W - 1 : LINE_OFFSET_W];
    wire [51:0]          l1d_t   = ls_addr[63 : LINE_OFFSET_W + L1D_SET_W];
    logic                l1d_hit;
    always_comb begin
        l1d_hit = 1'b0;
        for (int w = 0; w < L1D_WAYS; w++) begin
            if (l1d_valid[l1d_set][w] && (l1d_tag[l1d_set][w] == l1d_t)) begin
                l1d_hit = 1'b1;
            end
        end
    end

    // Invalidation address decoding
    wire [L1D_SET_W-1:0] inv_set = l1_inval_addr_i[LINE_OFFSET_W + L1D_SET_W - 1 : LINE_OFFSET_W];
    wire [51:0]          inv_tag = l1_inval_addr_i[63 : LINE_OFFSET_W + L1D_SET_W];

    // Combinational Data Memory Read/Write Formatting
    wire [2:0]  byte_off   = ls_addr[2:0];
    wire [63:0] shifted_rd = dmem_rdata_i >> (byte_off * 8);
    logic [63:0] load_val;

    always_comb begin
        dmem_we_o    = 1'b0;
        dmem_addr_o  = ls_addr;
        dmem_wdata_o = 64'd0;
        dmem_wstrb_o = 8'd0;
        load_val     = 64'd0;

        case (funct3)
            3'b000: load_val = {{56{shifted_rd[7]}},  shifted_rd[7:0]};   // LB
            3'b001: load_val = {{48{shifted_rd[15]}}, shifted_rd[15:0]};  // LH
            3'b010: load_val = {{32{shifted_rd[31]}}, shifted_rd[31:0]};  // LW
            3'b011: load_val = shifted_rd;                                // LD
            3'b100: load_val = {56'd0, shifted_rd[7:0]};                  // LBU
            3'b101: load_val = {48'd0, shifted_rd[15:0]};                 // LHU
            3'b110: load_val = {32'd0, shifted_rd[31:0]};                 // LWU
            default: load_val = shifted_rd;
        endcase

        if (is_store && rst_ni && !wfi_halted_q && (stall_cnt_q == 6'd0) && !pend_l2_valid_q) begin
            dmem_we_o    = 1'b1;
            dmem_wdata_o = rs2_val << (byte_off * 8);
            case (funct3)
                3'b000: dmem_wstrb_o = 8'b0000_0001 << byte_off; // SB
                3'b001: dmem_wstrb_o = 8'b0000_0011 << byte_off; // SH
                3'b010: dmem_wstrb_o = 8'b0000_1111 << byte_off; // SW
                3'b011: dmem_wstrb_o = 8'b1111_1111;             // SD
                default: dmem_wstrb_o = 8'b0000_0000;
            endcase
        end
    end

    // Execute Stage ALU / Branch / Mul / Div / CSR Computation
    logic [63:0] next_pc;
    logic        wb_en;
    logic [63:0] wb_data;
    logic [5:0]  exec_extra_lat;
    logic        enter_wfi;

    always_comb begin
        next_pc        = pc_q + 64'd4;
        wb_en          = 1'b0;
        wb_data        = 64'd0;
        exec_extra_lat = 6'd0;
        enter_wfi      = 1'b0;

        case (opcode)
            7'b0110111: begin // LUI
                wb_en   = 1'b1;
                wb_data = imm_u;
            end
            7'b0010111: begin // AUIPC
                wb_en   = 1'b1;
                wb_data = pc_q + imm_u;
            end
            7'b1101111: begin // JAL
                wb_en   = 1'b1;
                wb_data = pc_q + 64'd4;
                next_pc = pc_q + imm_j;
            end
            7'b1100111: begin // JALR
                wb_en   = 1'b1;
                wb_data = pc_q + 64'd4;
                next_pc = (rs1_val + imm_i) & ~64'd1;
            end
            7'b1100011: begin // BRANCH
                automatic logic take = 1'b0;
                case (funct3)
                    3'b000: take = (rs1_val == rs2_val);                   // BEQ
                    3'b001: take = (rs1_val != rs2_val);                   // BNE
                    3'b100: take = ($signed(rs1_val) < $signed(rs2_val));  // BLT
                    3'b101: take = ($signed(rs1_val) >= $signed(rs2_val)); // BGE
                    3'b110: take = (rs1_val < rs2_val);                    // BLTU
                    3'b111: take = (rs1_val >= rs2_val);                   // BGEU
                    default: take = 1'b0;
                endcase
                if (take) begin
                    next_pc        = pc_q + imm_b;
                    exec_extra_lat = 6'd1; // Branch redirect delay
                end
            end
            7'b0000011: begin // LOAD
                wb_en   = 1'b1;
                wb_data = load_val;
            end
            7'b0100011: begin // STORE
                wb_en   = 1'b0;
            end
            7'b0010011: begin // OP-IMM (64-bit)
                wb_en = 1'b1;
                case (funct3)
                    3'b000: wb_data = rs1_val + imm_i;                             // ADDI
                    3'b010: wb_data = {63'd0, $signed(rs1_val) < $signed(imm_i)};  // SLTI
                    3'b011: wb_data = {63'd0, rs1_val < imm_i};                    // SLTIU
                    3'b100: wb_data = rs1_val ^ imm_i;                             // XORI
                    3'b110: wb_data = rs1_val | imm_i;                             // ORI
                    3'b111: wb_data = rs1_val & imm_i;                             // ANDI
                    3'b001: wb_data = rs1_val << inst[25:20];                      // SLLI
                    3'b101: begin
                        if (inst[30]) wb_data = $signed(rs1_val) >>> inst[25:20];  // SRAI
                        else          wb_data = rs1_val >> inst[25:20];            // SRLI
                    end
                    default: wb_data = 64'd0;
                endcase
            end
            7'b0011011: begin // OP-IMM-32 (ADDIW, SLLIW, SRLIW, SRAIW)
                automatic logic [31:0] r32 = 32'd0;
                wb_en = 1'b1;
                case (funct3)
                    3'b000: r32 = rs1_val[31:0] + imm_i[31:0];
                    3'b001: r32 = rs1_val[31:0] << inst[24:20];
                    3'b101: begin
                        if (inst[30]) r32 = $signed(rs1_val[31:0]) >>> inst[24:20];
                        else          r32 = rs1_val[31:0] >> inst[24:20];
                    end
                    default: r32 = 32'd0;
                endcase
                wb_data = {{32{r32[31]}}, r32};
            end
            7'b0110011: begin // OP (64-bit ALU & M-Extension)
                wb_en = 1'b1;
                if (funct7 == 7'b0000001) begin // RV64M
                    case (funct3)
                        3'b000: begin wb_data = rs1_val * rs2_val; exec_extra_lat = 6'd1; end // MUL (2c)
                        3'b100: begin // DIV
                            wb_data = (rs2_val == 64'd0) ? 64'hFFFF_FFFF_FFFF_FFFF :
                                      $signed(rs1_val) / $signed(rs2_val);
                            exec_extra_lat = 6'd12;
                        end
                        3'b101: begin // DIVU
                            wb_data = (rs2_val == 64'd0) ? 64'hFFFF_FFFF_FFFF_FFFF : (rs1_val / rs2_val);
                            exec_extra_lat = 6'd12;
                        end
                        3'b110: begin // REM
                            wb_data = (rs2_val == 64'd0) ? rs1_val : $signed(rs1_val) % $signed(rs2_val);
                            exec_extra_lat = 6'd12;
                        end
                        3'b111: begin // REMU
                            wb_data = (rs2_val == 64'd0) ? rs1_val : (rs1_val % rs2_val);
                            exec_extra_lat = 6'd12;
                        end
                        default: wb_data = rs1_val * rs2_val;
                    endcase
                end else begin
                    case (funct3)
                        3'b000: wb_data = (funct7[5]) ? (rs1_val - rs2_val) : (rs1_val + rs2_val);
                        3'b001: wb_data = rs1_val << rs2_val[5:0];
                        3'b010: wb_data = {63'd0, $signed(rs1_val) < $signed(rs2_val)};
                        3'b011: wb_data = {63'd0, rs1_val < rs2_val};
                        3'b100: wb_data = rs1_val ^ rs2_val;
                        3'b101: wb_data = (funct7[5]) ? ($signed(rs1_val) >>> rs2_val[5:0]) : (rs1_val >> rs2_val[5:0]);
                        3'b110: wb_data = rs1_val | rs2_val;
                        3'b111: wb_data = rs1_val & rs2_val;
                    endcase
                end
            end
            7'b0111011: begin // OP-32 (ADDW, SUBW, SLLW, SRLW, SRAW, MULW, DIVW, REMW, REMUW)
                automatic logic [31:0] r32 = 32'd0;
                wb_en = 1'b1;
                if (funct7 == 7'b0000001) begin
                    case (funct3)
                        3'b000: begin r32 = rs1_val[31:0] * rs2_val[31:0]; exec_extra_lat = 6'd1; end // MULW
                        3'b100: begin
                            r32 = (rs2_val[31:0] == 32'd0) ? 32'hFFFF_FFFF :
                                  $signed(rs1_val[31:0]) / $signed(rs2_val[31:0]);
                            exec_extra_lat = 6'd10;
                        end
                        3'b101: begin
                            r32 = (rs2_val[31:0] == 32'd0) ? 32'hFFFF_FFFF : (rs1_val[31:0] / rs2_val[31:0]);
                            exec_extra_lat = 6'd10;
                        end
                        3'b110: begin
                            r32 = (rs2_val[31:0] == 32'd0) ? rs1_val[31:0] :
                                  $signed(rs1_val[31:0]) % $signed(rs2_val[31:0]);
                            exec_extra_lat = 6'd10;
                        end
                        3'b111: begin
                            r32 = (rs2_val[31:0] == 32'd0) ? rs1_val[31:0] : (rs1_val[31:0] % rs2_val[31:0]);
                            exec_extra_lat = 6'd10;
                        end
                        default: r32 = rs1_val[31:0] * rs2_val[31:0];
                    endcase
                end else if (funct7 == 7'b0000100 && funct3 == 3'b100) begin
                    // Zba / Zbb zext.h / packw fallback if emitted
                    r32 = {16'd0, rs1_val[15:0]};
                end else begin
                    case (funct3)
                        3'b000: r32 = (funct7[5]) ? (rs1_val[31:0] - rs2_val[31:0]) : (rs1_val[31:0] + rs2_val[31:0]);
                        3'b001: r32 = rs1_val[31:0] << rs2_val[4:0];
                        3'b101: r32 = (funct7[5]) ? ($signed(rs1_val[31:0]) >>> rs2_val[4:0]) : (rs1_val[31:0] >> rs2_val[4:0]);
                        default: r32 = 32'd0;
                    endcase
                end
                wb_data = {{32{r32[31]}}, r32};
            end
            7'b1110011: begin // SYSTEM (CSRR* / WFI / ECALL)
                if (funct3 == 3'b000) begin
                    if (inst[31:20] == 12'h105) begin // WFI
                        enter_wfi = 1'b1;
                    end
                end else begin
                    wb_en = 1'b1;
                    case (inst[31:20])
                        12'hF14: wb_data = 64'(HART_ID);     // mhartid
                        12'hB00,
                        12'hC00: wb_data = cnt_cycles_o;     // mcycle / cycle
                        12'hB02,
                        12'hC02: wb_data = cnt_instret_o;    // minstret / instret
                        default: wb_data = 64'd0;
                    endcase
                end
            end
            7'b0001111: begin // FENCE
                wb_en = 1'b0;
            end
            default: begin
                wb_en = 1'b0;
            end
        endcase
    end

    // Sequential Pipeline & L1 Cache State Update
    always_ff @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            pc_q            <= 64'(DRAM_BASE);
            stall_cnt_q     <= 6'd0;
            wfi_halted_q    <= 1'b0;
            pend_l2_valid_q <= 1'b0;
            pend_l2_write_q <= 1'b0;
            pend_l2_addr_q  <= 64'd0;

            cnt_cycles_o     <= 64'd0;
            cnt_instret_o    <= 64'd0;
            cnt_l1i_access_o <= 64'd0;
            cnt_l1i_misses_o <= 64'd0;
            cnt_l1d_access_o <= 64'd0;
            cnt_l1d_hits_o   <= 64'd0;
            cnt_l1d_misses_o <= 64'd0;

            for (int r = 0; r < 32; r++) rf_q[r] <= 64'd0;
            for (int s = 0; s < L1I_SETS; s++) begin
                l1i_rr[s] <= 2'd0;
                for (int w = 0; w < L1I_WAYS; w++) begin
                    l1i_valid[s][w] <= 1'b0;
                    l1i_tag[s][w]   <= 52'd0;
                end
            end
            for (int s = 0; s < L1D_SETS; s++) begin
                l1d_rr[s] <= 3'd0;
                for (int w = 0; w < L1D_WAYS; w++) begin
                    l1d_valid[s][w] <= 1'b0;
                    l1d_tag[s][w]   <= 52'd0;
                end
            end
        end else begin
            if (!wfi_halted_q) begin
                cnt_cycles_o <= cnt_cycles_o + 64'd1;
            end

            // Process incoming L2 -> L1D coherence invalidation from remote cores
            if (l1_inval_valid_i && (l1_inval_src_core_i != 2'(HART_ID))) begin
                for (int w = 0; w < L1D_WAYS; w++) begin
                    if (l1d_valid[inv_set][w] && (l1d_tag[inv_set][w] == inv_tag)) begin
                        l1d_valid[inv_set][w] <= 1'b0;
                    end
                end
            end

            // Wait on pending L2 transaction
            if (pend_l2_valid_q) begin
                if (l2_resp_valid_i) begin
                    pend_l2_valid_q <= 1'b0;
                    // For read refills, stall according to L2 hit / DRAM miss latency
                    if (!pend_l2_write_q && (l2_resp_latency_i > 6'd1)) begin
                        stall_cnt_q <= l2_resp_latency_i - 6'd1;
                    end
                end
            end else if (stall_cnt_q > 6'd0) begin
                stall_cnt_q <= stall_cnt_q - 6'd1;
            end else if (!wfi_halted_q) begin
                // Check L1 I-Cache
                cnt_l1i_access_o <= cnt_l1i_access_o + 64'd1;
                if (!l1i_hit) begin
                    cnt_l1i_misses_o              <= cnt_l1i_misses_o + 64'd1;
                    l1i_valid[l1i_set][l1i_rr[l1i_set]] <= 1'b1;
                    l1i_tag[l1i_set][l1i_rr[l1i_set]]   <= l1i_t;
                    l1i_rr[l1i_set]               <= l1i_rr[l1i_set] + 2'd1;
                    pend_l2_valid_q               <= 1'b1;
                    pend_l2_write_q               <= 1'b0;
                    pend_l2_addr_q                <= pc_q;
                end else begin
                    // Instruction executes and commits
                    cnt_instret_o <= cnt_instret_o + 64'd1;
                    pc_q          <= next_pc;
                    if (wb_en && (rd != 5'd0)) begin
                        rf_q[rd] <= wb_data;
                    end
                    if (enter_wfi) begin
                        wfi_halted_q <= 1'b1;
                    end

                    // Memory operations access Private L1 D-Cache (Write-Through)
                    if (is_load) begin
                        cnt_l1d_access_o <= cnt_l1d_access_o + 64'd1;
                        if (l1d_hit) begin
                            cnt_l1d_hits_o <= cnt_l1d_hits_o + 64'd1;
                            stall_cnt_q    <= 6'(L1_HIT_LAT);
                        end else begin
                            cnt_l1d_misses_o              <= cnt_l1d_misses_o + 64'd1;
                            l1d_valid[l1d_set][l1d_rr[l1d_set]] <= 1'b1;
                            l1d_tag[l1d_set][l1d_rr[l1d_set]]   <= l1d_t;
                            l1d_rr[l1d_set]               <= l1d_rr[l1d_set] + 3'd1;
                            pend_l2_valid_q               <= 1'b1;
                            pend_l2_write_q               <= 1'b0;
                            pend_l2_addr_q                <= ls_addr;
                        end
                    end else if (is_store) begin
                        // Write-Through, No-Write-Allocate L1D -> Always forwards write to Shared L2
                        cnt_l1d_access_o <= cnt_l1d_access_o + 64'd1;
                        if (l1d_hit) begin
                            cnt_l1d_hits_o <= cnt_l1d_hits_o + 64'd1;
                        end else begin
                            cnt_l1d_misses_o <= cnt_l1d_misses_o + 64'd1;
                        end
                        pend_l2_valid_q <= 1'b1;
                        pend_l2_write_q <= 1'b1;
                        pend_l2_addr_q  <= ls_addr;
                    end else if (exec_extra_lat > 6'd0) begin
                        stall_cnt_q <= exec_extra_lat;
                    end
                end
            end
        end
    end

endmodule
