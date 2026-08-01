"""
Workload Memory Trace Generator for Project Ouroboros.

Generates realistic 64-byte memory trace samples for 4 workload categories:
1. Pointer & Struct Arrays (OS / C++ Applications).
2. LLM KV-Cache Activations (Home AI Inference).
3. Texture & Geometry Vertex Buffers (AAA Gaming).
4. High-Entropy Encrypted Data (Bypass Validation).
"""

from __future__ import annotations

import os
import random
import struct
from typing import Dict, List


class WorkloadGenerator:
    """
    Generates synthetic memory trace datasets matching real-world memory access patterns.
    """

    @staticmethod
    def generate_pointer_trace(count: int = 1000) -> List[bytes]:
        """
        Simulates 64-byte memory blocks containing 64-bit pointers allocated on the heap/stack.
        Upper 48 bits of virtual addresses are identical; lower 16 bits vary by small deltas.
        """
        lines: List[bytes] = []
        base_virtual_addr = 0x00007FFF00100000
        for _ in range(count):
            ptrs = [base_virtual_addr + random.randint(0, 512) for _ in range(8)]
            lines.append(b''.join(struct.pack('<q', p) for p in ptrs))
        return lines

    @staticmethod
    def generate_llm_kv_cache_trace(count: int = 1000) -> List[bytes]:
        """
        Simulates 64-byte memory blocks of quantized FP8/FP16 key-value tensor activations.
        Characterized by low dynamic range and zero-heavy channels.
        """
        lines: List[bytes] = []
        for _ in range(count):
            # Mix of small 16-bit integers and zero channels simulating quantized attention weights
            base_val = random.randint(-100, 100)
            deltas = [random.randint(-15, 15) for _ in range(32)]
            values = [base_val + d for d in deltas]
            lines.append(b''.join(struct.pack('<h', v) for v in values))
        return lines

    @staticmethod
    def generate_game_buffer_trace(count: int = 1000) -> List[bytes]:
        """
        Simulates AAA game vertex buffers and index streams (repeated bytes, low-delta int16 coordinates).
        """
        lines: List[bytes] = []
        for _ in range(count):
            # 50% zero-padded geometry, 50% repeated vertex color index bytes
            if random.random() < 0.4:
                lines.append(b'\x00' * 64)
            else:
                base_coord = random.randint(0, 1000)
                coords = [base_coord + random.randint(-10, 10) for _ in range(16)]
                lines.append(b''.join(struct.pack('<i', c) for c in coords))
        return lines

    @staticmethod
    def generate_encrypted_trace(count: int = 1000) -> List[bytes]:
        """
        Simulates high-entropy encrypted SSL/TLS payload streams (incompressible failure mode).
        """
        return [os.urandom(64) for _ in range(count)]

    @classmethod
    def get_all_workloads(cls, count_per_workload: int = 1000) -> Dict[str, List[bytes]]:
        return {
            "OS & Pointer Arrays": cls.generate_pointer_trace(count_per_workload),
            "LLM KV-Cache (Home AI)": cls.generate_llm_kv_cache_trace(count_per_workload),
            "AAA Game Buffers": cls.generate_game_buffer_trace(count_per_workload),
            "Encrypted Payload (High Entropy)": cls.generate_encrypted_trace(count_per_workload),
        }
