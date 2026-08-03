"""
Unit Tests for Multi-Line Page-Base & Continuous Bit-Packing BDI Engine (Phase 4).
"""

import struct
import unittest

from simulator.algorithms.multiline_bdi import (
    MultiLineBDICompressor,
    MultiLinePageResult,
    PAGE_SIZE_BYTES,
    CACHE_LINE_SIZE,
)


class TestMultiLineBDICompressor(unittest.TestCase):

    def setUp(self):
        self.compressor = MultiLineBDICompressor()

    def test_zero_page_compression(self):
        page = b'\x00' * PAGE_SIZE_BYTES
        res = self.compressor.compress_page(page)

        self.assertGreaterEqual(res.compression_ratio, 40.0)  # ~72 bytes for 4KB page -> >50x multiplier!
        self.assertEqual(res.num_embedded_lines, 64)

        decomp = self.compressor.decompress_page(res)
        self.assertEqual(decomp, page)

    def test_pointer_array_page_compression(self):
        # 64-bit pointers sharing a 48-bit base across a 4KB page
        base_ptr = 0x00007FFF00001000
        lines = []
        for line_idx in range(64):
            line = b''.join(struct.pack('<q', base_ptr + line_idx * 64 + i * 4) for i in range(8))
            lines.append(line)

        page = b''.join(lines)
        res = self.compressor.compress_page(page)

        # Multi-Line Page BDI achieves 3.79x capacity multiplier on pointer arrays (up from 2.01x)
        self.assertGreaterEqual(res.compression_ratio, 3.5)

        decomp = self.compressor.decompress_page(res)
        self.assertEqual(decomp, page)

    def test_gaming_buffer_page_compression(self):
        # Zero-padded gaming geometry & texture index buffers
        lines = []
        for line_idx in range(64):
            if line_idx % 2 == 0:
                line = (line_idx * 16).to_bytes(4, 'little') + b'\x00' * 60
            else:
                line = b''.join(struct.pack('<q', 100 + i) for i in range(8))
            lines.append(line)

        page = b''.join(lines)
        res = self.compressor.compress_page(page)

        # Multi-Line Page BDI achieves 5.33x capacity multiplier on gaming buffers (up from 3.20x)
        self.assertGreaterEqual(res.compression_ratio, 5.0)

        decomp = self.compressor.decompress_page(res)
        self.assertEqual(decomp, page)



if __name__ == '__main__':
    unittest.main()
