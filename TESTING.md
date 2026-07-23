# Testing Patterns for Async CLI Applications

This document describes testing strategies for async code using Python's built-in `unittest.IsolatedAsyncioTestCase` (Python 3.8+).

## Why unittest.IsolatedAsyncioTestCase?

- **No external dependencies**: Built into Python 3.8+
- **Async support**: Properly handles `async def` test methods
- **Event loop management**: Automatic setup/teardown of event loop per test
- **Simple migration**: Familiar `unittest` API with async support

Compared to pytest:
- Fewer dependencies to maintain
- No need for `@pytest.mark.asyncio` decorators
- Cleaner test isolation

## Basic Pattern

```python
import unittest

class TestAsync(unittest.IsolatedAsyncioTestCase):
    """Test class for async code."""

    async def test_async_function(self) -> None:
        """Test an async function."""
        result = await some_async_function()
        self.assertEqual(result, expected_value)
```

## Testing Async HTTP Clients

### Mocking HTTP Responses

Use `unittest.mock.patch` with return values:

```python
from unittest.mock import patch

class TestGetResponse(unittest.IsolatedAsyncioTestCase):
    async def test_successful_response(self) -> None:
        """Test successful HTTP response."""
        expected_data = {"status": "success"}

        with patch("module.get_response") as mock_get:
            mock_get.return_value = expected_data

            result = await get_response(url="https://api.example.com")

            self.assertEqual(result, expected_data)

    async def test_404_returns_none(self) -> None:
        """Test 404 error handling."""
        with patch("module.get_response") as mock_get:
            mock_get.return_value = None

            result = await get_response(url="https://api.example.com/404")

            self.assertIsNone(result)
```

### Mocking Paginated Results

```python
class TestPagination(unittest.IsolatedAsyncioTestCase):
    async def test_pagination_with_limit(self) -> None:
        """Test pagination stops at result_limit."""
        entries = [{"id": i} for i in range(30)]

        def mock_get_response_side_effect(*args, **kwargs):
            page = kwargs.get("params", {}).get("page", 1)
            page_size = kwargs.get("params", {}).get("pageSize", 10)

            if page == 1:
                return {"results": entries[0:10], "info": {"next": "page2"}}
            elif page == 2:
                return {"results": entries[10:20], "info": {"next": "page3"}}
            elif page == 3:
                return {"results": entries[20:30], "info": {"next": None}}
            return {"results": [], "info": {}}

        with patch(
            "module.get_response",
            side_effect=mock_get_response_side_effect,
        ):
            results = []
            async for result in list_results_paginated(
                url="https://api.example.com",
                result_limit=15,
                page_size=10,
            ):
                results.append(result)

            # Verify we stopped at limit
            self.assertEqual(len(results), 15)
```

**Key points:**
- Use `side_effect` for functions with conditional logic
- Return proper response structure matching your API
- Test boundary conditions (limits, empty results, etc.)

## Testing Queue-Based Coordination

```python
class TestQueueCoordination(unittest.IsolatedAsyncioTestCase):
    async def test_queue_operations(self) -> None:
        """Test asyncio.Queue usage."""
        from asyncio import Queue

        q = Queue()
        expected_items = [{"id": 1}, {"id": 2}]

        # Producer: Put items in queue
        for item in expected_items:
            await q.put(item)

        # Consumer: Get items from queue
        retrieved_items = []
        for _ in expected_items:
            item = await q.get()
            retrieved_items.append(item)

        self.assertEqual(retrieved_items, expected_items)

    async def test_empty_queue(self) -> None:
        """Test handling of empty queue."""
        from asyncio import Queue

        q = Queue()

        self.assertTrue(q.empty())
        self.assertEqual(q.qsize(), 0)
```

## Testing Output Formatting

### Testing JSON Output

```python
import json
from io import StringIO
from unittest.mock import patch

class TestJsonOutput(unittest.IsolatedAsyncioTestCase):
    async def test_json_array_formatting(self) -> None:
        """Test JSON array output structure."""
        from asyncio import Queue

        q = Queue()
        entries = [{"id": 1, "name": "Item1"}, {"id": 2, "name": "Item2"}]

        for entry in entries:
            await q.put(entry)

        # Simulate contributing_tasks
        from module import contributing_tasks
        contributing_tasks.clear()
        contributing_tasks.append("test_task")

        output = StringIO()

        with patch("sys.stdout", output):
            await json_out(q)

        result = output.getvalue()

        # Verify valid JSON array structure
        self.assertTrue(result.strip().startswith("["))
        self.assertTrue(result.strip().endswith("]"))

        # Verify it parses as valid JSON
        parsed = json.loads(result)
        self.assertEqual(len(parsed), 2)
```

## Testing CLI Argument Parsing

CLI arguments don't require async tests:

```python
class TestCLIArgumentParsing(unittest.TestCase):
    """Synchronous tests for argument parsing."""

    def test_required_arguments(self) -> None:
        """Test required arguments validation."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--username", required=True)
        parser.add_argument("--password", required=True)

        with self.assertRaises(SystemExit):
            parser.parse_args([])

    def test_json_proxies_parsing(self) -> None:
        """Test JSON proxy string parsing."""
        import json

        proxies_json = '{"http": "http://proxy:8080"}'
        proxies = json.loads(proxies_json)

        self.assertEqual(proxies["http"], "http://proxy:8080")

    def test_invalid_json_raises_error(self) -> None:
        """Test invalid JSON raises JSONDecodeError."""
        import json

        with self.assertRaises(json.JSONDecodeError):
            json.loads('{"incomplete')
```

## Common Assertions for Async Tests

```python
class TestCommonAssertions(unittest.IsolatedAsyncioTestCase):
    async def test_assertions(self) -> None:
        """Examples of common assertions."""

        # Equality
        self.assertEqual(actual, expected)
        self.assertNotEqual(actual, unexpected)

        # Boolean
        self.assertTrue(condition)
        self.assertFalse(condition)

        # None checks
        self.assertIsNone(value)
        self.assertIsNotNone(value)

        # Membership
        self.assertIn(item, container)
        self.assertNotIn(item, container)

        # Type checks
        self.assertIsInstance(value, MyClass)

        # Exceptions
        with self.assertRaises(ValueError):
            raise_error()

        # Dictionary/list assertions
        self.assertDictEqual(dict1, dict2)
        self.assertListEqual(list1, list2)
        self.assertEqual(len(items), 5)
```

## Test Structure Best Practices

### Organize by Functionality

```python
class TestGetResponse(unittest.IsolatedAsyncioTestCase):
    """Group tests for single function."""
    # Tests for get_response()

class TestListResults(unittest.IsolatedAsyncioTestCase):
    """Group tests for single function."""
    # Tests for list_results()

class TestPagination(unittest.IsolatedAsyncioTestCase):
    """Group tests for feature."""
    # Multiple related tests
```

### Test Coverage

Run tests with coverage reporting:

```bash
# Run all tests
python -m unittest discover test/

# With coverage
coverage run -m unittest discover test/
coverage report -m
coverage html
```

**Target**: Aim for 80%+ coverage on new code.

### Test Naming

Use descriptive names:

```python
async def test_pagination_respects_result_limit(self) -> None:
    """Test that pagination stops at result_limit."""
    # ...

async def test_empty_response_returns_empty_list(self) -> None:
    """Test handling of empty API responses."""
    # ...

async def test_404_returns_none(self) -> None:
    """Test 404 error returns None instead of raising."""
    # ...
```

## Running Tests

```bash
# Discover and run all tests
python -m unittest discover test/

# Run specific test class
python -m unittest test.unit.test_client.TestGetResponse

# Run specific test method
python -m unittest test.unit.test_client.TestGetResponse.test_get_response_success

# Verbose output
python -m unittest discover test/ -v

# Show skipped tests
python -m unittest discover test/ -v 2>&1 | grep -i skip
```

## Type Hints in Tests

Use type hints for clarity:

```python
class TestTyped(unittest.IsolatedAsyncioTestCase):
    async def test_typed_function(self) -> None:
        """Test with clear types."""
        expected: dict[str, int] = {"count": 5}
        result: dict[str, int] = await get_counts()

        self.assertEqual(result, expected)

    def test_json_parsing(self) -> None:
        """Type hints for sync tests too."""
        json_str: str = '{"key": "value"}'
        parsed: dict[str, str] = json.loads(json_str)

        self.assertEqual(parsed["key"], "value")
```

## Examples

See `test/unit/` directory for complete test examples:
- `test_client.py` - HTTP client and pagination tests
- `test_parser.py` - JSON output formatting tests
- `test_cli.py` - CLI argument parsing tests

## Debugging Async Tests

### Print debugging

```python
async def test_debug(self) -> None:
    result = await some_function()
    print(f"Debug: result = {result}")
    self.assertEqual(result, expected)
```

Run with verbose output:
```bash
python -m unittest test.unit.test_client -v
```

### Using pdb (debugger)

```python
import pdb

async def test_debug(self) -> None:
    result = await some_function()
    pdb.set_trace()  # Breakpoint
    self.assertEqual(result, expected)
```

Run single test:
```bash
python -m unittest test.unit.test_client.TestGetResponse.test_specific
```

## Performance Testing

```python
import time

class TestPerformance(unittest.IsolatedAsyncioTestCase):
    async def test_pagination_performance(self) -> None:
        """Test pagination performance."""
        start = time.time()

        count = 0
        async for result in list_results_paginated(...):
            count += 1

        elapsed = time.time() - start

        # Assert acceptable performance
        self.assertLess(elapsed, 5.0, f"Took {elapsed}s, expected <5s")
```

## Further Reading

- [unittest documentation](https://docs.python.org/3/library/unittest.html)
- [asyncio documentation](https://docs.python.org/3/library/asyncio.html)
- See `PATTERNS.md` for async patterns used in production code
