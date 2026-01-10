"""
SimHash implementation for content deduplication.

SimHash is a locality-sensitive hashing algorithm that produces similar hashes
for similar content. Two documents are considered "similar" if their SimHash
values have a small Hamming distance (number of differing bits).

Reference: Charikar, M. (2002). Similarity estimation techniques from rounding algorithms.
https://www.cs.princeton.edu/courses/archive/spring04/cos598B/bib/CharikarES.pdf

Usage:
    from utils.simhash import compute_simhash, is_similar

    hash1 = compute_simhash(html_content_1)
    hash2 = compute_simhash(html_content_2)

    if is_similar(hash1, hash2):
        print("Content is similar, skip re-extraction")
"""

import hashlib
import re
from typing import Optional


def _tokenize(text: str) -> list[str]:
    """
    Tokenize text into words/tokens for SimHash computation.

    Extracts alphanumeric tokens, lowercased. This simple approach works
    well for HTML content where we want to detect meaningful text changes.
    """
    # Extract alphanumeric tokens (words), lowercase
    tokens = re.findall(r'\b\w+\b', text.lower())
    return tokens


def _hash_token(token: str) -> int:
    """
    Hash a single token to a 64-bit integer.

    Uses MD5 truncated to 64 bits. MD5 is fine here since we're not
    using it for security, just uniform distribution.
    """
    h = hashlib.md5(token.encode('utf-8')).digest()
    # Take first 8 bytes (64 bits)
    return int.from_bytes(h[:8], byteorder='big')


def compute_simhash(content: str) -> int:
    """
    Compute 64-bit SimHash of content.

    Algorithm:
    1. Tokenize content into words
    2. Hash each token to 64-bit value
    3. For each bit position, sum +1 if bit is 1, -1 if bit is 0
    4. Final hash: bit is 1 if sum > 0, else 0

    Args:
        content: Text content (typically raw HTML)

    Returns:
        64-bit SimHash as integer
    """
    if not content:
        return 0

    tokens = _tokenize(content)
    if not tokens:
        return 0

    # Vector of 64 counters, one per bit position
    v = [0] * 64

    for token in tokens:
        token_hash = _hash_token(token)

        # For each bit position
        for i in range(64):
            # Check if bit i is set
            if token_hash & (1 << i):
                v[i] += 1
            else:
                v[i] -= 1

    # Build final hash: bit is 1 if counter > 0
    simhash = 0
    for i in range(64):
        if v[i] > 0:
            simhash |= (1 << i)

    # Convert to signed 64-bit for PostgreSQL BIGINT compatibility
    # PostgreSQL BIGINT range: -9223372036854775808 to 9223372036854775807
    # Unsigned 64-bit range: 0 to 18446744073709551615
    # If MSB is set (value >= 2^63), convert to negative
    if simhash >= (1 << 63):
        simhash -= (1 << 64)

    return simhash


def hamming_distance(hash1: int, hash2: int) -> int:
    """
    Compute Hamming distance between two 64-bit hashes.

    Hamming distance = number of bit positions where bits differ.
    Works correctly for both signed and unsigned 64-bit values.

    Args:
        hash1: First 64-bit hash (signed or unsigned)
        hash2: Second 64-bit hash (signed or unsigned)

    Returns:
        Number of differing bits (0-64)
    """
    xor = hash1 ^ hash2
    # Mask to 64 bits to handle signed values correctly
    # (Python integers can be arbitrary precision)
    xor &= (1 << 64) - 1
    # Count set bits (differing positions)
    return bin(xor).count('1')


def is_similar(hash1: Optional[int], hash2: Optional[int], threshold: int = 3) -> bool:
    """
    Check if two SimHash values indicate similar content.

    Args:
        hash1: First SimHash (or None if no previous hash)
        hash2: Second SimHash (or None)
        threshold: Maximum Hamming distance to consider "similar" (default: 3)

    Returns:
        True if content is similar (Hamming distance <= threshold)
        False if content differs or either hash is None
    """
    if hash1 is None or hash2 is None:
        return False

    return hamming_distance(hash1, hash2) <= threshold
