"""
Example usage of job URL extractors

This file demonstrates how to use extractors via the registry system.
Shows both basic usage and advanced filtering configurations.
"""

from extractors import get_extractor, Company, list_companies
from extractors.config import TitleFilters


def example_basic():
    """Example: Basic usage with no filters"""
    print("\n" + "=" * 60)
    print("Example 1: Basic Usage (No Filters)")
    print("=" * 60)

    # Get extractor using registry
    extractor = get_extractor(Company.GOOGLE)
    result = extractor.extract_source_urls_metadata()

    print(f"Total jobs fetched: {result['total_count']}")
    print(f"Jobs filtered out: {result['filtered_count']}")
    print(f"Jobs extracted: {result['urls_count']}")

    # Access job metadata
    print("\nFirst 3 included jobs:")
    for job in result['included_jobs'][:3]:
        print(f"  {job['title']}")
        print(f"    Location: {job['location']}")
        print(f"    URL: {job['url']}")


def example_with_filters():
    """Example: Using title filters"""
    print("\n" + "=" * 60)
    print("Example 2: With Title Filters")
    print("=" * 60)

    # Configure filters
    filters = TitleFilters(
        include=['software', 'engineer'],
        exclude=['senior staff', 'principal']
    )

    # Get extractor with filters
    extractor = get_extractor(Company.GOOGLE, config=filters)
    result = extractor.extract_source_urls_metadata()

    print(f"Total jobs fetched: {result['total_count']}")
    print(f"Jobs filtered out: {result['filtered_count']}")
    print(f"Jobs extracted: {result['urls_count']}")


def example_all_companies():
    """Example: Extract from all companies"""
    print("\n" + "=" * 60)
    print("Example 3: All Companies")
    print("=" * 60)

    # Get all supported companies
    companies = list_companies()
    print(f"Supported companies: {', '.join(companies)}\n")

    # Extract from each company
    for company_name in companies:
        extractor = get_extractor(company_name)
        result = extractor.extract_source_urls_metadata()

        print(f"✓ {company_name.upper():12} | "
              f"Total: {result['total_count']:3} | "
              f"Filtered: {result['filtered_count']:3} | "
              f"URLs: {result['urls_count']:3}")


def example_specific_companies():
    """Example: Extract from specific companies"""
    print("\n" + "=" * 60)
    print("Example 4: Specific Companies")
    print("=" * 60)

    # Configure common filters
    filters = TitleFilters(
        include=['software', 'engineer'],
        exclude=['intern', 'early career']
    )

    # Target specific companies
    target_companies = [Company.GOOGLE, Company.AMAZON, Company.ANTHROPIC]

    for company in target_companies:
        extractor = get_extractor(company, config=filters)
        result = extractor.extract_source_urls_metadata()

        print(f"\n{company.value.upper()}:")
        print(f"  Total jobs: {result['total_count']}")
        print(f"  After filtering: {result['urls_count']}")

        # Show sample jobs
        if result['included_jobs']:
            print(f"  Sample jobs:")
            for job in result['included_jobs'][:2]:
                print(f"    - {job['title']} ({job['location']})")


def example_direct_import():
    """Example: Direct import (not recommended)"""
    print("\n" + "=" * 60)
    print("Example 5: Direct Import (Alternative)")
    print("=" * 60)

    # You can also import extractors directly
    from extractors.google import GoogleExtractor

    filters = TitleFilters(exclude=['senior staff'])
    extractor = GoogleExtractor(config=filters)
    result = extractor.extract_source_urls_metadata()

    print(f"Google jobs extracted: {result['urls_count']}")
    print("Note: Using registry (get_extractor) is recommended for consistency")


def example_access_raw_data():
    """Example: Access raw API response data"""
    print("\n" + "=" * 60)
    print("Example 6: Accessing Raw Response Data")
    print("=" * 60)

    extractor = get_extractor(Company.TIKTOK)
    result = extractor.extract_source_urls_metadata()

    print(f"TikTok jobs: {result['urls_count']}")

    # Access first job's data
    if result['included_jobs']:
        first_job = result['included_jobs'][0]
        print(f"\nFirst job: {first_job['title']}")
        print(f"Location (parsed): {first_job['location']}")
        print(f"URL: {first_job['url']}")

        # Note: response_data is available during _fetch_all_jobs() for debugging
        # but not included in the returned metadata for API efficiency
        print("\nNote: Raw response_data available during _fetch_all_jobs() for debugging")


if __name__ == '__main__':
    print("=" * 60)
    print("Job URL Extractor - Usage Examples")
    print("=" * 60)

    # Uncomment examples to run:

    # example_basic()
    # example_with_filters()
    # example_all_companies()
    # example_specific_companies()
    # example_direct_import()
    # example_access_raw_data()

    print("\nNote: Examples are commented out. Uncomment to run specific examples.")
    print("To test all extractors, use: src/api/test_sourcing.py")
