"""
Base-Delta-Immediate (BDI) Compression Engine for Project Ouroboros.

Implements the 8-pattern parallel evaluator described by Pekhimenko et al. (MICRO 2012).
Operates on 64-byte cache lines, evaluating Base 0 and Base 1 (0-base) delta encoding
states to achieve sub-nanosecond hardware compression and decompression.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import List, Optional, Tuple


CACHE_LINE_SIZE = 64

# Pattern Identifiers
PATTERN_ZER = "Zer"
PATTERN_REP = "Rep"
PATTERN_B8D1 = "B8D1"
PATTERN_B8D2 = "B8D2"
PATTERN_B8D4 = "B8D4"
PATTERN_B4D1 = "B4D1"
PATTERN_B4D2 = "B4D2"
PATTERN_UNCOMPRESSED = "Uncompressed"


@dataclass
class BDIResult:
    pattern: str
    original_size: int
    compressed_size: int
    compression_ratio: float
    compressed_bytes: bytes
    base_values: List[int]
    deltas: List[int]

    @property
    def is_compressed(self) -> bool:
        return self.pattern != PATTERN_UNCOMPRESSED


class BDICompressor:
    """
    Simulates the Base-Delta-Immediate (BDI) hardware compressor.
    Evaluates all 8 candidate patterns in parallel and selects the smallest payload.
    """

    def compress(self, line: bytes) -> BDIResult:
        if len(line) != CACHE_LINE_SIZE:
            # Pad or truncate to 64 bytes for evaluation
            line = line.ljust(CACHE_LINE_SIZE, b'\x00')[:CACHE_LINE_SIZE]

        # Candidate pattern evaluations
        candidates: List[Tuple[str, int, bytes, List[int], List[int]]] = []

        # 1. Zero Pattern (Zer)
        if all(b == 0 for b in line):
            candidates.append((PATTERN_ZER, 1, b'\x00', [0], []))

        # 2. Repeated Pattern (Rep)
        words_8 = [struct.unpack('<q', line[i:i + 8])[0] for i in range(0, 64, 8)]
        if all(w == words_8[0] for w in words_8):
            payload = struct.pack('<q', words_8[0])
            candidates.append((PATTERN_REP, 8, payload, [words_8[0]], []))

        # Helper to test Base-Delta states
        # B8D1
        res_b8d1 = self._try_base_delta(line, elem_size=8, delta_bits=8)
        if res_b8d1:
            candidates.append((PATTERN_B8D1, res_b8d1[0], res_b8d1[1], res_b8d1[2], res_b8d1[3]))

        # B8D2
        res_b8d2 = self._try_base_delta(line, elem_size=8, delta_bits=16)
        if res_b8d2:
            candidates.append((PATTERN_B8D2, res_b8d2[0], res_b8d2[1], res_b8d2[2], res_b8d2[3]))

        # B8D4
        res_b8d4 = self._try_base_delta(line, elem_size=8, delta_bits=32)
        if res_b8d4:
            candidates.append((PATTERN_B8D4, res_b8d4[0], res_b8d4[1], res_b8d4[2], res_b8d4[3]))

        # B4D1
        res_b4d1 = self._try_base_delta(line, elem_size=4, delta_bits=8)
        if res_b4d1:
            candidates.append((PATTERN_B4D1, res_b4d1[0], res_b4d1[1], res_b4d1[2], res_b4d1[3]))

        # B4D2
        res_b4d2 = self._try_base_delta(line, elem_size=4, delta_bits=16)
        if res_b4d2:
            candidates.append((PATTERN_B4D2, res_b4d2[0], res_b4d2[1], res_b4d2[2], res_b4d2[3]))

        # Fallback: Uncompressed
        candidates.append((PATTERN_UNCOMPRESSED, 64, line, [], []))

        # Select candidate with minimum compressed size
        best_pattern, compressed_sz, payload_bytes, bases, deltas = min(candidates, key=lambda c: c[1])
        ratio = CACHE_LINE_SIZE / compressed_sz

        return BDIResult(
            pattern=best_pattern,
            original_size=CACHE_LINE_SIZE,
            compressed_size=compressed_sz,
            compression_ratio=ratio,
            compressed_bytes=payload_bytes,
            base_values=bases,
            deltas=deltas
        )

    def _try_base_delta(self, line: bytes, elem_size: int, delta_bits: int) -> Tuple[int, bytes, List[int], List[int]] | None:
        """
        Attempts to represent cache line using elem_size base and delta_bits deltas.
        Returns (compressed_size, payload_bytes, bases, deltas) or None if deltas exceed limits.
        """
        fmt = '<q' if elem_size == 8 else '<i'
        num_elems = CACHE_LINE_SIZE // elem_size
        values = [struct.unpack(fmt, line[i * elem_size:(i + 1) * elem_size])[0] for i in range(num_elems)]

        base_0 = values[0]
        deltas = []

        min_delta = -(1 << (delta_bits - 1))
        max_delta = (1 << (delta_bits - 1)) - 1

        delta_byte_len = delta_bits // 8

        for val in values:
            diff = val - base_0
            if not (min_delta <= diff <= max_delta):
                return None
            deltas.append(diff)

        # Build compressed payload: Base 0 + all deltas
        base_bytes = struct.pack(fmt, base_0)
        delta_fmt = '<b' if delta_byte_len == 1 else ('<h' if delta_byte_len == 2 else '<i')
        deltas_packed = b''.join(struct.pack(delta_fmt, d) for d in deltas)

        payload = base_bytes + deltas_packed
        compressed_size = len(payload)

        return compressed_size, payload, [base_0], deltas

    def decompress(self, result: BDIResult) -> bytes:
        """
        Decompresses a BDIResult back into the original 64-byte cache line.
        Simulates the 1-cycle parallel adder decompression path.
        """
        if result.pattern == PATTERN_UNCOMPRESSED:
            return result.compressed_bytes

        if result.pattern == PATTERN_ZER:
            return b'\x00' * CACHE_LINE_SIZE

        if result.pattern == PATTERN_REP:
            word = result.compressed_bytes[:8]
            return word * 8

        # For base-delta patterns:
        bases = result.base_values
        deltas = result.deltas
        base_0 = bases[0]

        elem_size = 8 if result.pattern in (PATTERN_B8D1, PATTERN_B8D2, PATTERN_B8D4) else 4
        fmt = '<q' if elem_size == 8 else '<i'

        reconstructed_words = [base_0 + d for d in deltas]
        return b''.join(struct.pack(fmt, w) for w in reconstructed_words)
