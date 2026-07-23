import argparse
import logging
import os
import tempfile
from sys import stderr

from oj_toolkit.logging.consts import LOG_FORMAT
from oj_toolkit.parsing.consts import TimeFormats

from client import ZafranClient
from consts import PAGE_SIZE
from output import FORMATTERS, JsonFileFormatter, TABLE_STYLES, TableFormatter
from store import Store, execute_sql


DEFAULT_STORE_PATH = os.path.join(tempfile.gettempdir(), 'qz_store.db')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Query Zafran assets and findings.')
    parser.add_argument(
        '--api-key',
        type=str,
        required=False,
        default=None,
        dest='api_key',
        help='Bearer token for authentication (required for all modes except query)',
    )
    parser.add_argument(
        '--domain',
        type=str,
        required=False,
        default=None,
        help='Base URL for the API (e.g. https://api.example.com) (required for all modes except query)',
    )
    parser.add_argument(
        '--proxy',
        type=str,
        required=False,
        default=None,
        help='HTTP proxy URL to route API requests through (e.g. http://proxy.example.com:8080)',
    )
    parser.add_argument(
        '--mode',
        type=str,
        required=False,
        default='assets',
        choices=['assets', 'findings', 'join', 'query'],
        help='assets: fetch assets  findings: fetch findings  join: match findings to assets  query: run SQL against local store',
    )
    parser.add_argument(
        '--sql',
        type=str,
        required=False,
        default=None,
        help='SQL string to run against the local store (required for --mode query)',
    )
    parser.add_argument(
        '--assets-zql',
        type=str,
        required=False,
        default='',
        dest='asset_query',
        help='ZQL query for assets (used in assets and join modes)',
    )
    parser.add_argument(
        '--findings-zql',
        type=str,
        required=False,
        default='',
        dest='finding_query',
        help='ZQL query for findings (used in findings and join modes)',
    )
    parser.add_argument(
        '--page-size',
        type=int,
        required=False,
        default=PAGE_SIZE,
        dest='page_size',
        help='Results per page',
    )
    parser.add_argument(
        '--limit',
        type=int,
        required=False,
        default=0,
        dest='result_limit',
        help='Max records to fetch per endpoint (0 = no limit)',
    )
    parser.add_argument(
        '--output',
        type=str,
        required=False,
        default='jsonl',
        choices=[*FORMATTERS.keys(), 'json'],
        help='Output format: jsonl (default, pipe-friendly), csv, table, json (requires --output-file)',
    )
    parser.add_argument(
        '--table-style',
        type=str,
        required=False,
        default='rounded',
        dest='table_style',
        choices=TABLE_STYLES,
        help='Border style for --output table (default: rounded)',
    )
    parser.add_argument(
        '--output-file',
        type=str,
        required=False,
        default=None,
        dest='output_file',
        help='File path for --output json',
    )
    parser.add_argument(
        '--store-path',
        type=str,
        required=False,
        default=DEFAULT_STORE_PATH,
        dest='store_path',
        help=f'Path to the SQLite store (default: {DEFAULT_STORE_PATH})',
    )
    parser.add_argument(
        '--log-level',
        type=int,
        required=False,
        default=logging.INFO,
        dest='log_level',
        help='Logging verbosity: 0 (NOTSET) - 50 (CRITICAL)',
    )

    args = parser.parse_args()

    if args.mode == 'query':
        if not args.sql:
            parser.error('--mode query requires --sql')
    else:
        if not args.api_key:
            parser.error(f'--mode {args.mode} requires --api-key')
        if not args.domain:
            parser.error(f'--mode {args.mode} requires --domain')

    logging.basicConfig(
        format=LOG_FORMAT,
        level=args.log_level,
        datefmt=TimeFormats.DATE_AND_TIME.value,
        stream=stderr,
    )
    logger = logging.getLogger(__name__)

    if args.output == 'json':
        if not args.output_file:
            parser.error('--output json requires --output-file')
        formatter = JsonFileFormatter(path=args.output_file)
    elif args.output == 'table':
        formatter = TableFormatter(style=args.table_style)
    else:
        formatter = FORMATTERS[args.output]()

    try:
        if args.mode == 'assets':
            client = ZafranClient(api_key=args.api_key, domain=args.domain, proxy=args.proxy)
            for record in client.list_assets(
                query=args.asset_query,
                page_size=args.page_size,
                result_limit=args.result_limit,
            ):
                formatter.write(record)

        elif args.mode == 'findings':
            client = ZafranClient(api_key=args.api_key, domain=args.domain, proxy=args.proxy)
            for record in client.list_findings(
                query=args.finding_query,
                page_size=args.page_size,
                result_limit=args.result_limit,
            ):
                formatter.write(record)

        elif args.mode == 'join':
            client = ZafranClient(api_key=args.api_key, domain=args.domain, proxy=args.proxy)
            store = Store(path=args.store_path)
            logger.info(f'Loading assets into store ({args.store_path})...')
            for asset in client.list_assets(
                query=args.asset_query,
                page_size=args.page_size,
                result_limit=args.result_limit,
            ):
                store.save_asset(asset)

            logger.info('Loading findings into store...')
            for finding in client.list_findings(
                query=args.finding_query,
                page_size=args.page_size,
                result_limit=args.result_limit,
            ):
                store.save_finding(finding)

            logger.info('Writing joined output...')
            for record in store.iter_joined():
                formatter.write(record)

            store.close()

        elif args.mode == 'query':
            for record in execute_sql(db_path=args.store_path, sql=args.sql):
                formatter.write(record)

    finally:
        formatter.close()
