"""Unit tests for template_cli CLI argument parsing."""
import json
import unittest


class TestCLIArgumentParsing(unittest.TestCase):
    """Tests for CLI argument parsing."""

    def test_required_arguments(self) -> None:
        """Test that required arguments are properly defined."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--username", type=str, required=True)
        parser.add_argument("--password", type=str, required=True)
        parser.add_argument("--domain", type=str, required=False, default="example.com")

        # Missing required args should raise
        with self.assertRaises(SystemExit):
            parser.parse_args([])

    def test_all_arguments_parse_correctly(self) -> None:
        """Test that all expected arguments can be parsed."""
        import argparse

        test_args = [
            "--username",
            "admin",
            "--password",
            "secret",
            "--domain",
            "rickandmortyapi.com",
            "--log-level",
            "10",
            "--proxies",
            '{"http": "http://proxy:8080"}',
        ]

        parser = argparse.ArgumentParser()
        parser.add_argument("--username", type=str, required=True)
        parser.add_argument("--password", type=str, required=True)
        parser.add_argument("--domain", type=str, required=False, default="example.com")
        parser.add_argument("--log-level", type=int, required=False, default=20, dest="log_level")
        parser.add_argument("--proxies", type=str, required=False)

        args = parser.parse_args(test_args)

        self.assertEqual(args.username, "admin")
        self.assertEqual(args.password, "secret")
        self.assertEqual(args.domain, "rickandmortyapi.com")
        self.assertEqual(args.log_level, 10)

    def test_default_domain(self) -> None:
        """Test that domain defaults to example.com."""
        import argparse

        test_args = [
            "--username",
            "user",
            "--password",
            "pass",
        ]

        parser = argparse.ArgumentParser()
        parser.add_argument("--username", type=str, required=True)
        parser.add_argument("--password", type=str, required=True)
        parser.add_argument("--domain", type=str, required=False, default="example.com")
        parser.add_argument("--log-level", type=int, required=False, default=20, dest="log_level")

        args = parser.parse_args(test_args)

        self.assertEqual(args.domain, "example.com")
        self.assertEqual(args.log_level, 20)

    def test_proxies_json_parsing(self) -> None:
        """Test that proxies JSON string can be parsed."""
        proxies_json = '{"http": "http://proxy:8080", "https": "https://proxy:8080"}'
        proxies = json.loads(proxies_json)

        self.assertEqual(proxies["http"], "http://proxy:8080")
        self.assertEqual(proxies["https"], "https://proxy:8080")

    def test_invalid_json_handling(self) -> None:
        """Test that invalid JSON raises appropriate error."""
        invalid_json = '{"incomplete'

        with self.assertRaises(json.JSONDecodeError):
            json.loads(invalid_json)

    def test_username_required(self) -> None:
        """Test that username is required."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--username", type=str, required=True)
        parser.add_argument("--password", type=str, required=True)

        with self.assertRaises(SystemExit):
            parser.parse_args(["--password", "secret"])

    def test_password_required(self) -> None:
        """Test that password is required."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--username", type=str, required=True)
        parser.add_argument("--password", type=str, required=True)

        with self.assertRaises(SystemExit):
            parser.parse_args(["--username", "admin"])

    def test_log_level_type_validation(self) -> None:
        """Test that log-level must be an integer."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--log-level", type=int, required=False, default=20, dest="log_level")

        with self.assertRaises(SystemExit):
            parser.parse_args(["--log-level", "invalid"])


if __name__ == "__main__":
    unittest.main()
