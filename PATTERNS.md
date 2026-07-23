# Reusable Patterns for CLI Query Tools

This document describes patterns for building CLI tools that query APIs with pagination, authentication, and async/concurrent patterns.

## 1. Pagination with Result Limiting

### Problem
API endpoints often return large result sets across multiple pages. You may need to:
- Fetch a limited number of results for testing/sampling
- Reduce API calls when only partial data is needed
- Optimize page size based on actual requirements

### Pattern: `list_results_paginated()`

```python
async def list_results_paginated(
    url: str,
    additional_params: Optional[dict] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    proxies: Optional[dict] = None,
    result_limit: int = 0,        # Max results to yield (0 = no limit)
    page_size: int = 100,         # Results per API page
) -> AsyncGenerator[dict, None]:
    """Yield individual results from paginated API endpoint.

    Key features:
    - Automatically stops at result_limit (if > 0)
    - Optimizes page_size if result_limit < page_size
    - Handles pagination tokens/page numbers
    """
```

### Page-Size Optimization

When `result_limit` is smaller than `page_size`, automatically reduce `page_size`:

```python
# Optimize page_size if result_limit is set and smaller
effective_page_size = page_size
if result_limit > 0 and page_size > result_limit:
    effective_page_size = result_limit
```

**Benefits:**
- Reduces API bandwidth when only partial results needed
- Single API call instead of multiple when fetching small result sets
- Transparent to caller

### Result Tracking

Track yielded results and stop iteration at limit:

```python
results_yielded: int = 0

for result in results:
    if result_limit > 0 and results_yielded >= result_limit:
        should_continue = False
        break

    yield result
    results_yielded += 1
```

### Usage Examples

See `examples/paginated_search.py` for complete runnable examples:

```python
# Fetch all results (no limit)
async for result in list_results_paginated(
    url="https://api.example.com/data",
    result_limit=0,    # No limit
    page_size=20,
):
    process(result)

# Fetch only 100 results
async for result in list_results_paginated(
    url="https://api.example.com/data",
    result_limit=100,  # Stop after 100
    page_size=50,
):
    process(result)

# Fetch with optimization (page_size reduced to match limit)
async for result in list_results_paginated(
    url="https://api.example.com/data",
    result_limit=10,
    page_size=100,     # Automatically reduced to 10
):
    process(result)
```

## 2. HTTP Client with Automatic Retry

### Problem
Network requests can fail due to transient issues (timeouts, temporary unavailability). Manual retry logic is error-prone.

### Pattern: Decorator-based Retry

```python
from retry_async import retry
import logging

@retry(
    exceptions=Exception,
    tries=3,                    # Number of attempts
    delay=1,                    # Initial delay (seconds)
    backoff=2,                  # Backoff multiplier
    max_delay=5,               # Maximum delay between retries
    logger=logger,
    is_async=True,
)
async def get_response(url: str, **kwargs) -> Optional[dict]:
    """Fetch and parse JSON response with automatic retry."""
    async with AsyncClient() as session:
        response = await session.get(url, **kwargs)
        response.raise_for_status()
        return response.json()
```

**Benefits:**
- Automatic exponential backoff
- Transparent to caller
- Logging of retry attempts
- Configurable retry strategy

## 3. Authentication Patterns

### Basic HTTP Authentication

```python
import base64

if username and password:
    credentials = base64.b64encode(
        f'{username}:{password}'.encode()
    ).decode()
    session.headers.update({
        'Authorization': f'Basic {credentials}'
    })
```

### Proxy Support

```python
if isinstance(proxies, dict):
    session.proxies = proxies
```

## 4. Async Queue Coordination

### Problem
Coordinating between concurrent producers (fetchers) and consumers (parsers/writers) requires careful synchronization.

### Pattern: Producer/Consumer with Queue

```python
from asyncio import Queue, get_running_loop

# Producer: Fetch results and enqueue them
async def fetch_and_enqueue(url: str, q: Queue) -> None:
    results = await get_response(url)
    for result in results:
        await q.put(result)

# Consumer: Process enqueued results
async def process_from_queue(q: Queue) -> None:
    while True:
        result = await q.get()
        process(result)
        q.task_done()

# Main: Create concurrent tasks
async def main():
    q = Queue()

    fetch_task = asyncio.create_task(
        fetch_and_enqueue(url, q)
    )
    process_task = asyncio.create_task(
        process_from_queue(q)
    )

    await asyncio.gather(fetch_task, process_task)
```

**Benefits:**
- Decouples producers and consumers
- Automatic backpressure (queue size bounds memory)
- Simple synchronization primitive

### Task Tracking Pattern

Track contributing tasks to know when all work is complete:

```python
from typing import List

contributing_tasks: List[str] = []

# When starting a task
task = loop.create_task(some_async_function())
contributing_tasks.append(task.get_name())

# When task completes
task.add_done_callback(
    lambda t: contributing_tasks.pop(
        contributing_tasks.index(t.get_name())
    )
)

# Check if work is complete
while contributing_tasks:
    # Still work in progress
    await asyncio.sleep(0.1)
```

## 5. Search Parameter Flexibility

### Problem
Different APIs have different parameter names and defaults. Making these configurable improves reusability.

### Pattern: Configurable Additional Parameters

```python
async def search(
    url: str,
    attributes: Optional[str] = None,
    scope: str = "sub",                # Sensible default
    context: Optional[str] = None,
    return_mode: Optional[str] = None,
    additional_params: Optional[dict] = None,
) -> AsyncGenerator[dict, None]:
    """Generic search with flexible parameters.

    Args:
        attributes: Comma-separated attribute list
        scope: Search scope (sub, onelevel, base)
        context: Search context/base DN
        return_mode: Result format (standard, extended, etc.)
        additional_params: Extra API-specific parameters
    """
    params = {}
    if attributes:
        params['attributes'] = attributes
    params['scope'] = scope
    if context:
        params['context'] = context
    if return_mode:
        params['returnMode'] = return_mode

    if isinstance(additional_params, dict):
        params.update(additional_params)

    async for result in list_results_paginated(
        url, additional_params=params
    ):
        yield result
```

**Usage:**
```python
# Custom search with flexible parameters
async for result in search(
    url="https://api.example.com/search",
    attributes="cn,mail,phone",
    scope="sub",
    context="ou=users,dc=example,dc=com",
):
    process(result)
```

## 6. JSON Output Formatting

### Pattern: Valid JSON Array Output

When streaming results to JSON, maintain valid array syntax:

```python
async def json_out(q: Queue) -> None:
    """Output queue contents as valid JSON array."""
    endl = ''  # No comma before first item
    print('[')

    while True:
        result = await q.get()
        if result:
            # Prepend comma from previous line
            print(f'{endl}{json.dumps(result, indent=4)}', end='')
            endl = ',\n'  # Next line starts with comma

    print('\n]')
```

**Output format:**
```json
[
    {"id": 1, "name": "Item 1"},
    {"id": 2, "name": "Item 2"}
]
```

## Testing Patterns

See `TESTING.md` for comprehensive async test patterns using `unittest.IsolatedAsyncioTestCase`.

## Examples

Complete runnable examples are provided in `examples/`:
- `examples/paginated_search.py` - Pagination and result limiting in action

## References

- See `template_cli/client.py` for production implementations
- See `test/unit/` for comprehensive test examples
- See `TESTING.md` for async testing patterns
