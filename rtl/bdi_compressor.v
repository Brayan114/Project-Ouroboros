// ============================================================================
// Project Ouroboros Phase 3: Synthesizable Base-Delta-Immediate (BDI) Compressor
// Hardware Architecture: Parallel 8-Pattern Vector Adder Engine
// Author: Brayan Osinaka
// License: MIT
// ============================================================================

`timescale 1ns / 1ps

module bdi_compressor (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [511:0] line_in,          // 64-byte input cache line
    input  wire        valid_in,

    output reg  [3:0]   pattern_out,       // Matched BDI pattern ID
    output reg  [511:0] compressed_payload,// Compressed byte stream
    output reg  [9:0]   compressed_bytes,  // Size in bytes (1 to 64)
    output reg          is_compressed,     // High if compressed_bytes < 64
    output reg          valid_out
);

    // Pattern Encoding Constants
    localparam PAT_ZER          = 4'dB000; // Zero line
    localparam PAT_REP          = 4'dB001; // Repeated 8-byte value
    localparam PAT_B8D1         = 4'dB010; // Base 8B, Delta 1B
    localparam PAT_B8D2         = 4'dB011; // Base 8B, Delta 2B
    localparam PAT_B8D4         = 4'dB100; // Base 8B, Delta 4B
    localparam PAT_B4D1         = 4'dB101; // Base 4B, Delta 1B
    localparam PAT_B4D2         = 4'dB110; // Base 4B, Delta 2B
    localparam PAT_UNCOMPRESSED = 4'dB111; // Uncompressed fallback

    // 1. Zero Line Detection Logic
    wire is_zero = (line_in == 512'b0);

    // 2. 8-Byte Word Extraction
    wire signed [63:0] w64 [0:7];
    genvar i;
    generate
        for (i = 0; i < 8; i = i + 1) begin : gen_w64
            assign w64[i] = line_in[i*64 +: 64];
        end
    endgenerate

    // 3. Repeated Value Detection Logic
    wire is_rep = (w64[0] == w64[1]) && (w64[0] == w64[2]) && (w64[0] == w64[3]) &&
                 (w64[0] == w64[4]) && (w64[0] == w64[5]) && (w64[0] == w64[6]) && (w64[0] == w64[7]);

    // 4. B8 Delta Calculation (Base = w64[0])
    wire signed [63:0] b8_base = w64[0];
    wire signed [63:0] b8_deltas [0:7];
    generate
        for (i = 0; i < 8; i = i + 1) begin : gen_b8_deltas
            assign b8_deltas[i] = w64[i] - b8_base;
        end
    endgenerate

    // Check B8D1: All deltas fit in 8-bit signed integer [-128, 127]
    wire b8d1_valid = (b8_deltas[0] >= -128 && b8_deltas[0] <= 127) &&
                      (b8_deltas[1] >= -128 && b8_deltas[1] <= 127) &&
                      (b8_deltas[2] >= -128 && b8_deltas[2] <= 127) &&
                      (b8_deltas[3] >= -128 && b8_deltas[3] <= 127) &&
                      (b8_deltas[4] >= -128 && b8_deltas[4] <= 127) &&
                      (b8_deltas[5] >= -128 && b8_deltas[5] <= 127) &&
                      (b8_deltas[6] >= -128 && b8_deltas[6] <= 127) &&
                      (b8_deltas[7] >= -128 && b8_deltas[7] <= 127);

    // Check B8D2: All deltas fit in 16-bit signed integer [-32768, 32767]
    wire b8d2_valid = (b8_deltas[0] >= -32768 && b8_deltas[0] <= 32767) &&
                      (b8_deltas[1] >= -32768 && b8_deltas[1] <= 32767) &&
                      (b8_deltas[2] >= -32768 && b8_deltas[2] <= 32767) &&
                      (b8_deltas[3] >= -32768 && b8_deltas[3] <= 32767) &&
                      (b8_deltas[4] >= -32768 && b8_deltas[4] <= 32767) &&
                      (b8_deltas[5] >= -32768 && b8_deltas[5] <= 32767) &&
                      (b8_deltas[6] >= -32768 && b8_deltas[6] <= 32767) &&
                      (b8_deltas[7] >= -32768 && b8_deltas[7] <= 32767);

    // 5. Parallel Pipeline Evaluation & Payload Packing
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pattern_out        <= PAT_UNCOMPRESSED;
            compressed_payload <= 512'b0;
            compressed_bytes   <= 10'd64;
            is_compressed      <= 1'b0;
            valid_out          <= 1'b0;
        end else if (valid_in) begin
            valid_out <= 1'b1;
            if (is_zero) begin
                pattern_out        <= PAT_ZER;
                compressed_payload <= 512'b0;
                compressed_bytes   <= 10'd1;
                is_compressed      <= 1'b1;
            end else if (is_rep) begin
                pattern_out        <= PAT_REP;
                compressed_payload <= {448'b0, b8_base};
                compressed_bytes   <= 10'd8;
                is_compressed      <= 1'b1;
            end else if (b8d1_valid) begin
                pattern_out        <= PAT_B8D1;
                compressed_payload <= {
                    320'b0,
                    b8_deltas[7][7:0], b8_deltas[6][7:0], b8_deltas[5][7:0], b8_deltas[4][7:0],
                    b8_deltas[3][7:0], b8_deltas[2][7:0], b8_deltas[1][7:0], b8_deltas[0][7:0],
                    b8_base
                };
                compressed_bytes   <= 10'd16; // 8B base + 8*1B deltas
                is_compressed      <= 1'b1;
            end else if (b8d2_valid) begin
                pattern_out        <= PAT_B8D2;
                compressed_payload <= {
                    256'b0,
                    b8_deltas[7][15:0], b8_deltas[6][15:0], b8_deltas[5][15:0], b8_deltas[4][15:0],
                    b8_deltas[3][15:0], b8_deltas[2][15:0], b8_deltas[1][15:0], b8_deltas[0][15:0],
                    b8_base
                };
                compressed_bytes   <= 10'd24; // 8B base + 8*2B deltas
                is_compressed      <= 1'b1;
            end else begin
                pattern_out        <= PAT_UNCOMPRESSED;
                compressed_payload <= line_in;
                compressed_bytes   <= 10'd64;
                is_compressed      <= 1'b0;
            end
        end else begin
            valid_out <= 1'b0;
        end
    end

endmodule
