"""
TikTok extractor snapshot tests.

Tests extract_raw_info() against stored HTML fixtures.
"""

from extractors.tiktok import TikTokExtractor
from extractors.__tests__.base_snapshot_test import BaseExtractorSnapshotTest


class TestTikTokExtractor(BaseExtractorSnapshotTest):
    """Snapshot tests for TikTok job extractor."""

    extractor_class = TikTokExtractor
    company = "tiktok"
    test_cases = ["7554068070034573576", "7484327938503182600"]
