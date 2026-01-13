"""
Roblox extractor snapshot tests.

Tests extract_raw_info() against stored HTML fixtures.
"""

from extractors.roblox import RobloxExtractor
from extractors.__tests__.base_snapshot_test import BaseExtractorSnapshotTest


class TestRobloxExtractor(BaseExtractorSnapshotTest):
    """Snapshot tests for Roblox job extractor."""

    extractor_class = RobloxExtractor
    company = "roblox"
    test_cases = ["7350013", "7054468"]
