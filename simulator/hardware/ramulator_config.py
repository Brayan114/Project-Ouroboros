"""
Ramulator 2.1 Hardware Simulation Configuration Profiles.

Defines DRAM architecture specifications, timing parameters (in clock cycles),
controller queue latencies, and physical bus power profiles for DDR5-6400 and HBM3.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Union


class DRAMProfile(Enum):
    DDR5_6400 = "DDR5-6400"
    HBM3 = "HBM3"


@dataclass
class DRAMTimingSpec:
    tCK: float           # Clock period in nanoseconds
    tCL: int             # CAS Latency (cycles)
    tRCD: int            # RAS to CAS Delay (cycles)
    tRP: int             # Row Precharge Delay (cycles)
    tRAS: int            # Row Active Time (cycles)
    tRC: int             # Row Cycle Time (cycles)
    tWR: int             # Write Recovery Time (cycles)
    tCCD_S: int          # CAS to CAS Delay Short (cycles)
    tCCD_L: int          # CAS to CAS Delay Long / Bank Group Conflict (cycles)
    tRRD_S: int          # Row Active to Row Active Short (cycles)
    tRRD_L: int          # Row Active to Row Active Long (cycles)

    @property
    def tCL_ns(self) -> float:
        return self.tCL * self.tCK

    @property
    def tRCD_ns(self) -> float:
        return self.tRCD * self.tCK

    @property
    def tRP_ns(self) -> float:
        return self.tRP * self.tCK


@dataclass
class ControllerQueueSpec:
    read_queue_size: int = 64
    write_queue_size: int = 64
    base_queue_latency_cycles: int = 6
    congestion_threshold: int = 32
    congestion_penalty_cycles: int = 2


@dataclass
class PhysicalBusPowerSpec:
    interface_type: str                   # "PCB_Trace" or "2.5D_Silicon_Interposer"
    bus_capacitance_pf: float             # Trace capacitance in picofarads
    vdd_volts: float                      # Operating voltage
    active_bus_energy_pj_per_byte: float  # Dynamic energy consumption (pJ per byte transferred)
    static_power_mw: float                # Idle static background power (mW)


@dataclass
class RamulatorConfig:
    profile_name: str
    dram_type: str
    channels: int
    ranks_per_channel: int
    bank_groups: int
    banks_per_group: int
    rows_per_bank: int
    cols_per_row: int
    timing: DRAMTimingSpec
    queue: ControllerQueueSpec
    power: PhysicalBusPowerSpec
    extra_params: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_banks(self) -> int:
        return self.channels * self.ranks_per_channel * self.bank_groups * self.banks_per_group


# Configuration Specification for DDR5-6400 (3200 MHz Clock, 0.3125 ns tCK)
DDR5_6400_CONFIG = RamulatorConfig(
    profile_name="DDR5-6400",
    dram_type="DDR5",
    channels=2,
    ranks_per_channel=1,
    bank_groups=8,
    banks_per_group=4,
    rows_per_bank=65536,
    cols_per_row=1024,
    timing=DRAMTimingSpec(
        tCK=0.3125,
        tCL=45,
        tRCD=45,
        tRP=45,
        tRAS=102,
        tRC=147,
        tWR=96,
        tCCD_S=8,
        tCCD_L=16,
        tRRD_S=8,
        tRRD_L=12,
    ),
    queue=ControllerQueueSpec(
        read_queue_size=64,
        write_queue_size=64,
        base_queue_latency_cycles=6,
        congestion_threshold=32,
        congestion_penalty_cycles=2,
    ),
    power=PhysicalBusPowerSpec(
        interface_type="PCB_Trace",
        bus_capacitance_pf=12.0,
        vdd_volts=1.1,
        active_bus_energy_pj_per_byte=25.0,  # ~1600 pJ for 64B transfer
        static_power_mw=450.0,
    ),
)


# Configuration Specification for HBM3 (3200 MHz Clock, 0.3125 ns tCK, 16 Pseudo-Channels)
HBM3_CONFIG = RamulatorConfig(
    profile_name="HBM3",
    dram_type="HBM3",
    channels=16,
    ranks_per_channel=1,
    bank_groups=4,
    banks_per_group=4,
    rows_per_bank=32768,
    cols_per_row=64,
    timing=DRAMTimingSpec(
        tCK=0.3125,
        tCL=40,
        tRCD=40,
        tRP=40,
        tRAS=90,
        tRC=130,
        tWR=80,
        tCCD_S=4,
        tCCD_L=8,
        tRRD_S=6,
        tRRD_L=10,
    ),
    queue=ControllerQueueSpec(
        read_queue_size=32,
        write_queue_size=32,
        base_queue_latency_cycles=4,
        congestion_threshold=16,
        congestion_penalty_cycles=1,
    ),
    power=PhysicalBusPowerSpec(
        interface_type="2.5D_Silicon_Interposer",
        bus_capacitance_pf=0.8,
        vdd_volts=0.4,
        active_bus_energy_pj_per_byte=4.0,   # ~256 pJ for 64B transfer (~6x lower than DDR5 PCB)
        static_power_mw=180.0,
    ),
)


def get_profile_config(profile: Union[DRAMProfile, str]) -> RamulatorConfig:
    if isinstance(profile, str):
        profile = DRAMProfile(profile)
    if profile == DRAMProfile.DDR5_6400:
        return DDR5_6400_CONFIG
    elif profile == DRAMProfile.HBM3:
        return HBM3_CONFIG
    else:
        raise ValueError(f"Unsupported DRAM profile: {profile}")
