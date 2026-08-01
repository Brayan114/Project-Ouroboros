"""
Unit Tests for SystemVerilog RTL Hardware Modules (Phase 3).
"""

import os
import re
import unittest
from pathlib import Path


class TestRTLHardwareModules(unittest.TestCase):

    def setUp(self):
        self.rtl_dir = Path("rtl")
        self.required_modules = [
            "bdi_compressor.v",
            "hit_cache.v",
            "bfp_quantizer.v",
            "top_ouroboros_controller.v",
        ]

    def test_rtl_files_exist(self):
        for mod_name in self.required_modules:
            mod_path = self.rtl_dir / mod_name
            self.assertTrue(mod_path.exists(), f"Missing RTL module file: {mod_path}")

    def test_bdi_compressor_syntax(self):
        path = self.rtl_dir / "bdi_compressor.v"
        content = path.read_text(encoding="utf-8")

        self.assertIn("module bdi_compressor", content)
        self.assertIn("input  wire [511:0] line_in", content)
        self.assertIn("output reg  [3:0]   pattern_out", content)
        self.assertIn("output reg  [9:0]   compressed_bytes", content)
        self.assertIn("is_zero =", content)
        self.assertIn("is_rep =", content)

    def test_hit_cache_syntax(self):
        path = self.rtl_dir / "hit_cache.v"
        content = path.read_text(encoding="utf-8")

        self.assertIn("module hit_cache", content)
        self.assertIn("input  wire [ADDR_WIDTH-1:0] lookup_vaddr", content)
        self.assertIn("output reg                   hit_valid", content)
        self.assertIn("output reg                   is_embedded", content)
        self.assertIn("output reg  [127:0]          embedded_payload_16b", content)

    def test_bfp_quantizer_syntax(self):
        path = self.rtl_dir / "bfp_quantizer.v"
        content = path.read_text(encoding="utf-8")

        self.assertIn("module bfp_quantizer", content)
        self.assertIn("input  wire [255:0] fp16_block_in", content)
        self.assertIn("output reg  [7:0]   block_exponent", content)
        self.assertIn("output reg  [63:0]  packed_deltas_4b", content)

    def test_top_ouroboros_controller_syntax(self):
        path = self.rtl_dir / "top_ouroboros_controller.v"
        content = path.read_text(encoding="utf-8")

        self.assertIn("module top_ouroboros_controller", content)
        self.assertIn("bdi_compressor u_bdi_compressor", content)
        self.assertIn("hit_cache #(", content)
        self.assertIn("output wire        is_embedded_payload", content)


if __name__ == '__main__':
    unittest.main()
