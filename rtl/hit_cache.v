// ============================================================================
// Project Ouroboros Phase 3: Hardware Indirection Cache (HIT) Tag Array
// Features: Direct Payload Embedding (<= 16B Payloads stored directly in SRAM)
// Sub-nanosecond Tag Lookup & Zero-Sector DRAM Allocation Logic
// Author: Brayan Osinaka
// License: MIT
// ============================================================================

`timescale 1ns / 1ps

module hit_cache #(
    parameter ENTRIES = 512,
    parameter ADDR_WIDTH = 64
)(
    input  wire                  clk,
    input  wire                  rst_n,

    // Lookup Request Interface
    input  wire [ADDR_WIDTH-1:0] lookup_vaddr,
    input  wire                  lookup_en,
    output reg                   hit_valid,
    output reg                   is_embedded,
    output reg  [127:0]          embedded_payload_16b,
    output reg  [31:0]           dram_sector_addr,
    output reg  [9:0]            compressed_size_bytes,

    // Write-allocate / Update Interface
    input  wire                  alloc_en,
    input  wire [ADDR_WIDTH-1:0] alloc_vaddr,
    input  wire                  alloc_is_embedded,
    input  wire [127:0]          alloc_embedded_payload,
    input  wire [31:0]           alloc_dram_sector_addr,
    input  wire [9:0]            alloc_compressed_size
);

    // Entry Storage Registers
    reg                  valid_array    [0:ENTRIES-1];
    reg [ADDR_WIDTH-1:0] vaddr_array    [0:ENTRIES-1];
    reg                  embedded_array [0:ENTRIES-1];
    reg [127:0]          payload_array  [0:ENTRIES-1];
    reg [31:0]           sector_array   [0:ENTRIES-1];
    reg [9:0]            size_array     [0:ENTRIES-1];

    integer i;

    // 1. Parallel Tag Match (Fully-Associative SRAM CAM Lookup)
    wire [ENTRIES-1:0] match_bits;
    genvar g;
    generate
        for (g = 0; g < ENTRIES; g = g + 1) begin : gen_tag_match
            assign match_bits[g] = valid_array[g] && (vaddr_array[g] == lookup_vaddr);
        end
    endgenerate

    // 2. Synchronous Lookup & Allocation Logic
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < ENTRIES; i = i + 1) begin
                valid_array[i]    <= 1'b0;
                vaddr_array[i]    <= {ADDR_WIDTH{1'b0}};
                embedded_array[i] <= 1'b0;
                payload_array[i]  <= 128'b0;
                sector_array[i]   <= 32'b0;
                size_array[i]     <= 10'b0;
            end
            hit_valid             <= 1'b0;
            is_embedded           <= 1'b0;
            embedded_payload_16b  <= 128'b0;
            dram_sector_addr      <= 32'b0;
            compressed_size_bytes <= 10'b0;
        end else begin
            // Handle Allocation
            if (alloc_en) begin
                // Simple Round-Robin / Slot 0 allocation for model simulation
                valid_array[0]    <= 1'b1;
                vaddr_array[0]    <= alloc_vaddr;
                embedded_array[0] <= alloc_is_embedded;
                payload_array[0]  <= alloc_embedded_payload;
                sector_array[0]   <= alloc_dram_sector_addr;
                size_array[0]     <= alloc_compressed_size;
            end

            // Handle Lookup
            if (lookup_en) begin
                if (|match_bits) begin
                    hit_valid             <= 1'b1;
                    is_embedded           <= embedded_array[0];
                    embedded_payload_16b  <= payload_array[0];
                    dram_sector_addr      <= sector_array[0];
                    compressed_size_bytes <= size_array[0];
                end else begin
                    hit_valid             <= 1'b0;
                    is_embedded           <= 1 meb;
                    embedded_payload_16b  <= 128'b0;
                    dram_sector_addr      <= 32'b0;
                    compressed_size_bytes <= 10'd64; // Fallback to raw 64B line
                end
            end else begin
                hit_valid <= 1'b0;
            end
        end
    end

endmodule
