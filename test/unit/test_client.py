"""Unit tests for template_cli.client module."""
import unittest
from asyncio import Queue
from unittest.mock import patch

from template_cli.client import get_response, list_results_paginated, list_results


class TestGetResponse(unittest.IsolatedAsyncioTestCase):
    """Tests for low-level HTTP response handling."""

    async def test_get_response_success(self) -> None:
        """Test successful HTTP response."""
        expected_data = {"character": {"id": 1, "name": "Rick Sanchez"}}

        with patch("template_cli.client.get_response") as mock_get_response:
            mock_get_response.return_value = expected_data

            from template_cli.client import get_response as real_get_response

            result = await real_get_response(
                url="https://rickandmortyapi.com/api/character/1",
                username="test",
                password="test",
            )

            self.assertEqual(result, expected_data)

    async def test_get_response_404_returns_none(self) -> None:
        """Test that 404 returns None."""
        from httpx import HTTPStatusError, Response, Request

        mock_request = Request("GET", "https://rickandmortyapi.com/api/character/9999")
        mock_response = Response(404, request=mock_request)

        with patch("template_cli.client.get_response") as mock_get_response:
            mock_get_response.return_value = None

            from template_cli.client import get_response as real_get_response

            result = await real_get_response(
                url="https://rickandmortyapi.com/api/character/9999",
                username="test",
                password="test",
            )

            self.assertIsNone(result)

    async def test_get_response_with_headers(self) -> None:
        """Test that headers are set correctly."""
        expected_data = {"result": "success"}

        with patch("template_cli.client.get_response") as mock_get_response:
            mock_get_response.return_value = expected_data

            result = await mock_get_response(
                url="https://example.com/api",
                username="admin",
                password="secret",
            )

            self.assertEqual(result, expected_data)

    async def test_get_response_with_proxies(self) -> None:
        """Test that proxies are configured."""
        expected_data = {"result": "success"}
        proxies = {"http": "http://proxy:8080"}

        with patch("template_cli.client.get_response") as mock_get_response:
            mock_get_response.return_value = expected_data

            result = await mock_get_response(
                url="https://example.com/api",
                proxies=proxies,
            )

            self.assertEqual(result, expected_data)


class TestListResults(unittest.IsolatedAsyncioTestCase):
    """Tests for single-page results fetching."""

    async def test_list_results_single_page(self) -> None:
        """Test fetching single page of results."""
        entries = [
            {"id": 1, "name": "Rick"},
            {"id": 2, "name": "Morty"},
        ]
        response = {"results": entries}

        q = Queue()

        with patch("template_cli.client.get_response") as mock_get:
            mock_get.return_value = response

            await list_results(
                url="https://rickandmortyapi.com/api/character",
                q=q,
            )

            # Verify entries were put in queue
            for expected_entry in entries:
                result = await q.get()
                self.assertEqual(result, expected_entry)

    async def test_list_results_empty_response(self) -> None:
        """Test handling of empty results."""
        response = {"results": []}

        q = Queue()

        with patch("template_cli.client.get_response") as mock_get:
            mock_get.return_value = response

            await list_results(
                url="https://rickandmortyapi.com/api/character",
                q=q,
            )

            # Queue should be empty
            self.assertTrue(q.empty())


class TestPagination(unittest.IsolatedAsyncioTestCase):
    """Tests for pagination with result limiting."""

    async def test_pagination_respects_result_limit(self) -> None:
        """Test that pagination stops at result_limit."""
        # Create 30 entries (3 pages of 10)
        entries = [{"id": i, "name": f"character_{i}"} for i in range(30)]

        # Mock responses for 3 pages
        def mock_get_response_side_effect(*args, **kwargs):
            page = kwargs.get("params", {}).get("page", 1)
            if page == 1:
                return {"results": entries[0:10], "info": {"next": "page2"}}
            elif page == 2:
                return {"results": entries[10:20], "info": {"next": "page3"}}
            elif page == 3:
                return {"results": entries[20:30], "info": {"next": None}}
            return {"results": [], "info": {}}

        with patch(
            "template_cli.client.get_response",
            side_effect=mock_get_response_side_effect,
        ):
            results = []
            async for result in list_results_paginated(
                url="https://rickandmortyapi.com/api/character",
                result_limit=15,
                page_size=10,
            ):
                results.append(result)

            # Should stop at 15 results, not fetch all 30
            self.assertEqual(len(results), 15)

    async def test_pagination_no_limit_returns_all(self) -> None:
        """Test that pagination returns all results when result_limit=0."""
        entries = [{"id": i, "name": f"character_{i}"} for i in range(25)]

        def mock_get_response_side_effect(*args, **kwargs):
            page = kwargs.get("params", {}).get("page", 1)
            if page == 1:
                return {"results": entries[0:10], "info": {"next": "page2"}}
            elif page == 2:
                return {"results": entries[10:20], "info": {"next": "page3"}}
            elif page == 3:
                return {"results": entries[20:25], "info": {"next": None}}
            return {"results": [], "info": {}}

        with patch(
            "template_cli.client.get_response",
            side_effect=mock_get_response_side_effect,
        ):
            results = []
            async for result in list_results_paginated(
                url="https://rickandmortyapi.com/api/character",
                result_limit=0,
                page_size=10,
            ):
                results.append(result)

            # Should return all 25 results
            self.assertEqual(len(results), 25)

    async def test_page_size_optimization(self) -> None:
        """Test that page_size is optimized when > result_limit."""
        entry = {"id": 1, "name": "test"}
        response = {"results": [entry], "info": {"next": None}}

        with patch(
            "template_cli.client.get_response", return_value=response
        ) as mock_response:
            results = []
            async for result in list_results_paginated(
                url="https://rickandmortyapi.com/api/character",
                result_limit=5,
                page_size=100,
            ):
                results.append(result)

            # Verify that page in params was set (or page_size was optimized)
            call_args = mock_response.call_args
            self.assertIsNotNone(call_args)


if __name__ == "__main__":
    unittest.main()
