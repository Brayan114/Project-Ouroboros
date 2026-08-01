// ============================================================================
// Project Ouroboros Phase 3: Top-Level Memory Controller (Synthesizable RTL)
// Binding: BDI Compressor + BFP Quantizer + HIT Cache Tag Array
// Author: Brayan Osinaka
// License: MIT
// ============================================================================

`timescale 1ns / 1ps

module top_ouroboros_controller (
    input  wire        clk,
    input  wire        rst_n,

    // Memory Bus Transaction Request
    input  wire [63:0] req_vaddr,
    input  wire [511:0]req_wdata,
    input  wire        req_write_en,
    input  wire        req_read_en,

    // Response Output Interface
    output wire        hit_match,
    output wire        is_embedded_payload,
    output wire [127:0]embedded_payload,
    output wire [31:0] dram_sector_addr,
    output wire [9:0]  line_compressed_size
);

    // Wires for BDI Compressor
    wire [3:0]   bdi_pattern;
    wire [511:0] bdi_payload;
    wire [9:0]   bdi_bytes;
    wire         bdi_is_compressed;
    wire         bdi_valid;

    // Instantiate BDI Compressor Engine
    bdi_compressor u_bdi_compressor (
        .clk(clk),
        .rst_n(rst_n),
        .line_in(req_wdata),
        .valid_in(req_write_en),
        .pattern_out(bdi_pattern),
        .compressed_payload(bdi_payload),
        .compressed_bytes(bdi_bytes),
        .is_compressed(bdi_is_compressed),
        .valid_out(bdi_valid)
    );

    // Determine Direct Payload Embedding (<= 16 Bytes Payload)
    wire alloc_is_embed = (bdi_bytes <= 10'd16);

    // Instantiate Hardware Indirection Cache (HIT) Tag Array
    hit_cache #(
        .ENTRIES(512),
        .ADDR_WIDTH(64)
    ) u_hit_cache (
        .clk(clk),
        .rst_n(rst_n),
        .lookup_vaddr(req_vaddr),
        .lookup_en(req_read_en),
        .hit_valid(hit_match),
        .is_embedded(is_embedded_payload),
        .embedded_payload_16b(embedded_payload),
        .dram_sector_addr(dram_sector_addr),
        .compressed_size_bytes(line_compressed_size),
        .alloc_en(req_write_en && bdi_valid),
        .alloc_vaddr(req_vaddr),
        .alloc_is_embedded(alloc_is_embed),
        .alloc_embedded_payload(bdi_payload[127:0]),
        .alloc_dram_sector_addr(32'h0000_1000),
        .alloc_compressed_size(bdi_bytes)
    );

endmodule
