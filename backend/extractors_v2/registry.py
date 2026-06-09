"""
extractors_v2 registry — the SOURCE OF TRUTH for "what companies exist".

Replaces the old `Company` enum. Companies are an OPEN, growing set (the discovery
agent adds new ones), so an enum is the wrong type — this registry is keyed by the
company string and validates lookups (catching typos the enum used to catch at
compile time, now at lookup time, which is correct for a runtime-determined set).

The discovery agent MAINTAINS this file: when it onboards a company, it (via the
write_file tool, after read_file) adds an entry to REGISTRY below. So this file
grows alongside the generated extractors_v2/{company}.py files.

Consistency: every part of the backend that needs the company list reads HERE
(list_companies / get_extractor) — nobody hardcodes company strings elsewhere.
"""

from __future__ import annotations

from extractors_v2_base import BaseExtractorV2
from extractors_v2.anthropic import AnthropicExtractor
from extractors_v2.hrt import HrtExtractor
from extractors_v2.netflix import NetflixExtractor
from extractors_v2.openai import OpenaiExtractor
from extractors_v2.roblox import RobloxExtractor

# company slug → extractor class. The agent appends entries here (read-then-write).
REGISTRY: dict[str, type[BaseExtractorV2]] = {
    "anthropic": AnthropicExtractor,
    "hrt": HrtExtractor,
    "netflix": NetflixExtractor,
    "openai": OpenaiExtractor,
    "roblox": RobloxExtractor,
}


def list_companies() -> list[str]:
    """All known company slugs (the source of truth for the list-companies endpoint)."""
    return sorted(REGISTRY.keys())


def get_extractor(company: str) -> type[BaseExtractorV2]:
    """
    Look up an extractor class by company slug. Raises a clear error for unknown
    companies (this is the typo/consistency check that replaces the enum).
    """
    key = company.strip().lower()
    if key not in REGISTRY:
        known = ", ".join(list_companies()) or "(none yet)"
        raise ValueError(f"unknown company '{company}'. Known companies: {known}")
    return REGISTRY[key]
