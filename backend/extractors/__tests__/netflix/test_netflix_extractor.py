"""
Netflix extractor snapshot tests.

Tests extract_raw_info() against stored HTML fixtures.
"""

from extractors.netflix import NetflixExtractor
from extractors.__tests__.base_snapshot_test import BaseExtractorSnapshotTest


class TestNetflixExtractor(BaseExtractorSnapshotTest):
    """Snapshot tests for Netflix job extractor."""

    extractor_class = NetflixExtractor
    company = "netflix"
    test_cases = ["790312551421", "790302341342"]
