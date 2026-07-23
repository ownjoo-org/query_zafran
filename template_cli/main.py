import logging
from asyncio import Queue, gather
from typing import Coroutine, List, Optional

from template_cli.client import list_characters, list_locations, list_episodes
from template_cli.parser import json_out

logger = logging.getLogger(__name__)


async def main(
    domain: str,
    username: str,
    password: str,
    proxies: Optional[dict] = None,
) -> None:
    q = Queue(maxsize=100)
    client_coroutines: List[Coroutine] = [
        list_characters(url=domain, username=username, password=password, proxies=proxies, q=q),
        list_locations(url=domain, username=username, password=password, proxies=proxies, q=q),
        list_episodes(url=domain, username=username, password=password, proxies=proxies, q=q),
    ]
    parser_coroutines: List[Coroutine] = [
        json_out(q=q),
    ]
    await gather(
        *client_coroutines,
        *parser_coroutines,
        q.join(),
    )
