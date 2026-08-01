"""
Unit Tests for Ramulator 2.1 Hardware Simulator and Profiles.
"""

import unittest
from simulator.core.memory_controller import OuroborosMemoryController
from simulator.hardware.ramulator_config import (
    DDR5_6400_CONFIG,
    HBM3_CONFIG,
    get_profile_config,
    DRAMProfile,
)
from simulator.hardware.ramulator_runner import (
    RamulatorHardwareSimulator,
    MemoryAddressMapping,
)


class TestRamulatorHardwareSimulator(unittest.TestCase):

    def test_profile_loading(self):
        ddr5 = get_profile_config(DRAMProfile.DDR5_6400)
        hbm3 = get_profile_config("HBM3")

        self.assertEqual(ddr5.dram_type, "DDR5")
        self.assertEqual(ddr5.timing.tCK, 0.3125)
        self.assertEqual(ddr5.power.interface_type, "PCB_Trace")

        self.assertEqual(hbm3.dram_type, "HBM3")
        self.assertEqual(hbm3.channels, 16)
        self.assertEqual(hbm3.power.interface_type, "2.5D_Silicon_Interposer")

    def test_address_decoding(self):
        sim = RamulatorHardwareSimulator(DDR5_6400_CONFIG)
        addr = 0x00007FFF00001000
        mapping = sim.decode_address(addr)

        self.assertIsInstance(mapping, MemoryAddressMapping)
        self.assertGreaterEqual(mapping.channel, 0)
        self.assertLess(mapping.channel, DDR5_6400_CONFIG.channels)

    def test_embedded_hit_bypass_latency(self):
        sim = RamulatorHardwareSimulator(DDR5_6400_CONFIG)
        # Embedded payload (is_embedded=True, 1B compressed)
        cycles, energy = sim.simulate_request(address=0x1000, is_embedded=True, compressed_bytes=1)

        self.assertEqual(cycles, 1)  # 1 cycle SRAM HIT latency
        self.assertEqual(energy, 0.0) # 0 pJ DRAM bus transfer energy
        self.assertEqual(sim.total_embedded_requests, 1)

    def test_bank_conflict_latency_penalty(self):
        sim = RamulatorHardwareSimulator(DDR5_6400_CONFIG)

        # Access 1: Row Miss on closed bank
        cycles1, _ = sim.simulate_request(address=0x1000, is_embedded=False, compressed_bytes=64)
        # Access 2: Same address -> Row Hit
        cycles2, _ = sim.simulate_request(address=0x1000, is_embedded=False, compressed_bytes=64)

        self.assertLess(cycles2, cycles1)  # Row Hit must be faster than Row Miss!

    def test_trace_simulation_execution(self):
        mc = OuroborosMemoryController()
        # Write zero line
        mc.write_line(0x1000, b'\x00' * 64)

        sim = RamulatorHardwareSimulator(HBM3_CONFIG)
        result = sim.run_ouroboros_trace(
            workload_name="TestWorkload", controller=mc, virtual_addresses=[0x1000]
        )

        self.assertEqual(result.profile_name, "HBM3")
        self.assertEqual(result.total_requests, 1)
        self.assertEqual(result.embedded_bypass_requests, 1)
        self.assertGreater(result.bus_energy_saved_pj, 0.0)


if __name__ == '__main__':
    unittest.main()
