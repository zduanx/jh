"""
Anthropic extractor snapshot tests.

Tests extract_raw_info() against stored HTML fixtures.
"""

from extractors.anthropic import AnthropicExtractor
from extractors.__tests__.base_snapshot_test import BaseExtractorSnapshotTest


class TestAnthropicExtractor(BaseExtractorSnapshotTest):
    """Snapshot tests for Anthropic job extractor."""

    extractor_class = AnthropicExtractor
    company = "anthropic"
    test_cases = ["5058714008", "4941204008"]
