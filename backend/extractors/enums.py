"""
Company Enum

Defines all supported companies for job URL sourcing.
This is in a separate file to avoid circular imports between registry and extractors.
"""

from enum import Enum


class Company(str, Enum):
    """
    Supported companies for job URL sourcing

    This enum defines all companies that have extractors implemented.
    """
    GOOGLE = "google"
    AMAZON = "amazon"
    ANTHROPIC = "anthropic"
    TIKTOK = "tiktok"
    ROBLOX = "roblox"
    NETFLIX = "netflix"
    OPENAI = "openai"
