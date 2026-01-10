#!/usr/bin/env python3
"""
Live validation script for SimHash content deduplication.

Fetches real job pages 3 times with 1s backoff between requests,
computes SimHash for each fetch, and validates that repeated fetches
produce similar hashes (Hamming distance <= 3).

Usage:
    cd backend
    python3 utils/test_simhash_live.py google
    python3 utils/test_simhash_live.py amazon
    python3 utils/test_simhash_live.py --all
"""

import asyncio
import argparse
import time
import sys

# Add parent directory to path for imports
sys.path.insert(0, '/Users/duan/coding/jh/backend')

from extractors import get_extractor, list_companies
from extractors.config import TitleFilters
from utils.simhash import compute_simhash, hamming_distance, is_similar


async def get_sample_url(company: str) -> str | None:
    """Get a sample job URL for a company."""
    try:
        extractor = get_extractor(company, config=TitleFilters())
    except ValueError as e:
        print(f"ERROR: {e}")
        return None

    result = await extractor.extract_source_urls_metadata()

    if not result['included_jobs']:
        print(f"No jobs found for {company}")
        return None

    return result['included_jobs'][0]['url']


async def fetch_and_hash(extractor, url: str) -> tuple[str, int]:
    """Fetch content and compute SimHash."""
    raw_content = await extractor.crawl_raw_info(url)
    simhash = compute_simhash(raw_content)
    return raw_content, simhash


async def validate_simhash_for_company(company: str, num_fetches: int = 3, backoff_secs: float = 1.0) -> bool:
    """
    Validate SimHash for a company by fetching the same URL multiple times.

    Returns True if all fetches produce similar hashes (within threshold).
    """
    print(f"\n{'=' * 60}")
    print(f"Validating SimHash for: {company.upper()}")
    print(f"{'=' * 60}")

    # Get a sample URL
    print(f"\n1. Getting sample URL...")
    url = await get_sample_url(company)
    if not url:
        print(f"   SKIP: Could not get sample URL for {company}")
        return False
    print(f"   URL: {url}")

    # Create extractor
    extractor = get_extractor(company, config=TitleFilters())

    # Fetch N times with backoff
    results = []
    print(f"\n2. Fetching {num_fetches} times with {backoff_secs}s backoff...")

    for i in range(num_fetches):
        if i > 0:
            print(f"   Waiting {backoff_secs}s...")
            time.sleep(backoff_secs)

        print(f"   Fetch #{i + 1}...", end=" ")
        try:
            content, simhash = await fetch_and_hash(extractor, url)
            results.append({
                'fetch': i + 1,
                'content_len': len(content),
                'simhash': simhash,
            })
            print(f"OK ({len(content)} chars, hash={simhash})")
        except Exception as e:
            print(f"ERROR: {e}")
            return False

    # Compare hashes
    print(f"\n3. Comparing SimHash values...")
    print(f"   {'Fetch':<8} {'Content Len':<15} {'SimHash (hex)':<20}")
    print(f"   {'-' * 8} {'-' * 15} {'-' * 20}")
    for r in results:
        print(f"   {r['fetch']:<8} {r['content_len']:<15} {hex(r['simhash']):<20}")

    # Calculate all pairwise distances
    print(f"\n4. Pairwise Hamming distances:")
    all_similar = True
    for i in range(len(results)):
        for j in range(i + 1, len(results)):
            h1 = results[i]['simhash']
            h2 = results[j]['simhash']
            dist = hamming_distance(h1, h2)
            similar = is_similar(h1, h2, threshold=3)
            status = "SIMILAR" if similar else "DIFFERENT"
            if not similar:
                all_similar = False
            print(f"   Fetch #{i + 1} vs #{j + 1}: distance={dist} ({status})")

    # Summary
    print(f"\n5. Result: ", end="")
    if all_similar:
        print("PASS - All fetches produced similar hashes")
    else:
        print("FAIL - Some fetches produced different hashes")
        print("   This may indicate:")
        print("   - Dynamic content (timestamps, session IDs, etc.)")
        print("   - A/B testing on the page")
        print("   - High threshold needed for this content type")

    return all_similar


async def main():
    parser = argparse.ArgumentParser(
        description="Validate SimHash with live job page fetches",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        'company',
        nargs='?',
        help='Company name (e.g., google, amazon)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Test all available companies'
    )
    parser.add_argument(
        '-n', '--num-fetches',
        type=int,
        default=3,
        help='Number of times to fetch each URL (default: 3)'
    )
    parser.add_argument(
        '-b', '--backoff',
        type=float,
        default=1.0,
        help='Seconds to wait between fetches (default: 1.0)'
    )

    args = parser.parse_args()

    if not args.company and not args.all:
        parser.print_help()
        print(f"\nAvailable companies: {', '.join(list_companies())}")
        return

    companies = list_companies() if args.all else [args.company]

    print(f"SimHash Live Validation")
    print(f"=======================")
    print(f"Companies: {', '.join(companies)}")
    print(f"Fetches per URL: {args.num_fetches}")
    print(f"Backoff: {args.backoff}s")

    results = {}
    for company in companies:
        try:
            passed = await validate_simhash_for_company(
                company,
                num_fetches=args.num_fetches,
                backoff_secs=args.backoff
            )
            results[company] = passed
        except Exception as e:
            print(f"\nERROR testing {company}: {e}")
            results[company] = False

    # Final summary
    print(f"\n{'=' * 60}")
    print(f"SUMMARY")
    print(f"{'=' * 60}")
    for company, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {company:<15} {status}")

    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\nTotal: {passed}/{total} passed")


if __name__ == '__main__':
    asyncio.run(main())
