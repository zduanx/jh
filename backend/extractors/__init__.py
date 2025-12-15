"""
Job extractors package

This package contains the base extractor class and company-specific
implementations for extracting job URLs.

Phase 1: URL Extraction (current)
- BaseJobExtractor: Abstract base class
- Company-specific extractors: GoogleExtractor, TikTokExtractor, etc.

Future phases:
- Phase 2: Crawlers (fetch raw content)
- Phase 3: Parsers (extract structured data)
"""

from .base_extractor import BaseJobExtractor
from .config import TitleFilters
from .enums import Company
from .registry import get_extractor, list_companies, COMPANY_REGISTRY

__all__ = [
    'BaseJobExtractor',
    'TitleFilters',
    'Company',
    'get_extractor',
    'list_companies',
    'COMPANY_REGISTRY',
]

__version__ = '0.1.0'
