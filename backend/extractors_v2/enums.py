"""
Company enum for extractors_v2.

Carried from v1 (already self-contained). v2 grows this as the agent adds companies.
Self-contained: stdlib only — so this whole package can live inside the Docker sandbox
with no access to the rest of the backend.
"""

from enum import Enum


class Company(str, Enum):
    """Companies with a v2 extractor (or being discovered by the agent)."""

    GOOGLE = "google"
    AMAZON = "amazon"
    ANTHROPIC = "anthropic"
    TIKTOK = "tiktok"
    ROBLOX = "roblox"
    NETFLIX = "netflix"
    OPENAI = "openai"

    @classmethod
    def from_str(cls, value: str) -> "Company":
        """Look up a Company by name (case-insensitive). Raises ValueError if unknown."""
        try:
            return cls(value.lower())
        except ValueError:
            available = ", ".join(c.value for c in cls)
            raise ValueError(f"Unknown company '{value}'. Known: {available}")
