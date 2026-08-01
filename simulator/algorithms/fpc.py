"""
Frequent Pattern Compression (FPC) Engine for Project Ouroboros.

Implements the 32-bit word pattern matcher described by Alameldeen & Wood (ISCA 2004).
Evaluates 16 words per 64-byte cache line across 8 pattern prefix encodings.
Includes an in-flight 512-bit size checker to abort compression on high-entropy data.
"""

import struct
from dataclasses import dataclass
from typing import List, Tuple

CACHE_LINE_SIZE = 64
NUM_WORDS = 16


@dataclass
class FPCResult:
    original_size: int
    compressed_size_bytes: int
    compressed_bits: int
    compression_ratio: float
    is_compressed: bool
    patterns_used: List[str]


class FPCCompressor:
    """
    Simulates the Frequent Pattern Compression (FPC) hardware engine.
    Matches each 32-bit word to 1 of 8 prefix patterns.
    """

    def compress(self, line: bytes) -> FPCResult:
        if len(line) != CACHE_LINE_SIZE:
            line = line.ljust(CACHE_LINE_SIZE, b'\x00')[:CACHE_LINE_SIZE]

        words = [struct.unpack('<i', line[i:i + 4])[0] for i in range(0, 64, 4)]
        patterns: List[str] = []
        total_bits = 0

        for word in words:
            pat_name, bits = self._match_word_pattern(word)
            patterns.append(pat_name)
            total_bits += bits

        # In-flight size checker: If total compressed bits > 512 (64 bytes), abort compression
        if total_bits >= 512:
            return FPCResult(
                original_size=64,
                compressed_size_bytes=64,
                compressed_bits=512,
                compression_ratio=1.0,
                is_compressed=False,
                patterns_used=patterns
            )

        # Convert bits to byte alignment (rounding up)
        compressed_bytes = (total_bits + 7) // 8
        ratio = CACHE_LINE_SIZE / compressed_bytes

        return FPCResult(
            original_size=64,
            compressed_size_bytes=compressed_bytes,
            compressed_bits=total_bits,
            compression_ratio=ratio,
            is_compressed=True,
            patterns_used=patterns
        )

    def _match_word_pattern(self, word: int) -> Tuple[str, int]:
        # 000: Zero word
        if word == 0:
            return ("000 (Zero)", 3)

        # 001: 4-bit sign-extended
        if -8 <= word <= 7:
            return ("001 (4b Int)", 7)

        # 010: 8-bit sign-extended
        if -128 <= word <= 127:
            return ("010 (8b Int)", 11)

        # 011: 16-bit sign-extended
        if -32768 <= word <= 32767:
            return ("011 (16b Int)", 19)

        # 100: Half-word zero-padded (upper 16 bits zero)
        if 0 <= word <= 0xFFFF:
            return ("100 (Zero-Pad)", 19)

        # 110: Repeated byte pattern (e.g. 0xAAAA_AAAA)
        raw_u32 = struct.unpack('<I', struct.pack('<i', word))[0]
        b0 = raw_u32 & 0xFF
        b1 = (raw_u32 >> 8) & 0xFF
        b2 = (raw_u32 >> 16) & 0xFF
        b3 = (raw_u32 >> 24) & 0xFF
        if b0 == b1 == b2 == b3:
            return ("110 (Rep Byte)", 11)

        # 101: Two 1-byte sign-extended halfwords
        hw_high = struct.unpack('<h', struct.pack('<H', (raw_u32 >> 16) & 0xFFFF))[0]
        hw_low = struct.unpack('<h', struct.pack('<H', raw_u32 & 0xFFFF))[0]
        if (-128 <= hw_high <= 127) and (-128 <= hw_low <= 127):
            return ("101 (2x 8b Int)", 19)

        # 111: Uncompressed word
        return ("111 (Raw 32b)", 35)
