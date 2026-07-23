import argparse
import json
import logging
from asyncio import run
from sys import stderr
from typing import Optional

from ownjoo_toolkit.logging.consts import LOG_FORMAT
from ownjoo_toolkit.parsing.consts import TimeFormats

from template_cli.main import main


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--username',
        type=str,
        required=True,
        help='Username for authentication',
    )
    parser.add_argument(
        '--password',
        type=str,
        required=True,
        help='Password for authentication',
    )
    parser.add_argument(
        '--domain',
        default='example.com',
        type=str,
        required=False,
        help='The FQDN for your API (not full URL)',
    )
    parser.add_argument(
        '--proxies',
        type=str,
        required=False,
        help="JSON structure specifying 'http' and 'https' proxy URLs",
    )
    parser.add_argument(
        '--log-level',
        type=int,
        required=False,
        help="0 (NOTSET) - 50 (CRITICAL)",
        default=logging.INFO,
        dest='log_level',
    )

    args = parser.parse_args()

    logging.basicConfig(
        format=LOG_FORMAT,
        level=args.log_level,
        datefmt=TimeFormats.date_and_time.value,
        stream=stderr,
    )
    logger = logging.getLogger(__name__)

    proxies: Optional[dict] = None
    if args.proxies:
        try:
            proxies: dict = json.loads(args.proxies)
        except Exception as exc_json:
            logger.warning(f'failure parsing proxies: {exc_json}: proxies provided: {args.proxies}')

    run(main(domain=args.domain, username=args.username, password=args.password, proxies=proxies))
