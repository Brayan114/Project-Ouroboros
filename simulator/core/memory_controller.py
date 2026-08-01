"""
Ouroboros Memory Controller (Central Controller Unit).

Intercepts virtual memory read and write requests, executes real-time adaptive
entropy estimation, dispatches compression tasks to BDI/FPC, updates the
Hardware Indirection Cache (HIT), and tracks energy/capacity metrics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from simulator.algorithms.bdi import BDICompressor, BDIResult, CACHE_LINE_SIZE
from simulator.algorithms.entropy import is_high_entropy
from simulator.core.indirection_table import HardwareIndirectionCache, HITEntry

# Energy constants (in picojoules pJ)
OFF_CHIP_DRAM_READ_PJ_PER_BYTE = 25.0  # ~1600 pJ for 64B line
ON_CHIP_HIT_LOOKUP_PJ = 0.5            # 0.5 pJ per HIT SRAM lookup


@dataclass
class MemoryStats:
    total_writes: int = 0
    total_reads: int = 0
    virtual_bytes_written: int = 0
    physical_bytes_allocated: int = 0
    bypassed_writes: int = 0
    direct_embedded_writes: int = 0
    bdi_compressed_writes: int = 0
    energy_saved_pj: float = 0.0

    @property
    def effective_compression_ratio(self) -> float:
        if self.physical_bytes_allocated == 0:
            return 1.0
        return self.virtual_bytes_written / self.physical_bytes_allocated

    @property
    def capacity_saved_percent(self) -> float:
        if self.virtual_bytes_written == 0:
            return 0.0
        saved = self.virtual_bytes_written - self.physical_bytes_allocated
        return (saved / self.virtual_bytes_written) * 100.0


class OuroborosMemoryController:
    """
    Central Ouroboros Memory Controller simulating inline hardware memory compression,
    HIT translation, and energy reduction.
    """

    def __init__(self, dram_capacity_bytes: int = 1024 * 1024 * 1024):
        self.hit_cache = HardwareIndirectionCache(total_dram_bytes=dram_capacity_bytes)
        self.bdi = BDICompressor()
        self.stats = MemoryStats()
        # Simulated DRAM physical storage backing store
        self.dram_sector_storage: Dict[int, bytes] = {}

    def write_line(self, virtual_address: int, data: bytes) -> HITEntry:
        """
        Intercepts a 64-byte write request:
        1. Checks entropy (bypasses if high entropy).
        2. Compresses using BDI engine.
        3. Updates HIT indirection table (using direct embedding if <= 16B).
        4. Writes payload to physical DRAM sectors or HIT entry.
        """
        if len(data) != CACHE_LINE_SIZE:
            data = data.ljust(CACHE_LINE_SIZE, b'\x00')[:CACHE_LINE_SIZE]

        self.stats.total_writes += 1
        self.stats.virtual_bytes_written += CACHE_LINE_SIZE

        # 1. Entropy Check
        if is_high_entropy(data):
            self.stats.bypassed_writes += 1
            entry = self.hit_cache.allocate_and_map(
                virtual_address=virtual_address,
                pattern="Uncompressed",
                compressed_size=CACHE_LINE_SIZE,
                payload=data,
                base_values=[],
                deltas=[]
            )
            self._write_to_dram_sectors(entry, data)
            self.stats.physical_bytes_allocated += CACHE_LINE_SIZE
            return entry

        # 2. BDI Compression
        bdi_res: BDIResult = self.bdi.compress(data)

        if bdi_res.is_compressed:
            self.stats.bdi_compressed_writes += 1

        compressed_sz = bdi_res.compressed_size

        # 3. HIT Allocation & Direct Embedding
        entry = self.hit_cache.allocate_and_map(
            virtual_address=virtual_address,
            pattern=bdi_res.pattern,
            compressed_size=compressed_sz,
            payload=bdi_res.compressed_bytes,
            base_values=bdi_res.base_values,
            deltas=bdi_res.deltas
        )

        if entry.is_embedded:
            self.stats.direct_embedded_writes += 1
            # 0 physical DRAM sectors used!
            self.stats.physical_bytes_allocated += compressed_sz
            # Energy saved by eliminating 64B DRAM write transfer
            saved_bytes = CACHE_LINE_SIZE - compressed_sz
            self.stats.energy_saved_pj += saved_bytes * OFF_CHIP_DRAM_READ_PJ_PER_BYTE
        else:
            self._write_to_dram_sectors(entry, bdi_res.compressed_bytes)
            actual_alloc = len(entry.physical_sectors) * 16
            self.stats.physical_bytes_allocated += actual_alloc
            saved_bytes = CACHE_LINE_SIZE - actual_alloc
            if saved_bytes > 0:
                self.stats.energy_saved_pj += saved_bytes * OFF_CHIP_DRAM_READ_PJ_PER_BYTE

        return entry

    def read_line(self, virtual_address: int) -> Optional[bytes]:
        """
        Intercepts a read request:
        1. Performs sub-nanosecond HIT lookup.
        2. If embedded: returns decompressed payload directly from HIT entry.
        3. Else: fetches physical DRAM sectors and decompresses.
        """
        self.stats.total_reads += 1
        entry = self.hit_cache.lookup(virtual_address)
        if not entry:
            return None

        # 1. Direct Embedded Read (0 DRAM sector reads!)
        if entry.is_embedded:
            bdi_res = BDIResult(
                pattern=entry.pattern,
                original_size=CACHE_LINE_SIZE,
                compressed_size=entry.compressed_size,
                compression_ratio=CACHE_LINE_SIZE / entry.compressed_size,
                compressed_bytes=entry.embedded_payload,
                base_values=entry.base_values,
                deltas=entry.deltas
            )
            return self.bdi.decompress(bdi_res)

        # 2. Physical DRAM Sector Fetch
        compressed_payload = self._read_from_dram_sectors(entry)

        bdi_res = BDIResult(
            pattern=entry.pattern,
            original_size=CACHE_LINE_SIZE,
            compressed_size=entry.compressed_size,
            compression_ratio=CACHE_LINE_SIZE / entry.compressed_size,
            compressed_bytes=compressed_payload,
            base_values=entry.base_values,
            deltas=entry.deltas
        )
        return self.bdi.decompress(bdi_res)

    def _write_to_dram_sectors(self, entry: HITEntry, payload: bytes):
        for i, sec_idx in enumerate(entry.physical_sectors):
            chunk = payload[i * 16:(i + 1) * 16]
            self.dram_sector_storage[sec_idx] = chunk.ljust(16, b'\x00')

    def _read_from_dram_sectors(self, entry: HITEntry) -> bytes:
        chunks = [self.dram_sector_storage.get(sec_idx, b'\x00' * 16) for sec_idx in entry.physical_sectors]
        full_payload = b''.join(chunks)
        return full_payload[:entry.compressed_size]
