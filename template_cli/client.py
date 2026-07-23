import base64
import logging
from asyncio import Queue, get_running_loop
from typing import AsyncGenerator, Optional

from httpx import AsyncClient, HTTPError, HTTPStatusError, Response
from ownjoo_toolkit import get_value
from ownjoo_toolkit.logging.decorators import timed_async_generator
from retry_async import retry

from template_cli.consts import RETRY_COUNT, RETRY_BACKOFF_FACTOR
from template_cli.tracker import contributing_tasks

logger = logging.getLogger(__name__)


@retry(exceptions=Exception, tries=RETRY_COUNT, delay=1, backoff=RETRY_BACKOFF_FACTOR, max_delay=5, logger=logger, is_async=True)
async def get_response(
    url: str,
    method: str = 'GET',
    params=None,
    json: Optional[dict] = None,
    data: Optional[dict] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    proxies: Optional[dict] = None,
) -> Optional[dict]:
    async with AsyncClient(follow_redirects=True, http2=True) as session:
        try:
            if isinstance(proxies, dict):
                session.proxies = proxies

            session.headers.update(
                {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                }
            )

            # Add basic auth header if credentials provided
            if username and password:
                credentials = base64.b64encode(f'{username}:{password}'.encode()).decode()
                session.headers.update({'Authorization': f'Basic {credentials}'})

            session.verify = False  # for convenience...  evaluate for yourself if this is acceptable.

            r: Response = await session.request(
                method=method or 'GET',
                url=url,
                data=data,
                json=json,
                params=params,
                timeout=30,
            )
            r.raise_for_status()
            return r.json()
        except HTTPStatusError as exc_status:
            if exc_status.response.status_code == 404:
                return None
            else:
                logger.exception(
                    f'HTTP Error: {exc_status=}:\n'
                    f'{exc_status.response.status_code=}\n'
                    f'{exc_status.request.url=}\n'
                )
                raise
        except HTTPError as exc_http:
            logger.exception(
                f'HTTP Error: {exc_http=}:\n'
                f'{exc_http.request.url=}\n'
            )
            raise
        except Exception as exc:
            logger.exception(f'UNEXPECTED ERROR: {exc=}')
            raise


@timed_async_generator(log_progress=False, log_level=logging.DEBUG, logger=logger)
async def list_results_paginated(
    url: str,
    additional_params: Optional[dict] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    proxies: Optional[dict] = None,
    result_limit: int = 0,
    page_size: int = 100,
) -> AsyncGenerator[dict, None]:
    """Paginate through results with optional result limiting and page-size optimization.

    Args:
        url: API endpoint URL
        additional_params: Extra query parameters to pass to API
        username: Optional username for basic auth
        password: Optional password for basic auth
        proxies: Optional proxy configuration dict
        result_limit: Maximum results to yield (0 = no limit)
        page_size: Number of results per page from API

    Yields:
        Individual result dictionaries from paginated API responses
    """
    # Optimize page_size if result_limit is set and smaller
    effective_page_size = page_size
    if result_limit > 0 and page_size > result_limit:
        effective_page_size = result_limit

    should_continue: bool = True
    params: dict = {
        'page': 1,
        'pageSize': effective_page_size,
    }
    if isinstance(additional_params, dict):
        params.update(additional_params)

    results_yielded: int = 0

    while should_continue:
        data_raw: dict = await get_response(
            method='GET',
            url=url,
            params=params,
            username=username,
            password=password,
            proxies=proxies,
        )
        results: list[dict] = get_value(src=data_raw, path=['results'], exp=list, default=[])

        if not results or not get_value(src=data_raw, path=['info', 'next'], exp=str):
            should_continue = False

        params['page'] += 1

        for result in results:
            # Check if we've reached the result limit
            if result_limit > 0 and results_yielded >= result_limit:
                should_continue = False
                break

            yield result
            results_yielded += 1


async def list_results(
    url: str,
    additional_params: Optional[dict] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    proxies: Optional[dict] = None,
    q: Optional[Queue] = None,
) -> None:
    params: dict = {}
    if isinstance(additional_params, dict):
        params.update(additional_params)
    data_raw: dict = await get_response(
        method='GET',
        url=url,
        params=params,
        username=username,
        password=password,
        proxies=proxies,
    )
    for result in get_value(src=data_raw, path=['results'], exp=list, default=[]):
        await q.put(result)


async def list_characters(
    url: str,
    username: Optional[str] = None,
    password: Optional[str] = None,
    proxies: Optional[dict] = None,
    q: Optional[Queue] = None,
) -> None:
    loop = get_running_loop()
    r: dict = await get_response(url=url, username=username, password=password, proxies=proxies)
    chars_url: str = get_value(src=r, path=['characters'], exp=str, default='')
    if chars_url:
        chars: dict = await get_response(
            url=chars_url,
            username=username,
            password=password,
            proxies=proxies,
        )
        pages: int = get_value(src=chars, path=['info', 'pages'], exp=int, default=0)
        if pages:
            for page in range(1, pages + 1):
                task = loop.create_task(
                    list_results(
                        url=chars_url,
                        additional_params={'page': page},
                        username=username,
                        password=password,
                        proxies=proxies,
                        q=q,
                    )
                )
                contributing_tasks.append(task.get_name())
                task.add_done_callback(
                    lambda contributing_task: contributing_tasks.pop(
                        contributing_tasks.index(contributing_task.get_name())
                    )
                )
                task.add_done_callback(lambda contributing_task: contributing_task.cancel())


async def list_locations(
    url: str,
    username: Optional[str] = None,
    password: Optional[str] = None,
    proxies: Optional[dict] = None,
    q: Optional[Queue] = None,
) -> None:
    loop = get_running_loop()
    r: dict = await get_response(url=url, username=username, password=password, proxies=proxies)
    locations_url: str = get_value(src=r, path=['locations'], exp=str, default='')
    if locations_url:
        locations: dict = await get_response(
            url=locations_url,
            username=username,
            password=password,
            proxies=proxies,
        )
        pages: int = get_value(src=locations, path=['info', 'pages'], exp=int, default=0)
        if pages:
            for page in range(1, pages + 1):
                task = loop.create_task(
                    list_results(
                        url=locations_url,
                        additional_params={'page': page},
                        username=username,
                        password=password,
                        proxies=proxies,
                        q=q,
                    )
                )
                contributing_tasks.append(task.get_name())
                task.add_done_callback(
                    lambda contributing_task: contributing_tasks.pop(
                        contributing_tasks.index(contributing_task.get_name())
                    )
                )
                task.add_done_callback(lambda contributing_task: contributing_task.cancel())


async def list_episodes(
    url: str,
    username: Optional[str] = None,
    password: Optional[str] = None,
    proxies: Optional[dict] = None,
    q: Optional[Queue] = None,
) -> None:
    loop = get_running_loop()
    r: dict = await get_response(url=url, username=username, password=password, proxies=proxies)
    episodes_url: str = get_value(src=r, path=['episodes'], exp=str, default='')
    if episodes_url:
        episodes: dict = await get_response(
            url=episodes_url,
            username=username,
            password=password,
            proxies=proxies,
        )
        pages: int = get_value(src=episodes, path=['info', 'pages'], exp=int, default=0)
        if pages:
            for page in range(1, pages + 1):
                task = loop.create_task(
                    list_results(
                        url=episodes_url,
                        additional_params={'page': page},
                        username=username,
                        password=password,
                        proxies=proxies,
                        q=q,
                    )
                )
                contributing_tasks.append(task.get_name())
                task.add_done_callback(
                    lambda contributing_task: contributing_tasks.pop(
                        contributing_tasks.index(contributing_task.get_name())
                    )
                )
                task.add_done_callback(lambda contributing_task: contributing_task.cancel())
