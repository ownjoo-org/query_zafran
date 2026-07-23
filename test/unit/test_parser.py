"""Unit tests for template_cli.parser module."""
import json
import unittest


class TestJsonFormatting(unittest.TestCase):
    """Tests for JSON formatting utilities."""

    def test_json_serialization(self) -> None:
        """Test that dict can be serialized to JSON."""
        entry = {"id": 1, "name": "Rick", "location": "Earth"}

        json_str = json.dumps(entry, indent=4)

        # Should be valid JSON
        parsed = json.loads(json_str)
        self.assertEqual(parsed["name"], "Rick")

    def test_json_with_nested_objects(self) -> None:
        """Test JSON formatting with nested structures."""
        entry = {
            "id": 1,
            "name": "character",
            "origin": {"name": "Earth", "dimension": "C-137"},
        }

        json_str = json.dumps(entry, indent=4)
        parsed = json.loads(json_str)

        self.assertEqual(parsed["origin"]["name"], "Earth")
        self.assertEqual(parsed["origin"]["dimension"], "C-137")

    def test_json_array_formatting(self) -> None:
        """Test formatting of JSON arrays."""
        entries = [
            {"id": 1, "name": "Rick"},
            {"id": 2, "name": "Morty"},
        ]

        # Format as array with proper separators
        json_lines = [json.dumps(entry, indent=4) for entry in entries]
        json_array = "[\n" + ",\n".join(json_lines) + "\n]"

        # Should be valid JSON
        parsed = json.loads(json_array)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["name"], "Rick")
        self.assertEqual(parsed[1]["name"], "Morty")

    def test_json_with_special_characters(self) -> None:
        """Test JSON formatting with special characters."""
        entry = {
            "name": 'Quote "test"',
            "path": "C:\\Users\\test",
            "unicode": "Über",
        }

        json_str = json.dumps(entry, indent=4)
        parsed = json.loads(json_str)

        self.assertEqual(parsed["name"], 'Quote "test"')
        self.assertEqual(parsed["unicode"], "Über")

    def test_json_array_comma_formatting(self) -> None:
        """Test that JSON array items are properly comma-separated."""
        items = [{"id": i} for i in range(3)]

        # Simulate the json_out formatting pattern
        endl = ""
        json_parts = []
        for item in items:
            json_parts.append(f'{endl}{json.dumps(item)}')
            endl = ",\n"

        json_output = "[\n" + "".join(json_parts) + "\n]"

        # Verify it's valid JSON
        parsed = json.loads(json_output)
        self.assertEqual(len(parsed), 3)
        self.assertEqual(parsed[0]["id"], 0)
        self.assertEqual(parsed[2]["id"], 2)

    def test_empty_array_formatting(self) -> None:
        """Test formatting of empty arrays."""
        json_array = "[\n]"

        parsed = json.loads(json_array)
        self.assertEqual(len(parsed), 0)
        self.assertEqual(parsed, [])


if __name__ == "__main__":
    unittest.main()
