# Ramulator 2.1 Hardware Simulation Module for Project Ouroboros
from simulator.hardware.ramulator_config import (
    RamulatorConfig,
    DRAMProfile,
    DDR5_6400_CONFIG,
    HBM3_CONFIG,
    get_profile_config,
)
from simulator.hardware.ramulator_runner import (
    RamulatorHardwareSimulator,
    HardwareSimulationResult,
    run_hardware_benchmarks,
)

__all__ = [
    "RamulatorConfig",
    "DRAMProfile",
    "DDR5_6400_CONFIG",
    "HBM3_CONFIG",
    "get_profile_config",
    "RamulatorHardwareSimulator",
    "HardwareSimulationResult",
    "run_hardware_benchmarks",
]
