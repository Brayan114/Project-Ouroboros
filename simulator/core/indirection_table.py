"""
Hardware Indirection Cache (HIT) for Project Ouroboros.

Implements the low-latency hardware indirection table that maps Virtual Cache Line
Addresses to variable-sized physical DRAM sectors (16-byte granularity).

Includes Direct Payload Embedding:
If a compressed cache line is <= 16 bytes (e.g. Zer, Rep, B8D1), the payload is stored
DIRECTLY inside the 16-byte HIT entry, eliminating physical DRAM sector allocations
and saving 1 memory lookup access!
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

SECTOR_SIZE_BYTES = 16
DIRECT_EMBEDDING_MAX_BYTES = 16


@dataclass
class HITEntry:
    virtual_address: int
    is_compressed: bool
    is_embedded: bool
    compressed_size: int
    pattern: str
    embedded_payload: bytes = b''
    physical_sectors: List[int] = field(default_factory=list)
    base_values: List[int] = field(default_factory=list)
    deltas: List[int] = field(default_factory=list)


class HardwareIndirectionCache:
    """
    Simulates the Hardware Indirection Cache (HIT) memory translation layer.
    Manages physical DRAM sector allocations and sub-nanosecond address translation.
    """

    def __init__(self, total_dram_bytes: int = 1024 * 1024 * 1024):  # 1 GB default
        self.total_dram_bytes = total_dram_bytes
        self.total_sectors = total_dram_bytes // SECTOR_SIZE_BYTES
        self.table: Dict[int, HITEntry] = {}
        self.free_sectors: Set[int] = set(range(self.total_sectors))
        self.allocated_sectors_count = 0

    def lookup(self, virtual_address: int) -> Optional[HITEntry]:
        """
        Sub-nanosecond hardware lookup of a virtual cache line address.
        """
        return self.table.get(virtual_address)

    def allocate_and_map(
        self,
        virtual_address: int,
        pattern: str,
        compressed_size: int,
        payload: bytes,
        base_values: List[int],
        deltas: List[int]
    ) -> HITEntry:
        """
        Maps a virtual address to physical DRAM sectors or direct embedded payload.
        """
        # Unmap existing entry if overwriting
        if virtual_address in self.table:
            self.unmap(virtual_address)

        # Check for Direct Payload Embedding (<= 16 bytes)
        if compressed_size <= DIRECT_EMBEDDING_MAX_BYTES:
            entry = HITEntry(
                virtual_address=virtual_address,
                is_compressed=(pattern != "Uncompressed"),
                is_embedded=True,
                compressed_size=compressed_size,
                pattern=pattern,
                embedded_payload=payload,
                physical_sectors=[],
                base_values=base_values,
                deltas=deltas
            )
            self.table[virtual_address] = entry
            return entry

        # Standard physical sector allocation (16B granularity)
        needed_sectors = (compressed_size + SECTOR_SIZE_BYTES - 1) // SECTOR_SIZE_BYTES
        if len(self.free_sectors) < needed_sectors:
            raise MemoryError("DRAM Physical Sector Pool Exhausted!")

        allocated: List[int] = []
        for _ in range(needed_sectors):
            sec = self.free_sectors.pop()
            allocated.append(sec)

        self.allocated_sectors_count += needed_sectors

        entry = HITEntry(
            virtual_address=virtual_address,
            is_compressed=(pattern != "Uncompressed"),
            is_embedded=False,
            compressed_size=compressed_size,
            pattern=pattern,
            embedded_payload=b'',
            physical_sectors=allocated,
            base_values=base_values,
            deltas=deltas
        )
        self.table[virtual_address] = entry
        return entry

    def unmap(self, virtual_address: int) -> bool:
        """
        Frees physical sectors allocated to a virtual address.
        """
        if virtual_address not in self.table:
            return False

        entry = self.table.pop(virtual_address)
        if not entry.is_embedded:
            for sec in entry.physical_sectors:
                self.free_sectors.add(sec)
            self.allocated_sectors_count -= len(entry.physical_sectors)
        return True

    @property
    def used_physical_bytes(self) -> int:
        return self.allocated_sectors_count * SECTOR_SIZE_BYTES

    @property
    def direct_embedded_entries_count(self) -> int:
        return sum(1 for entry in self.table.values() if entry.is_embedded)
