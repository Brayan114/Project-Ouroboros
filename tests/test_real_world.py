"""
Unit Tests for Real-World PyTorch LLM Integration (ouroboros-llm).
"""

import unittest
from simulator.real_world.ouroboros_llm import OuroborosPyTorchKVCache


class TestOuroborosLLM(unittest.TestCase):

    def test_kv_cache_compression(self):
        keys = [[1.0, 0.5, -0.25, 0.75] * 4 for _ in range(16)]
        vals = [[-0.5, 0.2, 0.8, -0.1] * 4 for _ in range(16)]

        cache = OuroborosPyTorchKVCache(mantissa_bits=4)
        orig_bytes, comp_bytes, mult = cache.compress_key_value_tensors(keys, vals)

        self.assertGreater(orig_bytes, comp_bytes)
        self.assertGreaterEqual(mult, 3.0)

        recon_k, recon_v = cache.decompress_key_value_tensors()
        self.assertEqual(len(recon_k), 16 * 16)
        self.assertEqual(len(recon_v), 16 * 16)


if __name__ == '__main__':
    unittest.main()
