#!/usr/bin/env python3
"""
Test script for job URL sourcing

Runs sourcing with hardcoded config in dry_run mode and dumps results to JSON.
Usage:
    python -m backend.tests.test_sourcing
"""

import sys
import os
import json
from datetime import datetime

# Add backend to path
backend_path = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, backend_path)

# Add src to path
src_path = os.path.join(os.path.dirname(__file__), '../..')
sys.path.insert(0, src_path)

from sourcing.config import get_user_sourcing_settings
from sourcing.orchestrator import extract_all_companies_sync


def run_sourcing_test():
    """
    Run job URL sourcing with hardcoded config and dump results to JSON
    """
    print("=" * 80)
    print("Job URL Sourcing Test")
    print("=" * 80)
    print()

    # Get hardcoded settings (local testing mode)
    print("Loading hardcoded sourcing settings (local_testing=True)...")
    settings = get_user_sourcing_settings(local_testing=True)
    print(f"Configured {len(settings)} companies: {', '.join([c.value for c in settings.keys()])}")
    print()

    # Run extraction
    print("Running parallel extraction across all companies...")
    print("This may take 30-60 seconds depending on API response times...")
    print()

    results = extract_all_companies_sync(settings)

    # Calculate summary
    total_jobs = sum(r.total_count for r in results)
    total_filtered = sum(r.filtered_count for r in results)
    total_included = sum(r.urls_count for r in results)
    successful = sum(1 for r in results if not r.error)
    failed = sum(1 for r in results if r.error)

    print("Extraction complete!")
    print(f"  Successful: {successful}/{len(results)} companies")
    print(f"  Failed: {failed}/{len(results)} companies")
    print(f"  Total jobs from APIs: {total_jobs}")
    print(f"  Total filtered out: {total_filtered}")
    print(f"  Total included: {total_included}")
    print()

    # Print company-by-company results
    print("Company Results:")
    print("-" * 80)
    for result in results:
        status = "✓" if not result.error else "✗"
        print(f"{status} {result.company.upper():12} | "
              f"Total: {result.total_count:3} | "
              f"Filtered: {result.filtered_count:3} | "
              f"URLs: {result.urls_count:3}")
        if result.error:
            print(f"   Error: {result.error}")
    print("-" * 80)
    print()

    # Convert results to JSON-serializable format
    output = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "summary": {
            "total_companies": len(results),
            "successful_companies": successful,
            "failed_companies": failed,
            "total_jobs": total_jobs,
            "total_filtered_jobs": total_filtered,
            "total_included_jobs": total_included
        },
        "results": [
            {
                "company": r.company,
                "total_count": r.total_count,
                "filtered_count": r.filtered_count,
                "urls_count": r.urls_count,
                "included_jobs": [
                    {
                        "id": job.id,
                        "title": job.title,
                        "location": job.location,
                        "url": job.url
                    }
                    for job in r.included_jobs
                ],
                "excluded_jobs": [
                    {
                        "id": job.id,
                        "title": job.title,
                        "location": job.location,
                        "url": job.url
                    }
                    for job in r.excluded_jobs
                ],
                "error": r.error
            }
            for r in results
        ]
    }

    # Write to JSON file
    output_dir = os.path.join(backend_path, 'tests', 'output')
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(output_dir, f'sourcing_results_{timestamp}.json')

    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"Results saved to: {output_file}")
    print()

    # Show sample jobs from first successful company
    for result in results:
        if result.included_jobs and not result.error:
            print(f"Sample included jobs from {result.company.upper()} (first 5):")
            for job in result.included_jobs[:5]:
                print(f"  - [{job.id}] {job.title}")
                print(f"    Location: {job.location}")
                print(f"    URL: {job.url}")
            print()

            if result.excluded_jobs:
                print(f"Sample excluded jobs from {result.company.upper()} (first 3):")
                for job in result.excluded_jobs[:3]:
                    print(f"  - [{job.id}] {job.title}")
                    print(f"    Location: {job.location}")
                    print(f"    URL: {job.url}")
                print()
            break

    print("=" * 80)
    print("Test complete!")
    print("=" * 80)

    return output


if __name__ == "__main__":
    run_sourcing_test()
