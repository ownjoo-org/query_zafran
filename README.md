# query_zafran

A CLI tool for querying Zafran assets and findings via the Zafran API v2, joining them locally, and querying the results with SQL.

## Features

- **Asset & Finding Queries** — Fetch assets and findings using ZQL (Zafran Query Language)
- **Local Join** — Match findings to their assets by ID, stored in a persistent SQLite database
- **SQL Query Mode** — Run raw SQL against the local store without hitting the API
- **Pluggable Output** — JSONL (pipe-friendly), CSV, formatted table, or a valid JSON file
- **Offset & Cursor Pagination** — Assets use offset/count; findings use cursor tokens; both handled automatically
- **Automatic Retries** — Exponential backoff via `retry-async`
- **Result Limiting** — Stop early with `--limit` to sample large datasets

## Setup

### Prerequisites

- Python 3.10+
- pip

### Installation

```bash
pip install -r requirements.txt
```

## Usage

### Modes

| Mode | What it does |
|---|---|
| `assets` | Fetch assets from the API and output them |
| `findings` | Fetch findings from the API and output them |
| `join` | Fetch both, match findings to assets, output one record per asset with a `findings` list |
| `query` | Run a SQL string against the local SQLite store — no API calls |

### Common Arguments

```
--api-key       Bearer token (required for assets, findings, join)
--domain        API base URL, e.g. https://api.example.com (required for assets, findings, join)
--mode          assets | findings | join | query  (default: assets)
--assets-zql    ZQL filter for assets
--findings-zql  ZQL filter for findings
--page-size     Results per API page (default: 100)
--limit         Max records to fetch per endpoint, 0 = no limit (default: 0)
--output        jsonl | csv | table | json  (default: jsonl)
--output-file   File path, required when --output json
--table-style   rounded | double | single | ascii | none  (default: rounded, only applies to --output table)
--store-path    Path to the SQLite store (default: system temp dir)
--log-level     0 (NOTSET) – 50 (CRITICAL)  (default: 20 / INFO)
```

### Examples

```bash
# Fetch all assets, stream as JSONL
python qz.py --api-key TOKEN --domain https://api.example.com --mode assets
```

```json
{"AssetID": "abc-123", "name": "web-server-01", "is_internet_facing": true, "type": "Server", "criticality": "High"}
{"AssetID": "def-456", "name": "api-gateway-prod", "is_internet_facing": true, "type": "Gateway", "criticality": "Critical"}
{"AssetID": "ghi-789", "name": "db-primary-01", "is_internet_facing": false, "type": "Database", "criticality": "Critical"}
```

---

```bash
# Fetch a sample of 50 assets matching a ZQL filter, output as CSV
python qz.py --api-key TOKEN --domain https://api.example.com \
  --mode assets \
  --assets-zql "is_internet_facing = true" \
  --limit 50 \
  --output csv
```

```
AssetID,name,is_internet_facing,type,criticality
abc-123,web-server-01,true,Server,High
def-456,api-gateway-prod,true,Gateway,Critical
```

---

```bash
# Fetch findings and write to a valid JSON file
python qz.py --api-key TOKEN --domain https://api.example.com \
  --mode findings \
  --output json --output-file findings.json
```

```json
[
  {"Asset": {"AssetId": "abc-123"}, "severity": "Critical", "status": "Open", "title": "CVE-2024-1234"},
  {"Asset": {"AssetId": "abc-123"}, "severity": "High", "status": "Open", "title": "CVE-2024-5678"},
  {"Asset": {"AssetId": "ghi-789"}, "severity": "Low", "status": "Resolved", "title": "CVE-2023-9999"}
]
```

---

```bash
# Join assets and findings — one record per asset with a nested findings list
python qz.py --api-key TOKEN --domain https://api.example.com \
  --mode join \
  --assets-zql "is_internet_facing = true" \
  --store-path ./zafran.db
```

```json
{"AssetID": "abc-123", "name": "web-server-01", "is_internet_facing": true, "findings": [{"Asset": {"AssetId": "abc-123"}, "severity": "Critical", "title": "CVE-2024-1234"}, {"Asset": {"AssetId": "abc-123"}, "severity": "High", "title": "CVE-2024-5678"}]}
{"AssetID": "def-456", "name": "api-gateway-prod", "is_internet_facing": true, "findings": []}
```

---

```bash
# Pipe join output to jq — extract asset ID and the asset IDs referenced by each finding
python qz.py --api-key TOKEN --domain https://api.example.com \
  --mode join \
  --store-path ./zafran.db \
  | jq '{asset_id: .AssetID, finding_asset_ids: [.findings[].Asset.AssetId]}'
```

```json
{"asset_id": "abc-123", "finding_asset_ids": ["abc-123", "abc-123"]}
{"asset_id": "def-456", "finding_asset_ids": []}
{"asset_id": "ghi-789", "finding_asset_ids": ["ghi-789"]}
```

```bash
# Filter to assets that have findings, then summarise severity counts
python qz.py --api-key TOKEN --domain https://api.example.com \
  --mode join \
  --store-path ./zafran.db \
  | jq 'select(.findings | length > 0)
        | {asset_id: .AssetID,
           name: .name,
           finding_count: (.findings | length),
           severities: [.findings[].severity]}'
```

```json
{"asset_id": "abc-123", "name": "web-server-01", "finding_count": 2, "severities": ["Critical", "High"]}
{"asset_id": "ghi-789", "name": "db-primary-01", "finding_count": 1, "severities": ["Low"]}
```

---

```bash
# Query the local store with SQL and format as a table — no API key needed
python qz.py --mode query --store-path ./zafran.db \
  --sql "SELECT json_extract(a.value, '$.AssetID') AS asset_id,
                json_extract(a.value, '$.name')    AS name,
                json_extract(f.value, '$.severity') AS severity,
                json_extract(f.value, '$.title')    AS title
         FROM assets a
         JOIN findings f ON json_extract(f.value, '$._asset_id') = a.key
         WHERE json_extract(f.value, '$.severity') = 'Critical'" \
  --output table
```

```
 asset_id    name            severity   title
 ─────────────────────────────────────────────────────────
 abc-123     web-server-01   Critical   CVE-2024-1234
```

---

```bash
# Same join across all severities with rounded borders (--table-style rounded is the default)
python qz.py --mode query --store-path ./zafran.db \
  --sql "SELECT json_extract(a.value, '$.AssetID') AS asset_id,
                json_extract(a.value, '$.name')    AS name,
                json_extract(f.value, '$.title')   AS title,
                json_extract(f.value, '$.severity') AS severity
         FROM assets a
         JOIN findings f ON json_extract(f.value, '$._asset_id') = a.key
         ORDER BY severity" \
  --output table \
  --table-style rounded
```

```
╭──────────┬───────────────┬───────────────┬──────────╮
│ asset_id │ name          │ title         │ severity │
├──────────┼───────────────┼───────────────┼──────────┤
│ abc-123  │ web-server-01 │ CVE-2024-1234 │ Critical │
│ abc-123  │ web-server-01 │ CVE-2024-5678 │ High     │
│ ghi-789  │ db-primary-01 │ CVE-2023-9999 │ Low      │
╰──────────┴───────────────┴───────────────┴──────────╯
```

```
 asset_id    name            severity   title
 ─────────────────────────────────────────────────────────
 abc-123     web-server-01   Critical   CVE-2024-1234
```

```bash
# Same query as JSONL, piped to jq
python qz.py --mode query --store-path ./zafran.db \
  --sql "SELECT json_extract(a.value, '$.AssetID') AS asset_id,
                json_extract(a.value, '$.name')    AS name,
                json_extract(f.value, '$.severity') AS severity
         FROM assets a
         JOIN findings f ON json_extract(f.value, '$._asset_id') = a.key" \
  | jq 'select(.severity == "Critical")'
```

```json
{"asset_id": "abc-123", "name": "web-server-01", "severity": "Critical"}
```

### Table Styles (`--table-style`)

All styles use the same `--output table` flag. Pass `--table-style <name>` to choose.

**`rounded`** (default)
```
╭──────────┬───────────────┬──────────╮
│ asset_id │ name          │ severity │
├──────────┼───────────────┼──────────┤
│ abc-123  │ web-server-01 │ Critical │
│ def-456  │ api-gateway   │ High     │
╰──────────┴───────────────┴──────────╯
```

**`double`**
```
╔══════════╦═══════════════╦══════════╗
║ asset_id ║ name          ║ severity ║
╠══════════╬═══════════════╬══════════╣
║ abc-123  ║ web-server-01 ║ Critical ║
║ def-456  ║ api-gateway   ║ High     ║
╚══════════╩═══════════════╩══════════╝
```

**`single`**
```
┌──────────┬───────────────┬──────────┐
│ asset_id │ name          │ severity │
├──────────┼───────────────┼──────────┤
│ abc-123  │ web-server-01 │ Critical │
│ def-456  │ api-gateway   │ High     │
└──────────┴───────────────┴──────────┘
```

**`ascii`** (safest for terminals without Unicode support)
```
+----------+---------------+----------+
| asset_id | name          | severity |
+----------+---------------+----------+
| abc-123  | web-server-01 | Critical |
| def-456  | api-gateway   | High     |
+----------+---------------+----------+
```

**`none`** (whitespace only, no borders)
```
  asset_id   name            severity

  abc-123    web-server-01   Critical
  def-456    api-gateway     High
```

## Architecture

### Module Structure

```
query_zafran/
├── qz.py          # CLI entry point — argument parsing and mode orchestration
├── client.py      # ZafranClient — sync httpx session, list_assets(), list_findings()
├── store.py       # Store — SQLite-backed persistence via oj-persistence; execute_sql()
├── output.py      # Formatter ABC — JsonlFormatter, CsvFormatter, TableFormatter, JsonFileFormatter
├── consts.py      # Shared constants (PAGE_SIZE, retry config)
└── test/
    └── unit/
        ├── test_store.py   # Store join, truncation, indexes, execute_sql
        └── test_output.py  # All formatters and helper functions
```

### Local Store (SQLite)

The `join` mode writes assets and findings to a SQLite database so the join happens locally rather than in memory. The file persists after each run and can be queried directly with any SQLite client or with `--mode query`.

Schema:

```sql
CREATE TABLE assets  (key TEXT PRIMARY KEY, value TEXT NOT NULL)
CREATE TABLE findings (key TEXT PRIMARY KEY, value TEXT NOT NULL)
```

`value` is the full record as a JSON string. Indexed fields are queryable via `json_extract`:

```sql
-- fields indexed by default
json_extract(value, '$.is_internet_facing')   -- assets
json_extract(value, '$.severity')             -- findings
json_extract(value, '$.status')               -- findings
json_extract(value, '$._asset_id')            -- findings (join key)
```

To add more indexes, edit `ASSET_INDEX_FIELDS` and `FINDING_INDEX_FIELDS` in `store.py`, or pass them when constructing `Store` directly.

### Output Formats

| Format | Behavior | Best for |
|---|---|---|
| `jsonl` | One JSON object per line, streams to stdout | Piping to `jq`, downstream processing |
| `csv` | Streams rows; nested values are JSON strings | Spreadsheets, pandas |
| `table` | Buffers all rows, prints on exit | Small result sets, human review |
| `json` | Streams a valid JSON array to `--output-file` | Downstream tools that require a JSON file |

### Pagination

- **Assets** — offset/count: `GET /api/v2/assets?offset=N&count=100`
- **Findings** — cursor: `POST /api/v2/findings/query` with `token` in the request body, next token read from `pagination.nextToken`

Both stop automatically when the API returns an empty page or no next token.

## Running Tests

```bash
# Run all unit tests
python -m pytest test/unit/ -v

# Run a specific test class
python -m pytest test/unit/test_store.py::TestExecuteSql -v
```
