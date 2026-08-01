"""
Project Ouroboros Real PC File & Memory Trace Compression Utility.

Compresses real files, binary executables, source code, or graphics textures from your PC
using Ouroboros Adaptive Entropy Estimation, Base-Delta-Immediate (BDI), and BFP algorithms.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from simulator.core.memory_controller import OuroborosMemoryController


def compress_file_on_pc(file_path: str):
    path = Path(file_path)
    if not path.exists():
        print(f"[!] Error: File '{file_path}' does not exist.")
        return

    print("=========================================================================================")
    print("           PROJECT OUROBOROS: REAL PC FILE MEMORY COMPRESSION ENGINE                    ")
    print("=========================================================================================")
    print(f"[*] Processing Real PC File: {path.resolve()}")

    with open(path, "rb") as f:
        file_bytes = f.read()

    file_size = len(file_bytes)
    print(f"[*] Original File Size: {file_size:,} bytes ({file_size / 1024:.2f} KB)")

    controller = OuroborosMemoryController()

    # Process in 64-byte memory cache lines
    line_size = 64
    num_lines = (file_size + line_size - 1) // line_size

    uncompressed_bytes = 0
    compressed_bytes = 0
    embedded_count = 0
    bpassed_count = 0

    for i in range(num_lines):
        chunk = file_bytes[i * line_size : (i + 1) * line_size]
        if len(chunk) < line_size:
            chunk = chunk + b'\x00' * (line_size - len(chunk))

        vaddr = i * 64
        entry = controller.write_line(vaddr, chunk)

        uncompressed_bytes += 64
        compressed_bytes += entry.compressed_size

        if entry.is_embedded:
            embedded_count += 1
        if entry.pattern == "BYPASS":
            bpassed_count += 1


    ratio = uncompressed_bytes / compressed_bytes if compressed_bytes > 0 else 1.0

    print("\n--- Empirical Ouroboros Memory Controller Results ---")
    print(f"• Virtual Memory Allocated : {uncompressed_bytes:,} bytes")
    print(f"• Physical DRAM Allocated   : {compressed_bytes:,} bytes")
    print(f"• Effective Multiplier      : {ratio:.2f}x Capacity Expansion")
    print(f"• Direct Payload Embeddings : {embedded_count:,} lines ({embedded_count/num_lines*100:.1f}%) -> 0 DRAM Sectors!")
    print(f"• Adaptive Entropy Bypasses : {bpassed_count:,} lines ({bpassed_count/num_lines*100:.1f}%) -> High-entropy protected")
    print("=========================================================================================")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        compress_file_on_pc(sys.argv[1])
    else:
        # Default test on README.md
        compress_file_on_pc("README.md")
