"""
Unit Tests for Block-Floating-Point (BFP) Quantization Engine.
"""

import math
import struct
import unittest

from simulator.algorithms.bfp import BFPCompressor, BFPBlock, BFPResult, BLOCK_SIZE
from simulator.benchmarks.dataset_generator import WorkloadGenerator


class TestBFPCompressor(unittest.TestCase):

    def setUp(self):
        self.bfp = BFPCompressor(block_size=16)

    def test_single_block_compression_decompression(self):
        floats = [1.0, 0.5, 0.25, 0.125, -0.75, -0.5, 0.0, 0.1,
                  0.9, -0.2, 0.33, -0.88, 0.05, -0.01, 0.7, -0.4]
        block = self.bfp.compress_block(floats, mantissa_bits=4)

        self.assertEqual(len(block.mantissa_deltas), 16)
        self.assertEqual(block.mantissa_bits, 4)

        recon = self.bfp.decompress_block(block)
        self.assertEqual(len(recon), 16)

        for orig, r in zip(floats, recon):
            self.assertLess(abs(orig - r), 0.15)

    def test_shared_exponent_computation(self):
        floats = [8.0, 4.0, 2.0, 1.0] + [0.0] * 12
        block = self.bfp.compress_block(floats, mantissa_bits=4)

        self.assertEqual(block.block_exponent, 3)
        self.assertEqual(block.mantissa_deltas[0], 7)

    def test_zero_block_compression(self):
        floats = [0.0] * 16
        block = self.bfp.compress_block(floats, mantissa_bits=4)

        self.assertEqual(block.block_exponent, 0)
        self.assertTrue(all(d == 0 for d in block.mantissa_deltas))

        recon = self.bfp.decompress_block(block)
        self.assertEqual(recon, floats)

    def test_pack_unpack_block(self):
        floats = [1.5, -0.75, 0.375, -0.1875] + [0.0] * 12
        original_block = self.bfp.compress_block(floats, mantissa_bits=4)

        packed = self.bfp.pack_block(original_block)
        self.assertEqual(len(packed), 9)

        unpacked_block = self.bfp.unpack_block(packed, mantissa_bits=4)
        self.assertEqual(unpacked_block.block_exponent, original_block.block_exponent)
        self.assertEqual(unpacked_block.mantissa_deltas, original_block.mantissa_deltas)

    def test_compression_ratio_fp16(self):
        values = [0.1 * (i % 10) for i in range(32)]

        res_4b = self.bfp.compress_tensor(values, dtype="fp16", mantissa_bits=4)
        self.assertGreaterEqual(res_4b.compression_ratio, 3.5)
        self.assertLessEqual(res_4b.compression_ratio, 4.5)

        res_2b = self.bfp.compress_tensor(values, dtype="fp16", mantissa_bits=2)
        self.assertGreaterEqual(res_2b.compression_ratio, 6.0)
        self.assertLessEqual(res_2b.compression_ratio, 8.5)

    def test_compression_ratio_fp8(self):
        values = [float(i % 8) for i in range(32)]

        res_2b = self.bfp.compress_tensor(values, dtype="fp8", mantissa_bits=2)
        self.assertGreaterEqual(res_2b.compression_ratio, 3.0)

    def test_llm_kv_cache_trace_compression(self):
        traces = WorkloadGenerator.generate_llm_kv_cache_trace(count=50)

        ratios = []
        mses = []
        for line in traces:
            res = self.bfp.compress(line, dtype="fp16", mantissa_bits=4)
            ratios.append(res.compression_ratio)
            mses.append(res.mean_squared_error)

            decomp = self.bfp.decompress(res)
            self.assertEqual(len(decomp), len(line))

        avg_ratio = sum(ratios) / len(ratios)
        avg_mse = sum(mses) / len(mses)

        self.assertGreaterEqual(avg_ratio, 3.5)
        self.assertLess(avg_mse, 10.0)

    def test_error_metrics(self):
        values = [1.0, 2.0, 3.0, 4.0] + [0.0] * 12
        res = self.bfp.compress_tensor(values, dtype="fp16", mantissa_bits=4)

        self.assertGreaterEqual(res.mean_squared_error, 0.0)
        self.assertGreaterEqual(res.max_absolute_error, 0.0)


if __name__ == '__main__':
    unittest.main()
