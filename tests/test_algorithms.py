"""
Unit Tests for Ouroboros Compression Algorithms (BDI, FPC, Entropy Estimator).
"""

import os
import struct
import unittest

from simulator.algorithms.entropy import calculate_entropy, calculate_normalized_entropy, is_high_entropy
from simulator.algorithms.bdi import BDICompressor, PATTERN_ZER, PATTERN_REP, PATTERN_B8D1, PATTERN_UNCOMPRESSED
from simulator.algorithms.fpc import FPCCompressor


class TestEntropyEstimator(unittest.TestCase):

    def test_zero_bytes_entropy(self):
        data = b'\x00' * 64
        self.assertEqual(calculate_entropy(data), 0.0)
        self.assertFalse(is_high_entropy(data))

    def test_random_bytes_entropy(self):
        # 256 distinct bytes in sequence -> entropy should be 8.0 bits/byte
        data = bytes(range(256))
        self.assertAlmostEqual(calculate_entropy(data), 8.0, places=2)
        self.assertAlmostEqual(calculate_normalized_entropy(data), 1.0, places=2)
        self.assertTrue(is_high_entropy(data))

    def test_threshold_bypass(self):
        low_ent_data = b'AAAAAABBBBBBCCCCCC' * 4
        high_ent_data = bytes(range(256))
        self.assertFalse(is_high_entropy(low_ent_data))
        self.assertTrue(is_high_entropy(high_ent_data))

    def test_64b_line_entropy(self):
        # 64B random line has max entropy 6.0 bits
        high_ent_64b = os.urandom(64)
        self.assertTrue(is_high_entropy(high_ent_64b))


class TestBDICompressor(unittest.TestCase):

    def setUp(self):
        self.bdi = BDICompressor()

    def test_zero_line_compression(self):
        line = b'\x00' * 64
        res = self.bdi.compress(line)
        self.assertEqual(res.pattern, PATTERN_ZER)
        self.assertEqual(res.compressed_size, 1)
        self.assertEqual(res.compression_ratio, 64.0)

        # Verify lossless decompression
        decomp = self.bdi.decompress(res)
        self.assertEqual(decomp, line)

    def test_repeated_line_compression(self):
        line = struct.pack('<q', 0x123456789ABCDEF0) * 8
        res = self.bdi.compress(line)
        self.assertEqual(res.pattern, PATTERN_REP)
        self.assertEqual(res.compressed_size, 8)
        self.assertEqual(res.compression_ratio, 8.0)

        decomp = self.bdi.decompress(res)
        self.assertEqual(decomp, line)

    def test_b8d1_pointer_array_compression(self):
        # Base pointer = 0x00007FFF00001000
        # Subsequent pointers are small deltas within [-128, +127]
        base_ptr = 0x00007FFF00001000
        ptrs = [base_ptr + i * 4 for i in range(8)]
        line = b''.join(struct.pack('<q', p) for p in ptrs)

        res = self.bdi.compress(line)
        self.assertEqual(res.pattern, PATTERN_B8D1)
        self.assertEqual(res.compressed_size, 16)  # 8B base + 8*1B deltas
        self.assertEqual(res.compression_ratio, 4.0)

        decomp = self.bdi.decompress(res)
        self.assertEqual(decomp, line)

    def test_uncompressed_random_data(self):
        # Random bytes should fail BDI base-delta bounds and fallback to Uncompressed
        line = os.urandom(64)
        res = self.bdi.compress(line)
        decomp = self.bdi.decompress(res)
        self.assertEqual(decomp, line)


class TestFPCCompressor(unittest.TestCase):

    def setUp(self):
        self.fpc = FPCCompressor()

    def test_zero_words_fpc(self):
        line = b'\x00' * 64
        res = self.fpc.compress(line)
        self.assertTrue(res.is_compressed)
        self.assertLess(res.compressed_size_bytes, 64)

    def test_small_ints_fpc(self):
        # Array of 16 small 4-bit integers
        line = struct.pack('<16i', *range(16))
        res = self.fpc.compress(line)
        self.assertTrue(res.is_compressed)
        self.assertGreater(res.compression_ratio, 1.5)

    def test_high_entropy_fpc_abort(self):
        line = os.urandom(64)
        res = self.fpc.compress(line)
        self.assertFalse(res.is_compressed)
        self.assertEqual(res.compressed_size_bytes, 64)


if __name__ == '__main__':
    unittest.main()
