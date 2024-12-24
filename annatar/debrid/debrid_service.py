import asyncio
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional, Any, Dict, Union
import traceback

from annatar.debrid.models import StreamLink
import aiohttp
from aiohttp import ClientResponse, ClientTimeout, ContentTypeError, FormData, ClientResponse
from aiohttp_socks import ProxyConnector

from annatar.debrid.exceptions import ProviderException

class DebridService(ABC):
    api_key: str

    def __str__(self) -> str:
        return self.name()

    def __init__(self, api_key: str, source_ip: str):
        self.api_key = api_key
        self.source_ip = source_ip
        self.is_private_token = False
        self.headers: Dict[str, str] = {}
        self._session: Optional[aiohttp.ClientSession] = None
        self._timeout = ClientTimeout(total=15)  # Stremio timeout is 20s

    @property
    def session(self) -> aiohttp.ClientSession:
        if self._session is None:
            connector = aiohttp.TCPConnector(ttl_dns_cache=300)
            self._session = aiohttp.ClientSession(
                timeout=self._timeout, connector=connector
            )
        return self._session

    async def _make_request(
        self,
        method: str,
        url: str,
        data: Optional[dict | str | FormData] = None,
        json: Optional[dict] = None,
        params: Optional[dict] = None,
        is_return_none: bool = False,
        is_expected_to_fail: bool = False,
        is_http_response: bool = False,
        retry_count: int = 0,
    ) -> Any:
        try:
            async with self.session.request(
                method, url, data=data, json=json, params=params, headers=self.headers
            ) as response:
                await self._check_response_status(response, is_expected_to_fail)
                return await self._parse_response(
                    response, is_return_none, is_expected_to_fail, is_http_response
                )

        except ProviderException as error:
            raise error
        except aiohttp.ClientConnectorError as error:
            if retry_count < 1:  # Try one more time
                return await self._make_request(
                    method,
                    url,
                    data=data,
                    json=json,
                    params=params,
                    is_return_none=is_return_none,
                    is_expected_to_fail=is_expected_to_fail,
                    is_http_response=is_http_response,
                    retry_count=retry_count + 1,
                )
            await self._handle_request_error(error)
        except aiohttp.ClientError as error:
            await self._handle_request_error(error)
        except Exception as error:
            await self._handle_request_error(error)

    async def _check_response_status(
        self, response: ClientResponse, is_expected_to_fail: bool
    ):
        """Check response status and handle HTTP errors."""
        try:
            response.raise_for_status()
        except aiohttp.ClientResponseError as error:
            if is_expected_to_fail:
                return

            if response.headers.get("Content-Type") == "application/json":
                error_content = await response.json()
                await self._handle_service_specific_errors(error_content, error.status)
            else:
                error_content = await response.text()

            if error.status == 401:
                raise ProviderException("Invalid token", "invalid_token.mp4")

            if error.status in [502, 503, 504]:
                raise ProviderException(
                    "Debrid service is down.", "debrid_service_down_error.mp4"
                )

            formatted_traceback = "".join(traceback.format_exception(error))
            raise ProviderException(
                f"API Error {error_content} \n{formatted_traceback}",
                "api_error.mp4",
            )

    @staticmethod
    async def _handle_request_error(error: Exception):
        if isinstance(error, asyncio.TimeoutError):
            raise ProviderException("Request timed out.", "torrent_not_downloaded.mp4")
        elif isinstance(error, aiohttp.ClientConnectorError):
            raise ProviderException(
                "Failed to connect to Debrid service.", "debrid_service_down_error.mp4"
            )
        raise ProviderException(f"Request error: {str(error)}", "api_error.mp4")

    @staticmethod
    async def _parse_response(
        response: ClientResponse,
        is_return_none: bool,
        is_expected_to_fail: bool,
        is_http_response: bool = False,
    ) -> Union[dict, list, str]:
        if is_return_none:
            return {}
        try:
            json_data = await response.json()
            if is_http_response:
                return json_data
            return json_data
        except (ValueError, ContentTypeError) as error:
            text_data = await response.text()
            if is_http_response:
                return text_data
            if is_expected_to_fail:
                return text_data
            raise ProviderException(
                f"Failed to parse response error: {error}. \nresponse: {text_data}",
                "api_error.mp4",
            )

    async def wait_for_status(
        self,
        torrent_id: str,
        target_status: Union[str, int],
        max_retries: int,
        retry_interval: int,
        torrent_info: Optional[dict] = None,
    ) -> dict:
        """Wait for the torrent to reach a particular status."""
        # if torrent_info is available, check the status from it
        if torrent_info:
            if torrent_info["status"] == target_status:
                return torrent_info

        for _ in range(max_retries):
            torrent_info = await self.get_torrent_info(torrent_id)
            if torrent_info["status"] == target_status:
                return torrent_info
            await asyncio.sleep(retry_interval)
        raise ProviderException(
            f"Torrent did not reach {target_status} status.",
            "torrent_not_downloaded.mp4",
        )

    @abstractmethod
    async def get_torrent_info(self, torrent_id: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    async def _handle_service_specific_errors(self, error_data: dict, status_code: int):
        """
        Service specific errors on api requests.
        """
        raise NotImplementedError

    @abstractmethod
    def shared_cache(self) -> bool:
        ...

    @abstractmethod
    def short_name(self) -> str:
        ...

    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def id(self) -> str:
        ...

    @abstractmethod
    async def get_stream_links(
        self,
        torrents: list[str],
        stop: asyncio.Event,
        max_results: int,
        season: int = 0,
        episode: int = 0,
    ) -> AsyncGenerator[StreamLink, None]:
        ...
