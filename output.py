import csv
import json
import sys
from abc import ABC, abstractmethod

from oj_toolkit.console import Table


def _serialize(v) -> str | int | float | None:
    """Serialize values to JSON-compatible scalars for flat formats."""
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, (dict, list)):
        return json.dumps(v)
    return v


def _flatten(record: dict) -> dict:
    return {k: _serialize(v) for k, v in record.items()}


class Formatter(ABC):
    @abstractmethod
    def write(self, record: dict) -> None: ...

    def close(self) -> None:
        pass


class JsonlFormatter(Formatter):
    """One JSON object per line — streams to stdout, pipe-friendly (e.g. | jq ...)."""

    def write(self, record: dict) -> None:
        sys.stdout.write(json.dumps(record) + '\n')


class JsonFileFormatter(Formatter):
    """Writes a valid JSON array to a file. Streams records one at a time to keep memory flat."""

    def __init__(self, path: str):
        self._file = open(path, 'w')
        self._first = True
        self._file.write('[\n')

    def write(self, record: dict) -> None:
        if not self._first:
            self._file.write(',\n')
        self._file.write('  ' + json.dumps(record))
        self._first = False

    def close(self) -> None:
        self._file.write('\n]\n')
        self._file.close()


class CsvFormatter(Formatter):
    """Streams CSV rows — nested values are JSON-serialized strings."""

    def __init__(self):
        self._writer = None

    def write(self, record: dict) -> None:
        flat = _flatten(record)
        if self._writer is None:
            self._writer = csv.DictWriter(
                sys.stdout,
                fieldnames=list(flat.keys()),
            )
            self._writer.writeheader()
        self._writer.writerow(flat)


TABLE_STYLES = ('auto', 'ascii', 'rounded', 'double', 'single', 'none')


class TableFormatter(Formatter):
    """Buffers all records and prints a formatted table on close(). Not for large result sets."""

    def __init__(self, style: str = 'rounded'):
        self._style = style
        self._table = None

    def write(self, record: dict) -> None:
        flat = _flatten(record)
        if self._table is None:
            self._table = Table(
                headers=list(flat.keys()),
                columns=len(flat),
                style=self._style,
            )
        self._table.add_row(*flat.values())

    def close(self) -> None:
        if self._table:
            self._table.out()


FORMATTERS: dict[str, type[Formatter]] = {
    'jsonl': JsonlFormatter,
    'csv': CsvFormatter,
    'table': TableFormatter,
}
