"""
Unit Tests for Ouroboros Central Memory Controller and Hardware Indirection Cache (HIT).
"""

import os
import struct
import unittest

from simulator.core.memory_controller import OuroborosMemoryController


class TestOuroborosMemoryController(unittest.TestCase):

    def setUp(self):
        self.mc = OuroborosMemoryController(dram_capacity_bytes=1024 * 1024)

    def test_zero_line_direct_embedding(self):
        vaddr = 0x1000
        zero_data = b'\x00' * 64

        entry = self.mc.write_line(vaddr, zero_data)
        self.assertTrue(entry.is_embedded)
        self.assertEqual(entry.compressed_size, 1)
        self.assertEqual(len(entry.physical_sectors), 0)  # 0 DRAM sectors allocated!

        # Read back and verify losslessness
        read_data = self.mc.read_line(vaddr)
        self.assertEqual(read_data, zero_data)

    def test_pointer_array_compression(self):
        vaddr = 0x2000
        base_ptr = 0x00007FFF00001000
        ptrs = [base_ptr + i * 8 for i in range(8)]
        ptr_data = b''.join(struct.pack('<q', p) for p in ptrs)

        entry = self.mc.write_line(vaddr, ptr_data)
        self.assertTrue(entry.is_compressed)
        self.assertEqual(entry.pattern, "B8D1")
        self.assertTrue(entry.is_embedded)  # 16B payload <= 16B max embedded

        read_data = self.mc.read_line(vaddr)
        self.assertEqual(read_data, ptr_data)

    def test_high_entropy_bypass(self):
        vaddr = 0x3000
        high_ent_data = os.urandom(64)

        entry = self.mc.write_line(vaddr, high_ent_data)
        self.assertFalse(entry.is_compressed)
        self.assertEqual(entry.pattern, "Uncompressed")
        self.assertFalse(entry.is_embedded)
        self.assertEqual(len(entry.physical_sectors), 4)  # 64B / 16B = 4 sectors

        read_data = self.mc.read_line(vaddr)
        self.assertEqual(read_data, high_ent_data)

    def test_memory_statistics_tracking(self):
        # Write 1 zero line (1B alloc) + 1 pointer line (16B alloc) + 1 random line (64B alloc)
        self.mc.write_line(0x1000, b'\x00' * 64)

        base_ptr = 0x00007FFF00001000
        ptr_data = b''.join(struct.pack('<q', base_ptr + i * 8) for i in range(8))
        self.mc.write_line(0x2000, ptr_data)

        self.mc.write_line(0x3000, os.urandom(64))

        stats = self.mc.stats
        self.assertEqual(stats.total_writes, 3)
        self.assertEqual(stats.virtual_bytes_written, 192)  # 3 * 64B
        self.assertLess(stats.physical_bytes_allocated, 192)
        self.assertGreater(stats.effective_compression_ratio, 2.0)
        self.assertGreater(stats.capacity_saved_percent, 50.0)
        self.assertGreater(stats.energy_saved_pj, 0.0)


if __name__ == '__main__':
    unittest.main()
