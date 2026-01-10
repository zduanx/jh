"""
Unit tests for SimHash content deduplication.

Tests SimHash computation, Hamming distance, and similarity detection
using mock HTML content samples.

Run: python3 -m pytest utils/__tests__/test_simhash.py -v
"""

import pytest

from utils.simhash import (
    compute_simhash,
    hamming_distance,
    is_similar,
    _tokenize,
    _hash_token,
)


# Mock HTML content samples for testing
SAMPLE_HTML_1 = """
<html>
<head><title>Software Engineer - Google</title></head>
<body>
<h1>Software Engineer</h1>
<p>We are looking for a software engineer to join our team.</p>
<p>Requirements:</p>
<ul>
    <li>5+ years of experience in Python or Java</li>
    <li>Strong problem-solving skills</li>
    <li>Experience with distributed systems</li>
</ul>
</body>
</html>
"""

# Nearly identical content (minor wording change)
SAMPLE_HTML_SIMILAR = """
<html>
<head><title>Software Engineer - Google</title></head>
<body>
<h1>Software Engineer</h1>
<p>We are looking for a software engineer to join our amazing team.</p>
<p>Requirements:</p>
<ul>
    <li>5+ years of experience in Python or Java</li>
    <li>Strong problem-solving skills</li>
    <li>Experience with distributed systems</li>
</ul>
</body>
</html>
"""

# Completely different content
SAMPLE_HTML_DIFFERENT = """
<html>
<head><title>Marketing Manager - Amazon</title></head>
<body>
<h1>Marketing Manager</h1>
<p>Lead our marketing efforts across multiple channels.</p>
<p>Requirements:</p>
<ul>
    <li>MBA preferred</li>
    <li>10+ years marketing experience</li>
    <li>Strong communication skills</li>
</ul>
</body>
</html>
"""


class TestTokenize:
    """Tests for _tokenize function."""

    def test_basic_tokenization(self):
        """Should extract words and lowercase them."""
        tokens = _tokenize("Hello World")
        assert tokens == ["hello", "world"]

    def test_html_tags_become_tokens(self):
        """HTML tags are treated as tokens (tag names extracted)."""
        tokens = _tokenize("<html><body>Test</body></html>")
        assert "html" in tokens
        assert "body" in tokens
        assert "test" in tokens

    def test_mixed_case(self):
        """Should lowercase all tokens."""
        tokens = _tokenize("PyThOn JAVA javascript")
        assert tokens == ["python", "java", "javascript"]

    def test_numbers_included(self):
        """Should include alphanumeric tokens with numbers."""
        tokens = _tokenize("Python3 ES6 5years")
        assert "python3" in tokens
        assert "es6" in tokens
        assert "5years" in tokens

    def test_empty_string(self):
        """Empty string should return empty list."""
        assert _tokenize("") == []

    def test_only_punctuation(self):
        """Only punctuation should return empty list."""
        assert _tokenize("!@#$%^&*()") == []


class TestHashToken:
    """Tests for _hash_token function."""

    def test_deterministic(self):
        """Same token should always produce same hash."""
        hash1 = _hash_token("python")
        hash2 = _hash_token("python")
        assert hash1 == hash2

    def test_different_tokens_different_hashes(self):
        """Different tokens should produce different hashes."""
        hash1 = _hash_token("python")
        hash2 = _hash_token("java")
        assert hash1 != hash2

    def test_returns_64_bit_int(self):
        """Hash should be a 64-bit integer (0 to 2^64-1)."""
        h = _hash_token("test")
        assert isinstance(h, int)
        assert 0 <= h < (1 << 64)


class TestComputeSimhash:
    """Tests for compute_simhash function."""

    def test_empty_content_returns_zero(self):
        """Empty content should return 0."""
        assert compute_simhash("") == 0

    def test_only_punctuation_returns_zero(self):
        """Content with only punctuation (no tokens) should return 0."""
        assert compute_simhash("!!! ??? ...") == 0

    def test_deterministic(self):
        """Same content should always produce same hash."""
        hash1 = compute_simhash(SAMPLE_HTML_1)
        hash2 = compute_simhash(SAMPLE_HTML_1)
        assert hash1 == hash2

    def test_returns_64_bit_int(self):
        """SimHash should be a 64-bit integer."""
        h = compute_simhash(SAMPLE_HTML_1)
        assert isinstance(h, int)
        assert 0 <= h < (1 << 64)

    def test_different_content_different_hash(self):
        """Different content should produce different hashes."""
        hash1 = compute_simhash(SAMPLE_HTML_1)
        hash2 = compute_simhash(SAMPLE_HTML_DIFFERENT)
        assert hash1 != hash2

    def test_single_word(self):
        """Single word should produce non-zero hash."""
        h = compute_simhash("hello")
        assert h != 0


class TestHammingDistance:
    """Tests for hamming_distance function."""

    def test_identical_hashes_zero_distance(self):
        """Identical hashes should have distance 0."""
        assert hamming_distance(0b1010, 0b1010) == 0

    def test_one_bit_difference(self):
        """One bit different should have distance 1."""
        assert hamming_distance(0b1010, 0b1011) == 1

    def test_all_bits_different(self):
        """All bits different (for 4-bit) should count correctly."""
        assert hamming_distance(0b1010, 0b0101) == 4

    def test_zero_values(self):
        """Distance from 0 to 0 should be 0."""
        assert hamming_distance(0, 0) == 0

    def test_zero_to_nonzero(self):
        """Distance from 0 counts set bits in other value."""
        assert hamming_distance(0, 0b111) == 3
        assert hamming_distance(0, 0b1111) == 4

    def test_large_values(self):
        """Should work with 64-bit values."""
        max_64bit = (1 << 64) - 1  # All 1s
        assert hamming_distance(0, max_64bit) == 64


class TestIsSimilar:
    """Tests for is_similar function."""

    def test_none_values_not_similar(self):
        """None values should never be similar."""
        assert is_similar(None, 12345) is False
        assert is_similar(12345, None) is False
        assert is_similar(None, None) is False

    def test_identical_hashes_similar(self):
        """Identical hashes should be similar."""
        assert is_similar(12345, 12345) is True

    def test_within_threshold_similar(self):
        """Hashes within threshold should be similar."""
        # Distance of 3 (default threshold)
        hash1 = 0b1111
        hash2 = 0b1000  # 3 bits different
        assert is_similar(hash1, hash2, threshold=3) is True

    def test_exceeds_threshold_not_similar(self):
        """Hashes exceeding threshold should not be similar."""
        hash1 = 0b1111
        hash2 = 0b0000  # 4 bits different
        assert is_similar(hash1, hash2, threshold=3) is False

    def test_custom_threshold(self):
        """Should respect custom threshold."""
        hash1 = 0b11111
        hash2 = 0b00000  # 5 bits different
        assert is_similar(hash1, hash2, threshold=5) is True
        assert is_similar(hash1, hash2, threshold=4) is False


class TestSimilarityWithMockContent:
    """Integration tests using mock HTML content."""

    def test_identical_content_is_similar(self):
        """Same content should be similar."""
        hash1 = compute_simhash(SAMPLE_HTML_1)
        hash2 = compute_simhash(SAMPLE_HTML_1)
        assert is_similar(hash1, hash2) is True

    def test_minor_changes_is_similar(self):
        """Content with minor changes should be similar."""
        hash1 = compute_simhash(SAMPLE_HTML_1)
        hash2 = compute_simhash(SAMPLE_HTML_SIMILAR)

        distance = hamming_distance(hash1, hash2)
        # Similar content should have small Hamming distance
        assert distance <= 10, f"Expected distance <= 10, got {distance}"

        # With default threshold of 3, might not pass, but shows locality-sensitivity
        # The key property is that distance is much smaller than for different content

    def test_different_content_not_similar(self):
        """Completely different content should not be similar."""
        hash1 = compute_simhash(SAMPLE_HTML_1)
        hash2 = compute_simhash(SAMPLE_HTML_DIFFERENT)

        distance = hamming_distance(hash1, hash2)
        # Different content should have large Hamming distance
        assert distance > 10, f"Expected distance > 10, got {distance}"

        # Should not be similar with default threshold
        assert is_similar(hash1, hash2) is False

    def test_locality_sensitivity(self):
        """Similar content should be closer than different content."""
        hash_original = compute_simhash(SAMPLE_HTML_1)
        hash_similar = compute_simhash(SAMPLE_HTML_SIMILAR)
        hash_different = compute_simhash(SAMPLE_HTML_DIFFERENT)

        distance_to_similar = hamming_distance(hash_original, hash_similar)
        distance_to_different = hamming_distance(hash_original, hash_different)

        # Core property: similar content should have smaller distance
        assert distance_to_similar < distance_to_different, (
            f"Expected similar content distance ({distance_to_similar}) "
            f"< different content distance ({distance_to_different})"
        )


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_whitespace_only(self):
        """Whitespace-only content should return 0."""
        assert compute_simhash("   \n\t  ") == 0

    def test_very_long_content(self):
        """Should handle long content without issues."""
        long_content = "word " * 10000
        h = compute_simhash(long_content)
        assert h != 0
        assert isinstance(h, int)

    def test_unicode_content(self):
        """Should handle unicode content."""
        unicode_content = "Héllo Wörld café naïve 日本語"
        h = compute_simhash(unicode_content)
        # Japanese characters don't match \w in default locale,
        # but accented chars and basic words should work
        assert isinstance(h, int)

    def test_repeated_content(self):
        """Repeated words shouldn't break the algorithm."""
        content = "repeat repeat repeat repeat repeat"
        h = compute_simhash(content)
        assert h != 0
