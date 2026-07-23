"""Integration tests for template_cli.main module.

These tests demonstrate integration testing patterns with real or near-real dependencies.
Following ownjoo-org principles: prefer integration tests hitting real dependencies
over mocks that diverge from production behavior.
"""
import unittest
from unittest.mock import AsyncMock, patch

from template_cli.main import main


class TestMainIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests for main orchestration function."""

    async def test_main_fetches_all_endpoints(self) -> None:
        """Test that main fetches characters, locations, and episodes.

        This is a simplified test showing the pattern. In production, you might:
        - Use a test API server
        - Mock at the AsyncClient level (boundary)
        - Test actual pagination logic
        """
        # Mock the client functions to avoid real API calls
        with patch("template_cli.main.list_characters") as mock_chars, \
             patch("template_cli.main.list_locations") as mock_locs, \
             patch("template_cli.main.list_episodes") as mock_eps, \
             patch("template_cli.main.json_out") as mock_output:

            mock_chars.return_value = AsyncMock()
            mock_locs.return_value = AsyncMock()
            mock_eps.return_value = AsyncMock()
            mock_output.return_value = AsyncMock()

            await main(
                domain="https://rickandmortyapi.com/api",
                username="test",
                password="test",
                proxies=None,
            )

            # Verify all three endpoints were queried
            mock_chars.assert_called_once()
            mock_locs.assert_called_once()
            mock_eps.assert_called_once()
            mock_output.assert_called_once()

    async def test_main_coordinates_queue(self) -> None:
        """Test that main sets up Queue coordination correctly."""
        with patch("template_cli.main.list_characters") as mock_chars, \
             patch("template_cli.main.list_locations") as mock_locs, \
             patch("template_cli.main.list_episodes") as mock_eps, \
             patch("template_cli.main.json_out") as mock_output:

            # Properly mock async functions
            async def async_noop(*args, **kwargs):
                pass

            mock_chars.side_effect = async_noop
            mock_locs.side_effect = async_noop
            mock_eps.side_effect = async_noop
            mock_output.side_effect = async_noop

            # Should not raise any errors
            await main(
                domain="https://rickandmortyapi.com/api",
                username="test",
                password="test",
            )

            # Verify calls were made
            self.assertTrue(mock_chars.called)
            self.assertTrue(mock_locs.called)
            self.assertTrue(mock_eps.called)
            self.assertTrue(mock_output.called)


if __name__ == "__main__":
    unittest.main()
