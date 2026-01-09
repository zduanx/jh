#!/usr/bin/env python3
"""
Test script for raw info crawling and extraction.

Usage:
    cd backend

    # Get sample URLs for a company (up to 5)
    python3 extractors/test_extractor_raw.py urls <company>
    python3 extractors/test_extractor_raw.py urls google

    # Crawl raw info from a URL
    python3 extractors/test_extractor_raw.py crawl <company> <url>
    python3 extractors/test_extractor_raw.py crawl google "https://..."

    # Extract description/requirements from a URL (crawl + extract)
    python3 extractors/test_extractor_raw.py extract <company> <url>
    python3 extractors/test_extractor_raw.py extract google "https://..."

Available companies: google, tiktok, amazon, anthropic, netflix, roblox
"""

import asyncio
import argparse
from extractors import get_extractor, list_companies
from extractors.config import TitleFilters


async def get_sample_urls(company: str, limit: int = 5) -> None:
    """Get up to N sample job URLs for a company."""
    print(f"Getting sample URLs for {company}...")

    try:
        extractor = get_extractor(company, config=TitleFilters())
    except ValueError as e:
        print(f"ERROR: {e}")
        print(f"Available companies: {', '.join(list_companies())}")
        return

    result = await extractor.extract_source_urls_metadata()

    if not result['included_jobs']:
        print(f"No jobs found for {company}")
        return

    print(f"\nFound {result['urls_count']} jobs (showing up to {limit}):\n")

    for i, job in enumerate(result['included_jobs'][:limit]):
        print(f"{i + 1}. {job['title']}")
        print(f"   Location: {job['location']}")
        print(f"   URL: {job['url']}")
        print()


async def crawl_raw_info(company: str, url: str) -> str | None:
    """Crawl raw info from a job URL."""
    print(f"Crawling raw info for {company}...")
    print(f"URL: {url}\n")

    try:
        extractor = get_extractor(company, config=TitleFilters())
    except ValueError as e:
        print(f"ERROR: {e}")
        print(f"Available companies: {', '.join(list_companies())}")
        return None

    try:
        raw_content = await extractor.crawl_raw_info(url)
    except Exception as e:
        print(f"ERROR: {e}")
        return None

    print(f"Content length: {len(raw_content)} chars")
    print(f"\nPreview (first 1000 chars):\n{'-' * 50}")
    print(raw_content[:1000])
    print(f"{'-' * 50}")

    return raw_content


async def extract_info(company: str, url: str) -> None:
    """Extract description and requirements from a job URL."""
    print(f"Extracting info for {company}...")
    print(f"URL: {url}\n")

    try:
        extractor = get_extractor(company, config=TitleFilters())
    except ValueError as e:
        print(f"ERROR: {e}")
        print(f"Available companies: {', '.join(list_companies())}")
        return

    # Step 1: Crawl
    print("Step 1: Crawling raw content...")
    try:
        raw_content = await extractor.crawl_raw_info(url)
    except Exception as e:
        print(f"ERROR during crawl: {e}")
        return

    print(f"  Content: {len(raw_content)} chars")

    # Step 2: Extract
    print("\nStep 2: Extracting structured info...")
    try:
        extracted = extractor.extract_raw_info(raw_content)
    except ValueError as e:
        print(f"ERROR during extraction: {e}")
        return
    except NotImplementedError:
        print(f"ERROR: extract_raw_info() not implemented for {company}")
        print("This company extractor needs to implement the extract_raw_info() method.")
        return

    # Display results
    print(f"\n{'=' * 60}")
    print("EXTRACTED INFO")
    print(f"{'=' * 60}")

    desc = extracted.get('description', '')
    req = extracted.get('requirements', '')

    print(f"\nDescription ({len(desc)} chars):")
    print(f"{'-' * 40}")
    if desc:
        # Show first 500 chars
        print(desc[:500])
        if len(desc) > 500:
            print(f"\n... [{len(desc) - 500} more chars]")
    else:
        print("(empty)")

    print(f"\nRequirements ({len(req)} chars):")
    print(f"{'-' * 40}")
    if req:
        # Show first 500 chars
        print(req[:500])
        if len(req) > 500:
            print(f"\n... [{len(req) - 500} more chars]")
    else:
        print("(empty)")

    print(f"\n{'=' * 60}")
    print("Test completed!")


def main():
    parser = argparse.ArgumentParser(
        description="Test extractor raw info features",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    # urls command
    urls_parser = subparsers.add_parser('urls', help='Get sample URLs for a company')
    urls_parser.add_argument('company', help='Company name (e.g., google, tiktok)')
    urls_parser.add_argument('-n', '--limit', type=int, default=5, help='Max URLs to show')

    # crawl command
    crawl_parser = subparsers.add_parser('crawl', help='Crawl raw info from a URL')
    crawl_parser.add_argument('company', help='Company name')
    crawl_parser.add_argument('url', help='Job URL to crawl')

    # extract command
    extract_parser = subparsers.add_parser('extract', help='Extract description/requirements')
    extract_parser.add_argument('company', help='Company name')
    extract_parser.add_argument('url', help='Job URL to extract from')

    args = parser.parse_args()

    if args.command == 'urls':
        asyncio.run(get_sample_urls(args.company, args.limit))
    elif args.command == 'crawl':
        asyncio.run(crawl_raw_info(args.company, args.url))
    elif args.command == 'extract':
        asyncio.run(extract_info(args.company, args.url))


if __name__ == '__main__':
    main()
