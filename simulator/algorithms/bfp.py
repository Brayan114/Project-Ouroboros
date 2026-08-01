"""
Block-Floating-Point (BFP) Quantization Engine for Project Ouroboros.

Implements Block-Floating-Point (BFP) quantization for tensor activations and LLM KV-caches.
Groups FP16/FP8/FP32 values into blocks of 16 elements sharing a single exponent.
Computes mantissa deltas relative to the block exponent to achieve 4.0x - 8.0x
compression ratio on tensor arrays while maintaining low quantization error.
"""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union, Sequence

BLOCK_SIZE = 16  # Standard BFP block size (16 elements per shared exponent)


@dataclass
class BFPBlock:
    """
    Represents a single Block-Floating-Point (BFP) block of 16 elements sharing a single exponent.
    """
    block_exponent: int
    mantissa_deltas: List[int]
    mantissa_bits: int = 4
    original_values: Optional[List[float]] = None
    reconstructed_values: Optional[List[float]] = None


@dataclass
class BFPResult:
    """
    Encapsulates the output of BFP quantization on a tensor array or byte line.
    """
    original_size: int         # Original size in bytes
    compressed_size: int       # Compressed size in bytes
    compression_ratio: float   # original_size / compressed_size
    num_blocks: int            # Number of 16-element blocks
    mantissa_bits: int         # Bits per mantissa delta (e.g. 2, 4, 8)
    dtype: str                 # 'fp16', 'fp8', 'fp32', or 'float'
    blocks: List[BFPBlock]     # List of compressed blocks
    compressed_bytes: bytes    # Serialized binary payload
    mean_squared_error: float  # Quantization error metric (MSE)
    max_absolute_error: float  # Maximum absolute quantization error

    @property
    def is_compressed(self) -> bool:
        return self.compressed_size < self.original_size


class BFPCompressor:
    """
    Simulates Block-Floating-Point (BFP) quantization for tensor activations and LLM KV-caches.
    
    Groups values into blocks of 16 elements sharing a single exponent E_block, and computes
    mantissa deltas relative to E_block.
    """

    def __init__(self, block_size: int = BLOCK_SIZE, default_mantissa_bits: int = 4):
        self.block_size = block_size
        self.default_mantissa_bits = default_mantissa_bits

    def compress_block(self, elements: Sequence[float], mantissa_bits: Optional[int] = None) -> BFPBlock:
        """
        Compresses up to 16 floating-point values into a single BFPBlock.
        
        1. Shared block exponent E_block = ceil(log2(max(|x_i|))) for non-zero elements.
        2. Mantissa deltas = round((x_i / 2^E_block) * (2^(mantissa_bits-1) - 1)).
        """
        mbits = mantissa_bits if mantissa_bits is not None else self.default_mantissa_bits
        elems = list(elements)
        if len(elems) < self.block_size:
            elems = elems + [0.0] * (self.block_size - len(elems))
        elif len(elems) > self.block_size:
            elems = elems[:self.block_size]

        max_abs = max((abs(x) for x in elems if not (math.isnan(x) or math.isinf(x))), default=0.0)

        if max_abs <= 0.0 or math.isnan(max_abs) or math.isinf(max_abs):
            block_exp = 0
            deltas = [0] * self.block_size
        else:
            try:
                log_val = math.log2(max_abs)
                block_exp = math.ceil(log_val) if not (math.isnan(log_val) or math.isinf(log_val)) else 0
            except Exception:
                block_exp = 0
            block_exp = max(-128, min(127, block_exp))


            scale = 2.0 ** block_exp
            max_quant = (1 << (mbits - 1)) - 1
            min_quant = -max_quant

            deltas = []
            for x in elems:
                norm_val = x / scale if scale > 0 else 0.0
                quant_val = round(norm_val * max_quant)
                quant_val = max(min_quant, min(max_quant, quant_val))
                deltas.append(quant_val)

        block = BFPBlock(
            block_exponent=block_exp,
            mantissa_deltas=deltas,
            mantissa_bits=mbits,
            original_values=elems
        )
        block.reconstructed_values = self.decompress_block(block)
        return block

    def decompress_block(self, block: BFPBlock) -> List[float]:
        """
        Decompresses a BFPBlock into 16 floating-point values.
        x_hat = (delta / max_quant) * 2^block_exponent
        """
        if block.block_exponent == 0 and all(d == 0 for d in block.mantissa_deltas):
            return [0.0] * self.block_size

        scale = 2.0 ** block.block_exponent
        max_quant = (1 << (block.mantissa_bits - 1)) - 1

        if max_quant == 0:
            return [0.0] * self.block_size

        reconstructed = []
        for d in block.mantissa_deltas:
            val = (d / max_quant) * scale
            reconstructed.append(val)
        return reconstructed

    def pack_block(self, block: BFPBlock) -> bytes:
        """
        Packs a BFPBlock into binary payload:
        - 1 byte exponent (int8)
        - Packed mantissa deltas (depending on mantissa_bits)
        """
        header = struct.pack('b', block.block_exponent)
        mbits = block.mantissa_bits
        deltas = block.mantissa_deltas

        if mbits == 4:
            packed_deltas = bytearray()
            for i in range(0, len(deltas), 2):
                d0 = deltas[i] & 0x0F
                d1 = deltas[i + 1] & 0x0F if (i + 1) < len(deltas) else 0
                packed_deltas.append((d0 << 4) | d1)
            return header + bytes(packed_deltas)
        elif mbits == 2:
            packed_deltas = bytearray()
            for i in range(0, len(deltas), 4):
                d0 = deltas[i] & 0x03
                d1 = deltas[i + 1] & 0x03 if (i + 1) < len(deltas) else 0
                d2 = deltas[i + 2] & 0x03 if (i + 2) < len(deltas) else 0
                d3 = deltas[i + 3] & 0x03 if (i + 3) < len(deltas) else 0
                packed_deltas.append((d0 << 6) | (d1 << 4) | (d2 << 2) | d3)
            return header + bytes(packed_deltas)
        elif mbits == 8:
            packed_deltas = bytes(struct.pack('b', d) for d in deltas)
            return header + packed_deltas
        else:
            packed_deltas = bytes(struct.pack('b', d) for d in deltas)
            return header + packed_deltas

    def unpack_block(self, data: bytes, mantissa_bits: int = 4) -> BFPBlock:
        """
        Unpacks a binary payload back into a BFPBlock.
        """
        block_exp = struct.unpack('b', data[:1])[0]
        payload = data[1:]

        deltas: List[int] = []
        if mantissa_bits == 4:
            for b in payload:
                d0 = (b >> 4) & 0x0F
                d1 = b & 0x0F
                d0 = d0 if d0 < 8 else d0 - 16
                d1 = d1 if d1 < 8 else d1 - 16
                deltas.extend([d0, d1])
        elif mantissa_bits == 2:
            for b in payload:
                for shift in (6, 4, 2, 0):
                    d = (b >> shift) & 0x03
                    d = d if d < 2 else d - 4
                    deltas.append(d)
        elif mantissa_bits == 8:
            deltas = list(struct.unpack(f'{len(payload)}b', payload))
        else:
            deltas = list(struct.unpack(f'{len(payload)}b', payload))

        deltas = deltas[:self.block_size]

        block = BFPBlock(
            block_exponent=block_exp,
            mantissa_deltas=deltas,
            mantissa_bits=mantissa_bits
        )
        block.reconstructed_values = self.decompress_block(block)
        return block

    def compress_tensor(
        self,
        values: Sequence[float],
        dtype: str = "fp16",
        mantissa_bits: Optional[int] = None
    ) -> BFPResult:
        """
        Compresses a sequence of floating point values into BFPResult.
        """
        mbits = mantissa_bits if mantissa_bits is not None else self.default_mantissa_bits
        elem_bytes = 2 if dtype == "fp16" else (4 if dtype == "fp32" else 1)
        original_size = len(values) * elem_bytes

        blocks: List[BFPBlock] = []
        packed_chunks: List[bytes] = []
        orig_all: List[float] = []
        recon_all: List[float] = []

        for i in range(0, len(values), self.block_size):
            chunk = values[i:i + self.block_size]
            block = self.compress_block(chunk, mantissa_bits=mbits)
            blocks.append(block)
            packed_chunks.append(self.pack_block(block))
            orig_all.extend(block.original_values or [])
            recon_all.extend(block.reconstructed_values or [])

        compressed_bytes = b''.join(packed_chunks)
        compressed_size = len(compressed_bytes)
        ratio = original_size / compressed_size if compressed_size > 0 else 1.0

        mse = sum((o - r) ** 2 for o, r in zip(orig_all, recon_all)) / len(orig_all) if orig_all else 0.0
        mae = max((abs(o - r) for o, r in zip(orig_all, recon_all)), default=0.0)

        return BFPResult(
            original_size=original_size,
            compressed_size=compressed_size,
            compression_ratio=ratio,
            num_blocks=len(blocks),
            mantissa_bits=mbits,
            dtype=dtype,
            blocks=blocks,
            compressed_bytes=compressed_bytes,
            mean_squared_error=mse,
            max_absolute_error=mae
        )

    def decompress_tensor(self, result: BFPResult) -> List[float]:
        """
        Decompresses a BFPResult back into a list of floats.
        """
        reconstructed: List[float] = []
        for block in result.blocks:
            reconstructed.extend(self.decompress_block(block))
        return reconstructed

    def compress(
        self,
        data: Union[bytes, Sequence[float]],
        dtype: str = "fp16",
        mantissa_bits: Optional[int] = None
    ) -> BFPResult:
        """
        Byte/sequence entry point for BFP compression.
        """
        if isinstance(data, bytes):
            floats = self._bytes_to_floats(data, dtype)
            res = self.compress_tensor(floats, dtype=dtype, mantissa_bits=mantissa_bits)
            res.original_size = len(data)
            res.compression_ratio = res.original_size / res.compressed_size if res.compressed_size > 0 else 1.0
            return res
        else:
            return self.compress_tensor(data, dtype=dtype, mantissa_bits=mantissa_bits)

    def decompress(self, result: BFPResult) -> Union[bytes, List[float]]:
        """
        Decompresses a BFPResult back to original format (bytes if result derived from bytes).
        """
        floats = self.decompress_tensor(result)
        return self._floats_to_bytes(floats, result.dtype)[:result.original_size]

    def _bytes_to_floats(self, data: bytes, dtype: str) -> List[float]:
        raw_floats: List[float] = []
        if dtype == "fp16":
            num_elems = len(data) // 2
            try:
                raw_floats = list(struct.unpack(f'<{num_elems}e', data[:num_elems * 2]))
            except Exception:
                ints = struct.unpack(f'<{num_elems}h', data[:num_elems * 2])
                raw_floats = [float(v) for v in ints]
        elif dtype == "fp32":
            num_elems = len(data) // 4
            raw_floats = list(struct.unpack(f'<{num_elems}f', data[:num_elems * 4]))
        elif dtype in ("fp8", "int8"):
            raw_floats = [float(b) for b in struct.unpack(f'{len(data)}b', data)]
        else:
            num_elems = len(data) // 2
            raw_floats = [float(v) for v in struct.unpack(f'<{num_elems}h', data[:num_elems * 2])]

        return [0.0 if (math.isnan(v) or math.isinf(v)) else v for v in raw_floats]


    def _floats_to_bytes(self, floats: List[float], dtype: str) -> bytes:
        if dtype == "fp16":
            try:
                return b''.join(struct.pack('<e', f) for f in floats)
            except Exception:
                return b''.join(struct.pack('<h', int(f)) for f in floats)
        elif dtype == "fp32":
            return b''.join(struct.pack('<f', f) for f in floats)
        elif dtype in ("fp8", "int8"):
            return b''.join(struct.pack('b', max(-128, min(127, int(f)))) for f in floats)
        elif dtype == "int16":
            return b''.join(struct.pack('<h', max(-32768, min(32767, int(f)))) for f in floats)
        else:
            return b''.join(struct.pack('<e', f) for f in floats)
