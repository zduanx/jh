"""
Company Extractor Registry

Maps company names to their corresponding extractor classes.
This allows dynamic lookup of extractors based on user selections.

Usage:
    from extractors.registry import COMPANY_REGISTRY, get_extractor
    from extractors.enums import Company

    # Get extractor class
    ExtractorClass = COMPANY_REGISTRY[Company.GOOGLE]

    # Or use helper
    extractor = get_extractor(Company.GOOGLE, config=filters)
"""

from typing import Dict, Type
from .base_extractor import BaseJobExtractor
from .config import TitleFilters
from .enums import Company

# Import all extractors
from .google import GoogleExtractor
from .amazon import AmazonExtractor
from .anthropic import AnthropicExtractor
from .tiktok import TikTokExtractor
from .roblox import RobloxExtractor
from .netflix import NetflixExtractor


# Company to Extractor mapping
COMPANY_REGISTRY: Dict[Company, Type[BaseJobExtractor]] = {
    Company.GOOGLE: GoogleExtractor,
    Company.AMAZON: AmazonExtractor,
    Company.ANTHROPIC: AnthropicExtractor,
    Company.TIKTOK: TikTokExtractor,
    Company.ROBLOX: RobloxExtractor,
    Company.NETFLIX: NetflixExtractor,
}


def get_extractor(company: Company | str, config: TitleFilters = None) -> BaseJobExtractor:
    """
    Get an initialized extractor for a company

    Args:
        company: Company enum or string identifier (e.g., Company.GOOGLE or 'google')
        config: Title filtering configuration

    Returns:
        Initialized extractor instance

    Raises:
        ValueError: If company not found in registry

    Example:
        >>> from extractors.config import TitleFilters
        >>> from extractors.enums import Company
        >>> filters = TitleFilters(exclude=['senior staff'])
        >>> extractor = get_extractor(Company.GOOGLE, config=filters)
        >>> # Or using string
        >>> extractor = get_extractor('google', config=filters)
        >>> result = extractor.extract_source_urls_metadata()
    """
    # Convert string to Company enum if needed
    if isinstance(company, str):
        try:
            company = Company(company.lower())
        except ValueError:
            available = ', '.join([c.value for c in Company])
            raise ValueError(
                f"Company '{company}' not found in registry. "
                f"Available: {available}"
            )

    if company not in COMPANY_REGISTRY:
        available = ', '.join([c.value for c in Company])
        raise ValueError(
            f"Company '{company.value}' not found in registry. "
            f"Available: {available}"
        )

    ExtractorClass = COMPANY_REGISTRY[company]
    return ExtractorClass(config=config)


def list_companies() -> list[str]:
    """
    Get list of all supported company names

    Returns:
        List of company name strings

    Example:
        >>> list_companies()
        ['google', 'amazon', 'anthropic', 'tiktok', 'roblox', 'netflix']
    """
    return [company.value for company in Company]
