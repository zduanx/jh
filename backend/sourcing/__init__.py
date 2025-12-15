"""
Job URL Sourcing Module

Handles web crawling/scraping of job posting URLs from various company career pages.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from extractors.registry import Company

__all__ = ['Company']
