#!/usr/bin/env python3
"""
Example: Paginated Search with Result Limiting

This example demonstrates how to use result_limit and page_size
parameters to control pagination in template_cli.

Key concepts:
- result_limit: Maximum total results to fetch (0 = no limit)
- page_size: Number of results per API page
- Page-size optimization: Automatically reduces page_size if larger than result_limit
"""

import asyncio
from template_cli.client import list_results_paginated


async def example_basic_pagination():
    """Example 1: Fetch results without any limit."""
    print("Example 1: Basic pagination (no limit)")
    print("-" * 50)

    # Fetch all available results (result_limit=0 means no limit)
    count = 0
    async for result in list_results_paginated(
        url="https://rickandmortyapi.com/api/character",
        result_limit=0,  # No limit - fetch all
        page_size=20,     # 20 results per page
    ):
        count += 1
        print(f"  Result {count}: {result.get('name', 'Unknown')}")
        if count >= 5:  # Just show first 5 for demo
            print("  ... (truncated)")
            break

    print(f"Total fetched: {count}\n")


async def example_with_limit():
    """Example 2: Fetch only 10 results total."""
    print("Example 2: Pagination with result_limit=10")
    print("-" * 50)

    # Fetch only 10 results total, even if more are available
    count = 0
    async for result in list_results_paginated(
        url="https://rickandmortyapi.com/api/character",
        result_limit=10,   # Stop after 10 results
        page_size=20,      # Request 20 per page (optimization will reduce to 10)
    ):
        count += 1
        print(f"  Result {count}: {result.get('name', 'Unknown')}")

    print(f"Total fetched: {count} (stopped at limit)\n")


async def example_page_size_optimization():
    """Example 3: Page-size optimization in action."""
    print("Example 3: Page-size optimization")
    print("-" * 50)
    print("Request page_size=100 but result_limit=5")
    print("✓ Optimization: page_size will be reduced to 5")
    print("✓ This saves API bandwidth when you only need a few results\n")

    count = 0
    async for result in list_results_paginated(
        url="https://rickandmortyapi.com/api/character",
        result_limit=5,    # Only need 5 results
        page_size=100,     # Would normally request 100 per page
        # ← Page-size automatically optimized to 5
    ):
        count += 1
        print(f"  Result {count}: {result.get('name', 'Unknown')}")

    print(f"Total fetched: {count}\n")


async def example_with_additional_params():
    """Example 4: Pagination with additional parameters."""
    print("Example 4: Pagination with additional parameters")
    print("-" * 50)

    count = 0
    async for result in list_results_paginated(
        url="https://rickandmortyapi.com/api/character",
        additional_params={"status": "alive"},  # Filter to alive characters
        result_limit=15,
        page_size=10,
    ):
        count += 1
        print(f"  Result {count}: {result.get('name')} - {result.get('status')}")

    print(f"Total fetched: {count} alive characters\n")


async def main():
    """Run all examples."""
    print("=" * 50)
    print("Paginated Search Examples for template_cli")
    print("=" * 50)
    print()

    try:
        await example_basic_pagination()
        await example_with_limit()
        await example_page_size_optimization()
        await example_with_additional_params()
    except Exception as e:
        print(f"Error: {e}")
        print("\nNote: These examples require internet access to rickandmortyapi.com")
        print("They demonstrate the pagination API with a public example service.")


if __name__ == "__main__":
    asyncio.run(main())
