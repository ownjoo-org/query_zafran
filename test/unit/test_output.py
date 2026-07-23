import csv
import io
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from output import (
    CsvFormatter,
    JsonFileFormatter,
    JsonlFormatter,
    TableFormatter,
    _flatten,
    _serialize,
)


class TestSerialize(unittest.TestCase):
    def test_scalar_int_unchanged(self):
        self.assertEqual(_serialize(42), 42)

    def test_scalar_string_unchanged(self):
        self.assertEqual(_serialize('hello'), 'hello')

    def test_bool_becomes_lowercase_string(self):
        self.assertEqual(_serialize(True), 'true')
        self.assertEqual(_serialize(False), 'false')

    def test_none_unchanged(self):
        self.assertIsNone(_serialize(None))

    def test_dict_becomes_json_string(self):
        result = _serialize({'x': 1})
        self.assertIsInstance(result, str)
        self.assertEqual(json.loads(result), {'x': 1})

    def test_list_becomes_json_string(self):
        result = _serialize([1, 2, 3])
        self.assertIsInstance(result, str)
        self.assertEqual(json.loads(result), [1, 2, 3])


class TestFlatten(unittest.TestCase):
    def test_flat_record_unchanged(self):
        record = {'a': 1, 'b': 'hello'}
        self.assertEqual(_flatten(record), record)

    def test_nested_dict_serialized(self):
        result = _flatten({'findings': {'severity': 'High'}})
        self.assertIsInstance(result['findings'], str)
        self.assertEqual(json.loads(result['findings']), {'severity': 'High'})

    def test_list_value_serialized(self):
        result = _flatten({'tags': ['web', 'db']})
        self.assertIsInstance(result['tags'], str)
        self.assertEqual(json.loads(result['tags']), ['web', 'db'])

    def test_empty_list_serialized(self):
        result = _flatten({'findings': []})
        self.assertEqual(result['findings'], '[]')


class TestJsonlFormatter(unittest.TestCase):
    def _capture(self, records: list[dict]) -> list[dict]:
        buf = io.StringIO()
        with patch('sys.stdout', buf):
            fmt = JsonlFormatter()
            for r in records:
                fmt.write(r)
        return [json.loads(line) for line in buf.getvalue().strip().splitlines()]

    def test_one_line_per_record(self):
        results = self._capture([{'a': 1}, {'b': 2}])
        self.assertEqual(len(results), 2)

    def test_record_content_preserved(self):
        results = self._capture([{'name': 'asset1', 'severity': 'High'}])
        self.assertEqual(results[0]['severity'], 'High')

    def test_nested_values_preserved(self):
        results = self._capture([{'findings': [{'severity': 'Critical'}]}])
        self.assertIsInstance(results[0]['findings'], list)

    def test_empty_findings_list_preserved(self):
        results = self._capture([{'AssetID': 'a1', 'findings': []}])
        self.assertEqual(results[0]['findings'], [])


class TestCsvFormatter(unittest.TestCase):
    def _capture(self, records: list[dict]) -> tuple[list[str], list[dict]]:
        buf = io.StringIO()
        with patch('sys.stdout', buf):
            fmt = CsvFormatter()
            for r in records:
                fmt.write(r)
        reader = csv.DictReader(io.StringIO(buf.getvalue()))
        return reader.fieldnames or [], list(reader)

    def test_header_matches_first_record_keys(self):
        headers, _ = self._capture([{'name': 'asset1', 'severity': 'High'}])
        self.assertEqual(headers, ['name', 'severity'])

    def test_row_values_correct(self):
        _, rows = self._capture([{'name': 'asset1'}, {'name': 'asset2'}])
        self.assertEqual(rows[1]['name'], 'asset2')

    def test_nested_value_serialized_to_json_string(self):
        _, rows = self._capture([{'findings': [{'severity': 'High'}]}])
        self.assertEqual(json.loads(rows[0]['findings']), [{'severity': 'High'}])

    def test_multiple_rows_written(self):
        _, rows = self._capture([{'a': 1}, {'a': 2}, {'a': 3}])
        self.assertEqual(len(rows), 3)


class TestTableFormatter(unittest.TestCase):
    def test_no_output_before_close(self):
        buf = io.StringIO()
        with patch('sys.stdout', buf):
            fmt = TableFormatter()
            fmt.write({'name': 'asset1'})
        self.assertEqual(buf.getvalue(), '')

    def test_output_flushed_on_close(self):
        fmt = TableFormatter()
        fmt.write({'name': 'asset1', 'severity': 'High'})
        buf = io.StringIO()
        with patch('sys.stdout', buf):
            fmt.close()
        self.assertIn('asset1', buf.getvalue())

    def test_close_with_no_records_does_not_raise(self):
        TableFormatter().close()

    def test_all_rows_present_in_output(self):
        fmt = TableFormatter()
        fmt.write({'name': 'alpha'})
        fmt.write({'name': 'beta'})
        buf = io.StringIO()
        with patch('sys.stdout', buf):
            fmt.close()
        output = buf.getvalue()
        self.assertIn('alpha', output)
        self.assertIn('beta', output)


class TestJsonFileFormatter(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix='.json')
        os.close(fd)

    def tearDown(self):
        os.unlink(self.path)

    def _load(self) -> list:
        with open(self.path) as f:
            return json.load(f)

    def test_produces_valid_json_array(self):
        fmt = JsonFileFormatter(path=self.path)
        fmt.write({'a': 1})
        fmt.write({'b': 2})
        fmt.close()
        self.assertEqual(self._load(), [{'a': 1}, {'b': 2}])

    def test_empty_run_produces_empty_array(self):
        fmt = JsonFileFormatter(path=self.path)
        fmt.close()
        self.assertEqual(self._load(), [])

    def test_single_record_valid(self):
        fmt = JsonFileFormatter(path=self.path)
        fmt.write({'x': 99})
        fmt.close()
        self.assertEqual(self._load(), [{'x': 99}])

    def test_nested_values_preserved(self):
        fmt = JsonFileFormatter(path=self.path)
        fmt.write({'findings': [{'severity': 'Critical'}]})
        fmt.close()
        data = self._load()
        self.assertEqual(data[0]['findings'], [{'severity': 'Critical'}])

    def test_records_written_incrementally(self):
        fmt = JsonFileFormatter(path=self.path)
        fmt.write({'n': 1})
        fmt.write({'n': 2})
        fmt.write({'n': 3})
        fmt.close()
        data = self._load()
        self.assertEqual([r['n'] for r in data], [1, 2, 3])


if __name__ == '__main__':
    unittest.main()
