"""
Enums for job URL sourcing
"""

from enum import Enum


class Company(str, Enum):
    """
    Supported companies for job URL sourcing

    This enum defines all companies that have extractors implemented.
    Used across the codebase for type safety and API responses.
    """
    GOOGLE = "google"
    AMAZON = "amazon"
    ANTHROPIC = "anthropic"
    TIKTOK = "tiktok"
    ROBLOX = "roblox"
    NETFLIX = "netflix"

    @classmethod
    def list_all(cls) -> list[str]:
        """
        Get list of all company names

        Returns:
            List of company name strings

        Example:
            >>> Company.list_all()
            ['google', 'amazon', 'anthropic', 'tiktok', 'roblox', 'netflix']
        """
        return [company.value for company in cls]

    @classmethod
    def from_string(cls, company_name: str) -> "Company":
        """
        Convert string to Company enum

        Args:
            company_name: Company name (case-insensitive)

        Returns:
            Company enum value

        Raises:
            ValueError: If company not found

        Example:
            >>> Company.from_string("google")
            <Company.GOOGLE: 'google'>
            >>> Company.from_string("GOOGLE")
            <Company.GOOGLE: 'google'>
        """
        try:
            return cls(company_name.lower())
        except ValueError:
            valid = ", ".join(cls.list_all())
            raise ValueError(
                f"Unknown company '{company_name}'. "
                f"Valid companies: {valid}"
            )
