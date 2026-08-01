"""
Unit Tests for Compressed-Domain Processing-in-Memory (CPIM) Engine.
"""

import struct
import unittest

from simulator.algorithms.bdi import BDICompressor
from simulator.algorithms.bfp import BFPCompressor
from simulator.core.pim_engine import CPIMEngine


class TestCPIMEngine(unittest.TestCase):

    def setUp(self):
        self.cpim = CPIMEngine()
        self.bdi = BDICompressor()
        self.bfp = BFPCompressor()

    def test_compressed_domain_vector_add(self):
        base_ptr = 0x00007FFF00001000
        line_a = b''.join(struct.pack('<q', base_ptr + i * 4) for i in range(8))
        line_b = b''.join(struct.pack('<q', 10 + i) for i in range(8))

        res_a = self.bdi.compress(line_a)
        res_b = self.bdi.compress(line_b)

        result = self.cpim.vector_add_compressed_bdi(res_a, res_b)

        self.assertEqual(len(result.result_data), 8)
        self.assertTrue(result.computed_in_dram)
        self.assertGreater(result.energy_saved_pj, 0.0)

    def test_bfp_sum_reduction(self):
        floats = [1.0, 2.0, 3.0, 4.0] + [0.0] * 12
        bfp_res = self.bfp.compress_tensor(floats, dtype="fp16", mantissa_bits=4)

        result = self.cpim.sum_reduction_bfp(bfp_res)

        self.assertEqual(len(result.result_data), 1)
        self.assertAlmostEqual(result.result_data[0], 10.0, delta=0.5)
        self.assertTrue(result.computed_in_dram)


if __name__ == '__main__':
    unittest.main()
