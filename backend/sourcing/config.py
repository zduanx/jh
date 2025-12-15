"""
Configuration management for job URL sourcing

Provides get_user_sourcing_settings() function that:
- For local/testing: Returns hardcoded configurations
- For production (future): Will query from database based on user_id

This abstraction allows us to switch from hardcoded to DB without changing
the orchestrator code.
"""

import sys
import os
from typing import Dict

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from extractors import TitleFilters
from extractors.registry import Company


def get_user_sourcing_settings(user_id: str = None, local_testing: bool = False) -> Dict[Company, TitleFilters]:
    """
    Get job URL sourcing configuration for a user

    Args:
        user_id: User identifier (for future DB queries)
        local_testing: If True, return hardcoded configurations.
                      If False, will integrate with DB/SQS (future)

    Returns:
        Dict mapping Company enum to their TitleFilters configuration

    Current implementation:
        - local_testing=True: Returns hardcoded configurations
        - local_testing=False: Raises NotImplementedError (awaiting DB/SQS integration)

    Example:
        >>> settings = get_user_sourcing_settings("user123", local_testing=True)
        >>> google_config = settings[Company.GOOGLE]
        >>> print(google_config.exclude)
        ['senior staff']
    """
    if not local_testing:
        raise NotImplementedError(
            "Production mode (local_testing=False) requires DB/SQS integration. "
            "Use local_testing=True for hardcoded configurations."
        )

    # Hardcoded configurations for local testing
    return {
        Company.GOOGLE: TitleFilters(
            include=None,  # Include all
            exclude=['senior staff']
        ),
        Company.AMAZON: TitleFilters(
            include=None,
            exclude=[]
        ),
        Company.ANTHROPIC: TitleFilters(
            include=None,
            exclude=[]
        ),
        Company.TIKTOK: TitleFilters(
            include=['software', 'tech lead'],
            exclude=['usds']
        ),
        Company.ROBLOX: TitleFilters(
            include=['software'],
            exclude=['intern', 'early career']
        ),
        Company.NETFLIX: TitleFilters(
            include=None,
            exclude=[]
        ),
    }


def get_company_settings(user_id: str, company: Company | str, local_testing: bool = False) -> TitleFilters:
    """
    Get configuration for a specific company for a user

    Args:
        user_id: User identifier
        company: Company enum or string identifier (e.g., Company.GOOGLE or 'google')
        local_testing: If True, use hardcoded configurations

    Returns:
        TitleFilters configuration for the company

    Raises:
        KeyError: If company not found in user's configuration

    Example:
        >>> config = get_company_settings("user123", Company.GOOGLE, local_testing=True)
        >>> print(config.exclude)
        ['senior staff']
    """
    # Convert string to Company enum if needed
    if isinstance(company, str):
        company = Company(company.lower())

    settings = get_user_sourcing_settings(user_id, local_testing=local_testing)
    if company not in settings:
        available = ', '.join([c.value for c in Company])
        raise KeyError(
            f"Company '{company.value}' not found in user's configuration. "
            f"Available: {available}"
        )
    return settings[company]


# Future implementation (commented out):
# def get_user_sourcing_settings_from_db(user_id: str) -> Dict[str, TitleFilters]:
#     """
#     Query job URL sourcing configuration from database for a specific user
#
#     Args:
#         user_id: User ID to get user-specific configurations
#
#     Returns:
#         Dict mapping company names to their TitleFilters configuration
#     """
#     import boto3
#     from boto3.dynamodb.conditions import Key
#
#     dynamodb = boto3.resource('dynamodb')
#     table = dynamodb.Table('user_sourcing_settings')
#
#     # Query user's configurations
#     response = table.query(
#         KeyConditionExpression=Key('user_id').eq(user_id)
#     )
#
#     # Parse configurations
#     settings = {}
#     for item in response['Items']:
#         company = item['company_name']
#         settings[company] = TitleFilters(
#             include=item.get('include_terms'),
#             exclude=item.get('exclude_terms', [])
#         )
#
#     return settings
