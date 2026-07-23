import logging
import re
import sqlite3
from typing import Iterator

from oj_persistence import Manager, Sqlite, TableAlreadyRegistered

logger = logging.getLogger(__name__)

ASSETS_TABLE = 'assets'
FINDINGS_TABLE = 'findings'

# Top-level asset fields to index for fast SQL queries.
# Add any field name you want to filter on: WHERE json_extract(value, '$.field') = ...
ASSET_INDEX_FIELDS: list[str] = [
    'is_internet_facing',
]

# Same for findings. Nested paths use dot notation (e.g. 'Asset.AssetId').
FINDING_INDEX_FIELDS: list[str] = [
    'severity',
    'status',
]

_SAFE_FIELD = re.compile(r'^[\w.]+$')


def _json_path(field: str) -> str:
    """Turn a field name or dot-notation path into a json_extract path."""
    return field if field.startswith('$') else f'$.{field}'


def _index_name(table: str, field: str) -> str:
    """Derive a safe index name from table + field (dots become underscores)."""
    safe = field.replace('$', '').replace('.', '_').strip('_')
    return f'idx_{table}_{safe}'


class Store:
    def __init__(
        self,
        path: str,
        asset_fields: list[str] | None = None,
        finding_fields: list[str] | None = None,
    ):
        self._path = path
        self._manager = Manager()
        spec = Sqlite(path=path)

        for table in (ASSETS_TABLE, FINDINGS_TABLE):
            try:
                self._manager.register(table, spec)
            except TableAlreadyRegistered:
                pass
            self._manager.truncate(table)

        # oj-persistence index for the Python-side join lookup
        try:
            self._manager.add_index(FINDINGS_TABLE, '$._asset_id')
        except ValueError:
            pass  # already exists from a prior run

        self._create_field_indexes(
            asset_fields if asset_fields is not None else ASSET_INDEX_FIELDS,
            finding_fields if finding_fields is not None else FINDING_INDEX_FIELDS,
        )
        self._finding_idx = 0

    def _create_field_indexes(
        self,
        asset_fields: list[str],
        finding_fields: list[str],
    ) -> None:
        """Create expression indexes directly in SQLite for ad-hoc SQL queries."""
        conn = sqlite3.connect(self._path)
        try:
            for field in asset_fields:
                if not _SAFE_FIELD.match(field):
                    logger.warning(f'Skipping unsafe asset index field: {field!r}')
                    continue
                name = _index_name(ASSETS_TABLE, field)
                path = _json_path(field)
                conn.execute(
                    f'CREATE INDEX IF NOT EXISTS {name} '
                    f'ON {ASSETS_TABLE} (json_extract(value, "{path}"))'
                )

            for field in finding_fields:
                if not _SAFE_FIELD.match(field):
                    logger.warning(f'Skipping unsafe finding index field: {field!r}')
                    continue
                name = _index_name(FINDINGS_TABLE, field)
                path = _json_path(field)
                conn.execute(
                    f'CREATE INDEX IF NOT EXISTS {name} '
                    f'ON {FINDINGS_TABLE} (json_extract(value, "{path}"))'
                )

            conn.commit()
        finally:
            conn.close()

    def save_asset(self, asset: dict) -> None:
        self._manager.upsert(ASSETS_TABLE, asset['AssetID'], asset)

    def save_finding(self, finding: dict) -> None:
        # Hoist the join key to the top level so the index can find it
        enriched = {
            **finding,
            '_asset_id': finding.get('Asset', {}).get('AssetId', ''),
        }
        self._manager.upsert(FINDINGS_TABLE, str(self._finding_idx), enriched)
        self._finding_idx += 1

    def iter_joined(self) -> Iterator[dict]:
        for asset in self._manager.iter(ASSETS_TABLE):
            asset_id = asset.get('AssetID', '')
            raw_findings = self._manager.list_by_field(FINDINGS_TABLE, '$._asset_id', asset_id)
            findings = [
                {k: v for k, v in f.items() if k != '_asset_id'}
                for f in raw_findings
            ]
            yield {**asset, 'findings': findings}

    def close(self) -> None:
        self._manager.close()


def execute_sql(db_path: str, sql: str) -> Iterator[dict]:
    """Run a raw SQL query against the store and yield each row as a dict.

    Opens the DB read-only so it is safe to call while a Store is not active.
    Column names come from the SELECT list (or json_extract aliases).
    """
    conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
    try:
        cursor = conn.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        for row in cursor:
            yield dict(zip(columns, row))
    finally:
        conn.close()
