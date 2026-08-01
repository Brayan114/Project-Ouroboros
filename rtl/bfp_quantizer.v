// ============================================================================
// Project Ouroboros Phase 3: Block-Floating-Point (BFP) Hardware Quantizer
// Shared Exponent Logic: E_block = ceil(log2(max(|x_i|)))
// Author: Brayan Osinaka
// License: MIT
// ============================================================================

`timescale 1ns / 1ps

module bfp_quantizer (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [255:0] fp16_block_in,   // 16 FP16 elements (256 bits total)
    input  wire        valid_in,

    output reg  [7:0]   block_exponent,  // Shared 8-bit block exponent
    output reg  [63:0]  packed_deltas_4b,// 16 x 4-bit mantissa deltas (64 bits)
    output reg  [9:0]   compressed_size, // 1B exponent + 8B payload = 9 bytes
    output reg          valid_out
);

    // FP16 Format: 1-bit Sign, 5-bit Exponent, 10-bit Mantissa
    wire [4:0] exp0  = fp16_block_in[14:10];
    wire [4:0] exp1  = fp16_block_in[30:26];
    wire [4:0] exp2  = fp16_block_in[46:42];
    wire [4:0] exp3  = fp16_block_in[62:58];
    wire [4:0] exp4  = fp16_block_in[78:74];
    wire [4:0] exp5  = fp16_block_in[94:90];
    wire [4:0] exp6  = fp16_block_in[110:106];
    wire [4:0] exp7  = fp16_block_in[126:122];
    wire [4:0] exp8  = fp16_block_in[142:138];
    wire [4:0] exp9  = fp16_block_in[158:154];
    wire [4:0] exp10 = fp16_block_in[174:170];
    wire [4:0] exp11 = fp16_block_in[190:186];
    wire [4:0] exp12 = fp16_block_in[206:202];
    wire [4:0] exp13 = fp16_block_in[222:218];
    wire [4:0] exp14 = fp16_block_in[238:234];
    wire [4:0] exp15 = fp16_block_in[254:250];

    // Tree Max Exponent Reduction
    wire [4:0] max_e0 = (exp0 > exp1) ? exp0 : exp1;
    wire [4:0] max_e1 = (exp2 > exp3) ? exp2 : exp3;
    wire [4:0] max_e2 = (exp4 > exp5) ? exp4 : exp5;
    wire [4:0] max_e3 = (exp6 > exp7) ? exp6 : exp7;
    wire [4:0] max_e4 = (exp8 > exp9) ? exp8 : exp9;
    wire [4:0] max_e5 = (exp10 > exp11) ? exp10 : exp11;
    wire [4:0] max_e6 = (exp12 > exp13) ? exp12 : exp13;
    wire [4:0] max_e7 = (exp14 > exp15) ? exp14 : exp15;

    wire [4:0] max_m0 = (max_e0 > max_e1) ? max_e0 : max_e1;
    wire [4:0] max_m1 = (max_e2 > max_e3) ? max_e2 : max_e3;
    wire [4:0] max_m2 = (max_e4 > max_e5) ? max_e4 : max_e5;
    wire [4:0] max_m3 = (max_e6 > max_e7) ? max_e6 : max_e7;

    wire [4:0] max_f0 = (max_m0 > max_m1) ? max_m0 : max_m1;
    wire [4:0] max_f1 = (max_m2 > max_m3) ? max_m2 : max_m3;

    wire [4:0] max_exponent = (max_f0 > max_f1) ? max_f0 : max_f1;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            block_exponent    <= 8'b0;
            packed_deltas_4b  <= 64'b0;
            compressed_size   <= 10'd9; // 1B exp + 8B mantissa
            valid_out         <= 1'b0;
        end else if (valid_in) begin
            valid_out         <= 1'b1;
            block_exponent    <= {3'b0, max_exponent};
            // Pack 4-bit mantissa deltas into 64-bit output vector
            packed_deltas_4b  <= {
                fp16_block_in[249:246], fp16_block_in[233:230], fp16_block_in[217:214], fp16_block_in[201:198],
                fp16_block_in[185:182], fp16_block_in[169:166], fp16_block_in[153:150], fp16_block_in[137:134],
                fp16_block_in[121:118], fp16_block_in[105:102], fp16_block_in[89:86],   fp16_block_in[73:70],
                fp16_block_in[57:54],   fp16_block_in[41:38],   fp16_block_in[25:22],   fp16_block_in[9:6]
            };
            compressed_size   <= 10'd9;
        end else begin
            valid_out <= 1 meb;
        end
    end

endmodule
