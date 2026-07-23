import logging
from typing import Generator, Optional

from httpx import Client, HTTPError, HTTPStatusError, Response
from oj_toolkit import dig
from retry_async import retry

from consts import PAGE_SIZE, RETRY_COUNT, RETRY_BACKOFF_FACTOR

logger = logging.getLogger(__name__)


class ZafranClient:
    def __init__(self, api_key: str, domain: str, proxy: Optional[str] = None):
        self.domain = domain
        self._session = Client(follow_redirects=True, http2=True, proxy=proxy)
        self._session.headers.update(
            {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}',
            }
        )

    @retry(
        exceptions=Exception,
        tries=RETRY_COUNT,
        delay=1,
        backoff=RETRY_BACKOFF_FACTOR,
        max_delay=5,
        logger=logger,
        is_async=False,
    )
    def _request(
        self,
        method: str,
        url: str,
        params: Optional[dict] = None,
        json: Optional[dict] = None,
    ) -> Optional[dict]:
        try:
            r: Response = self._session.request(
                method=method,
                url=url,
                params=params,
                json=json,
                timeout=30,
            )
            r.raise_for_status()
            return r.json()
        except HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            logger.exception(f'HTTP {exc.response.status_code} error: {exc.request.url}')
            raise
        except HTTPError as exc:
            logger.exception(f'HTTP error: {exc.request.url}')
            raise

    def list_assets(
        self,
        query: str = '',
        page_size: int = PAGE_SIZE,
        result_limit: int = 0,
    ) -> Generator[dict, None, None]:
        offset = 0
        results_yielded = 0

        while True:
            data = self._request(
                method='GET',
                url=f'{self.domain}/api/v2/assets',
                params={'query': query, 'offset': offset, 'count': page_size},
            )
            if not data:
                break
            results: list = dig(src=data, path=['assets'], exp=list, default=[]) or []
            if not results:
                break

            for asset in results:
                if 0 < result_limit <= results_yielded:
                    return
                yield asset
                results_yielded += 1

            if len(results) < page_size:
                break
            offset += len(results)

    def list_findings(
        self,
        query: str = '',
        page_size: int = PAGE_SIZE,
        result_limit: int = 0,
    ) -> Generator[dict, None, None]:
        next_token: Optional[str] = None
        results_yielded = 0

        while True:
            body: dict = {'query': query, 'page_size': page_size}
            if next_token:
                body['token'] = next_token

            data = self._request(
                method='POST',
                url=f'{self.domain}/api/v2/findings/query',
                json=body,
            )
            if not data:
                break
            results: list = dig(src=data, path=['findings'], exp=list, default=[]) or []
            if not results:
                break

            for finding in results:
                if 0 < result_limit <= results_yielded:
                    return
                yield finding
                results_yielded += 1

            next_token = dig(src=data, path=['pagination', 'nextToken'], exp=str) or None
            if not next_token:
                break
