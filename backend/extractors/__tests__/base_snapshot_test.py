"""
Base class for extractor snapshot tests.

Snapshot testing pattern:
1. Store raw HTML fixtures in __tests__/<company>/<external_id>.html
2. Store expected output in __tests__/<company>/<external_id>.expected.json
3. Tests verify extract_raw_info() produces expected output

Usage:
    class TestNetflixExtractor(BaseExtractorSnapshotTest):
        extractor_class = NetflixExtractor
        company = "netflix"
        test_cases = ["790312551421"]
"""

import json
import pytest
from pathlib import Path
from abc import ABC
from typing import Type, List

from extractors.base_extractor import BaseJobExtractor
from extractors.config import TitleFilters


class BaseExtractorSnapshotTest(ABC):
    """
    Base class for extractor snapshot tests.

    Subclasses must define:
    - extractor_class: The extractor class to test
    - company: Company name (matches __tests__ directory)
    - test_cases: List of external_ids to test
    """

    extractor_class: Type[BaseJobExtractor] = None
    company: str = None
    test_cases: List[str] = []

    @pytest.fixture
    def extractor(self):
        """Create extractor instance with empty filters."""
        return self.extractor_class(config=TitleFilters())

    @pytest.fixture
    def test_dir(self) -> Path:
        """Get the test directory for this company."""
        return Path(__file__).parent / self.company

    def get_fixture_path(self, external_id: str) -> Path:
        """Get path to raw HTML fixture."""
        return Path(__file__).parent / self.company / f"{external_id}.html"

    def get_expected_path(self, external_id: str) -> Path:
        """Get path to expected output JSON."""
        return Path(__file__).parent / self.company / f"{external_id}.expected.json"

    def load_fixture(self, external_id: str) -> str:
        """Load raw HTML fixture."""
        path = self.get_fixture_path(external_id)
        if not path.exists():
            pytest.skip(f"Fixture not found: {path}")
        return path.read_text()

    def load_expected(self, external_id: str) -> dict:
        """Load expected output JSON."""
        path = self.get_expected_path(external_id)
        if not path.exists():
            pytest.skip(f"Expected output not found: {path}")
        return json.loads(path.read_text())

    def save_expected(self, external_id: str, result: dict):
        """Save expected output JSON (for generating snapshots)."""
        path = self.get_expected_path(external_id)
        path.write_text(json.dumps(result, indent=2, ensure_ascii=False))

    def test_extract_raw_info(self, extractor):
        """
        Test extract_raw_info against all test cases.

        For each test case:
        1. Load raw HTML fixture
        2. Run extract_raw_info
        3. Compare against expected output
        """
        for external_id in self.test_cases:
            raw_content = self.load_fixture(external_id)
            expected = self.load_expected(external_id)

            result = extractor.extract_raw_info(raw_content)

            # Compare description
            assert result.get('description') == expected.get('description'), \
                f"Description mismatch for {self.company}:{external_id}"

            # Compare requirements
            assert result.get('requirements') == expected.get('requirements'), \
                f"Requirements mismatch for {self.company}:{external_id}"

    def test_extract_has_requirements(self, extractor):
        """Verify requirements are not empty for test cases."""
        for external_id in self.test_cases:
            raw_content = self.load_fixture(external_id)
            result = extractor.extract_raw_info(raw_content)

            assert result.get('requirements'), \
                f"Requirements should not be empty for {self.company}:{external_id}"

    def test_extract_has_description(self, extractor):
        """Verify description is not empty for test cases."""
        for external_id in self.test_cases:
            raw_content = self.load_fixture(external_id)
            result = extractor.extract_raw_info(raw_content)

            assert result.get('description'), \
                f"Description should not be empty for {self.company}:{external_id}"


def generate_expected_output(extractor_class: Type[BaseJobExtractor],
                              company: str,
                              external_id: str) -> dict:
    """
    Helper to generate expected output for a test case.

    Usage:
        from extractors.netflix import NetflixExtractor
        from extractors.__tests__.base_snapshot_test import generate_expected_output

        result = generate_expected_output(NetflixExtractor, "netflix", "790312551421")
        print(result)
    """
    test_dir = Path(__file__).parent / company
    fixture_path = test_dir / f"{external_id}.html"

    if not fixture_path.exists():
        raise FileNotFoundError(f"Fixture not found: {fixture_path}")

    extractor = extractor_class(config=TitleFilters())
    raw_content = fixture_path.read_text()
    result = extractor.extract_raw_info(raw_content)

    # Save to expected file
    expected_path = test_dir / f"{external_id}.expected.json"
    expected_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))

    print(f"Generated: {expected_path}")
    return result
