"""
Real-Time Adaptive Entropy Estimator for Project Ouroboros.

Calculates Shannon Entropy H(X) and Normalized Entropy H_norm(X) to predict compressibility.
High-entropy data (e.g. encrypted payloads, pre-compressed JPEG/video) above the
threshold (default 0.90 normalized or 5.4 bits for 64B cache lines) will bypass the
compression pipeline to prevent size expansion and latency overhead.
"""

from __future__ import annotations

import math
from typing import Sequence, Union

DEFAULT_ENTROPY_THRESHOLD = 5.4  # For 64-byte cache line (max theoretical H = 6.0 bits)


def calculate_entropy(data: Union[bytes, Sequence[int]]) -> float:
    """
    Calculate the Shannon Entropy of a byte sequence in bits per byte.
    Max theoretical entropy for N bytes is min(8.0, log2(N)).
    """
    if not data:
        return 0.0

    length = len(data)
    counts = [0] * 256
    for byte in data:
        counts[byte] += 1

    entropy = 0.0
    for count in counts:
        if count > 0:
            p = count / length
            entropy -= p * math.log2(p)

    return entropy


def calculate_normalized_entropy(data: Union[bytes, Sequence[int]]) -> float:
    """
    Calculates normalized entropy between 0.0 (zero entropy) and 1.0 (maximum randomness).
    """
    if not data:
        return 0.0
    length = len(data)
    max_h = min(8.0, math.log2(length)) if length > 1 else 1.0
    return calculate_entropy(data) / max_h


def is_high_entropy(data: Union[bytes, Sequence[int]], threshold: float | None = None) -> bool:
    """
    Determines if a block of data is high-entropy (incompressible).
    
    For 64-byte cache lines, defaults to 5.4 bits (90% of max 6.0 bits).
    For arbitrary byte lengths, uses threshold if provided or 0.90 normalized entropy.
    """
    if not data:
        return False

    if threshold is None:
        if len(data) == 64:
            threshold = 5.4
        else:
            return calculate_normalized_entropy(data) >= 0.90

    return calculate_entropy(data) >= threshold
