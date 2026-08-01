"""
Compressed-Domain Processing-in-Memory (CPIM) Execution Engine.

Executes SIMD vector additions and sum reductions DIRECTLY on compressed BDI/BFP
payloads within DRAM bank controllers without prior decompression, maximizing memory
bandwidth and eliminating bus transfer energy penalties.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import List, Tuple, Optional

from simulator.algorithms.bdi import BDICompressor, BDIResult, CACHE_LINE_SIZE
from simulator.algorithms.bfp import BFPCompressor, BFPBlock, BFPResult


@dataclass
class CPIMResult:
    operation: str
    result_data: List[float]
    cycles_saved: int
    energy_saved_pj: float
    computed_in_dram: bool = True


class CPIMEngine:
    """
    Simulates Compressed-Domain Processing-in-Memory (CPIM) ALU hardware units.
    """

    def __init__(self, pcb_energy_pj_per_byte: float = 25.0):
        self.bdi = BDICompressor()
        self.bfp = BFPCompressor()
        self.pcb_energy_pj_per_byte = pcb_energy_pj_per_byte

    def vector_add_compressed_bdi(self, bdi_a: BDIResult, bdi_b: BDIResult) -> CPIMResult:
        """
        Executes vector addition directly on two compressed BDI lines:
        If both lines share the same BDI pattern (e.g. B8D1), CPIM adds:
        1. Base_A + Base_B -> New Base
        2. Delta_A[i] + Delta_B[i] -> New Deltas
        Zero DRAM decompression required!
        """
        if bdi_a.pattern == bdi_b.pattern and bdi_a.is_compressed and bdi_b.is_compressed:
            # Direct compressed-domain addition
            new_bases = [bdi_a.base_values[i] + bdi_b.base_values[i] for i in range(len(bdi_a.base_values))]
            new_deltas = [bdi_a.deltas[i] + bdi_b.deltas[i] for i in range(len(bdi_a.deltas))]

            reconstructed = [new_bases[0] + d for d in new_deltas]
            saved_energy = (128 - (bdi_a.compressed_size + bdi_b.compressed_size)) * self.pcb_energy_pj_per_byte

            return CPIMResult(
                operation="vector_add_bdi_compressed_domain",
                result_data=[float(x) for x in reconstructed],
                cycles_saved=12,
                energy_saved_pj=max(0.0, saved_energy),
                computed_in_dram=True
            )

        # Fallback: Decompress and compute in-memory
        data_a = self.bdi.decompress(bdi_a)
        data_b = self.bdi.decompress(bdi_b)
        words_a = struct.unpack('<8q', data_a)
        words_b = struct.unpack('<8q', data_b)
        res = [float(a + b) for a, b in zip(words_a, words_b)]

        return CPIMResult(
            operation="vector_add_in_memory",
            result_data=res,
            cycles_saved=6,
            energy_saved_pj=64 * self.pcb_energy_pj_per_byte,
            computed_in_dram=True
        )

    def sum_reduction_bfp(self, bfp_result: BFPResult) -> CPIMResult:
        """
        Executes sum reduction directly on BFP quantized blocks:
        Sum = (sum(mantissa_deltas) / max_quant) * 2^E_block
        """
        total_sum = 0.0
        for block in bfp_result.blocks:
            if block.block_exponent == 0 and all(d == 0 for d in block.mantissa_deltas):
                continue
            scale = 2.0 ** block.block_exponent
            max_quant = (1 << (block.mantissa_bits - 1)) - 1
            if max_quant > 0:
                block_sum_delta = sum(block.mantissa_deltas)
                total_sum += (block_sum_delta / max_quant) * scale

        saved_energy = (bfp_result.original_size - bfp_result.compressed_size) * self.pcb_energy_pj_per_byte

        return CPIMResult(
            operation="sum_reduction_bfp_compressed_domain",
            result_data=[total_sum],
            cycles_saved=16,
            energy_saved_pj=max(0.0, saved_energy),
            computed_in_dram=True
        )
