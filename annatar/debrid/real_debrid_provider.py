"""Real Debrid Provider implementation."""
from typing import Any, Optional, AsyncGenerator
from base64 import b64encode, b64decode
from binascii import Error as BinasciiError
import structlog
import asyncio

from aiohttp import FormData

from annatar import magnet
from annatar.debrid.debrid_service import DebridService
from annatar.debrid.models import StreamLink

from annatar.debrid.exceptions import ProviderException

log = structlog.get_logger(__name__)

class RealDebridProvider(DebridService):
    """Real-Debrid API provider."""

    BASE_URL = "https://api.real-debrid.com/rest/1.0"
    OAUTH_URL = "https://api.real-debrid.com/oauth/v2"
    OPENSOURCE_CLIENT_ID = "X245A4XAIBGVM"

    def __init__(self, api_key: str, source_ip: Optional[str] = None):
        """Initialize the provider with API key and optional source IP."""
        self.api_key = api_key
        self.source_ip = source_ip
        self._session = None
        self._headers = None

    async def __aenter__(self):
        """Async context manager enter."""
        if not self._session:
            await self.initialize_headers()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._session:
            await self._session.close()
            self._session = None

    def __str__(self) -> str:
        return "RealDebridProvider"

    def short_name(self) -> str:
        return "RD"

    def name(self) -> str:
        return "real-debrid.com"

    def id(self) -> str:
        return "real_debrid"

    def shared_cache(self) -> bool:
        return True

    async def _handle_service_specific_errors(self, error_data: dict, status_code: int):
        """Handle service specific errors."""
        error_code = error_data.get("error_code")
        error_message = error_data.get("error", "Unknown error")
        
        # 根据 Real-Debrid API 文档的错误代码映射
        error_mapping = {
            -1: ("Internal error", "api_error.mp4"),
            1: ("Missing parameter", "api_error.mp4"),
            2: ("Bad parameter value", "api_error.mp4"),
            3: ("Unknown method", "api_error.mp4"),
            4: ("Method not allowed", "api_error.mp4"),
            5: ("Slow down", "too_many_requests.mp4"),
            6: ("Resource unreachable", "api_error.mp4"),
            7: ("Resource not found", "file_error.mp4"),
            8: ("Bad token (expired, invalid)", "invalid_token.mp4"),
            9: ("Permission denied", "invalid_token.mp4"),
            10: ("Two-factor authentication needed", "auth_error.mp4"),
            11: ("Two-factor authentication pending", "auth_error.mp4"),
            12: ("Invalid login", "auth_error.mp4"),
            13: ("Invalid password", "auth_error.mp4"),
            14: ("Account locked", "account_error.mp4"),
            15: ("Account not activated", "account_error.mp4"),
            16: ("Unsupported hoster", "hoster_error.mp4"),
            17: ("Hoster in maintenance", "hoster_error.mp4"),
            18: ("Hoster limit reached", "hoster_error.mp4"),
            19: ("Hoster temporarily unavailable", "hoster_error.mp4"),
            20: ("Hoster not available for free users", "hoster_error.mp4"),
            21: ("Too many active downloads", "torrent_limit.mp4"),
            22: ("IP Address not allowed", "ip_not_allowed.mp4"),
            23: ("Traffic exhausted", "traffic_error.mp4"),
            24: ("File unavailable", "file_error.mp4"),
            25: ("Service unavailable", "service_error.mp4"),
            26: ("Upload too big", "upload_error.mp4"),
            27: ("Upload error", "upload_error.mp4"),
            28: ("File not allowed", "file_error.mp4"),
            29: ("Torrent too big", "torrent_error.mp4"),
            30: ("Torrent file invalid", "transfer_error.mp4"),
            31: ("Action already done", "action_error.mp4"),
            32: ("Image resolution error", "image_error.mp4"),
            33: ("Torrent already active", "torrent_error.mp4"),
            34: ("Too many requests", "too_many_requests.mp4"),
            35: ("Infringing file", "content_infringing.mp4"),
            36: ("Fair Usage Limit", "too_many_requests.mp4"),
            37: ("Disabled endpoint", "api_error.mp4"),
        }
        
        if error_code in error_mapping:
            message, video_file = error_mapping[error_code]
        else:
            message = f"Unknown error: {error_message} (code: {error_code})"
            video_file = "api_error.mp4"
            
        raise ProviderException(message, video_file)

    async def make_request(
        self,
        method: str,
        url: str,
        data: Optional[dict | str | FormData] = None,
        **kwargs,
    ) -> dict:
        if method in ["POST", "PUT"] and self.source_ip:
            if isinstance(data, dict):
                data = dict(data)  # 创建副本以避免修改原始数据
                data["ip"] = self.source_ip
            elif data is None:
                data = {"ip": self.source_ip}
            # 如果 data 是 str 或 FormData，保持原样
        return await super()._make_request(method=method, url=url, data=data, **kwargs)

    async def initialize_headers(self):
        if self.api_key:
            token_data = self.decode_token_str(self.api_key)
            if "private_token" in token_data:
                self.headers = {
                    "Authorization": f"Bearer {token_data['private_token']}"
                }
                self.is_private_token = True
            else:
                access_token_data = await self.get_token(
                    token_data["client_id"],
                    token_data["client_secret"],
                    token_data["code"],
                )
                self.headers = {
                    "Authorization": f"Bearer {access_token_data['access_token']}"
                }

    @staticmethod
    def encode_token_data(
        code: str, client_id: Optional[str] = None, client_secret: Optional[str] = None, *args, **kwargs
    ):
        token = f"{client_id}:{client_secret}:{code}"
        return b64encode(str(token).encode()).decode()

    @staticmethod
    def decode_token_str(token: str) -> dict[str, str]:
        try:
            client_id, client_secret, code = b64decode(token).decode().split(":")
        except (ValueError, BinasciiError):
            return {"private_token": token}
        return {"client_id": client_id, "client_secret": client_secret, "code": code}

    async def get_device_code(self):
        return await self.make_request(
            "GET",
            f"{self.OAUTH_URL}/device/code",
            params={"client_id": self.OPENSOURCE_CLIENT_ID, "new_credentials": "yes"},
        )

    async def get_token(self, client_id, client_secret, device_code):
        return await self.make_request(
            "POST",
            f"{self.OAUTH_URL}/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": device_code,
                "grant_type": "http://oauth.net/grant_type/device/1.0",
            },
        )

    async def authorize(self, device_code):
        response_data = await self.make_request(
            "GET",
            f"{self.OAUTH_URL}/device/credentials",
            params={"client_id": self.OPENSOURCE_CLIENT_ID, "code": device_code},
            is_expected_to_fail=True,
        )

        if "client_secret" not in response_data:
            return response_data

        token_data = await self.get_token(
            response_data["client_id"], response_data["client_secret"], device_code
        )

        if "access_token" in token_data:
            token = self.encode_token_data(
                client_id=response_data["client_id"],
                client_secret=response_data["client_secret"],
                code=token_data["refresh_token"],
            )
            return {"token": token}
        else:
            return token_data

    async def add_magnet_link(self, magnet_link):
        return await self.make_request(
            "POST", f"{self.BASE_URL}/torrents/addMagnet", data={"magnet": magnet_link}
        )

    async def add_torrent_file(self, torrent_file: bytes):
        form = FormData()
        form.add_field('file', torrent_file, filename='torrent')
        return await self.make_request(
            "PUT",
            f"{self.BASE_URL}/torrents/addTorrent",
            data=form,
        )

    async def get_active_torrents(self):
        return await self.make_request("GET", f"{self.BASE_URL}/torrents/activeCount")

    async def get_user_torrent_list(self):
        return await self.make_request("GET", f"{self.BASE_URL}/torrents")

    async def get_user_downloads(self):
        return await self.make_request("GET", f"{self.BASE_URL}/downloads")

    async def get_torrent_info(self, torrent_id):
        return await self.make_request(
            "GET", f"{self.BASE_URL}/torrents/info/{torrent_id}"
        )

    async def disable_access_token(self):
        return await self.make_request(
            "GET",
            f"{self.BASE_URL}/disable_access_token",
            is_return_none=True,
            is_expected_to_fail=True,
        )

    async def start_torrent_download(self, torrent_id, file_ids="all"):
        return await self.make_request(
            "POST",
            f"{self.BASE_URL}/torrents/selectFiles/{torrent_id}",
            data={"files": file_ids},
            is_return_none=True,
        )

    async def get_available_torrent(self, info_hash) -> Optional[dict[str, Any]]:
        available_torrents = await self.get_user_torrent_list()
        for torrent in available_torrents:
            if torrent["hash"] == info_hash:
                return torrent
        return None

    async def create_download_link(self, link):
        response = await self.make_request(
            "POST",
            f"{self.BASE_URL}/unrestrict/link",
            data={"link": link},
            is_expected_to_fail=True,
        )
        if "download" in response:
            return response

        if "error_code" in response:
            if response["error_code"] == 23:
                raise ProviderException(
                    "Exceed remote traffic limit", "exceed_remote_traffic_limit.mp4"
                )
        raise ProviderException(
            f"Failed to create download link. response: {response}", "api_error.mp4"
        )

    async def delete_torrent(self, torrent_id) -> dict:
        return await self.make_request(
            "DELETE",
            f"{self.BASE_URL}/torrents/delete/{torrent_id}",
            is_return_none=True,
        )

    async def get_user_info(self) -> dict:
        return await self.make_request("GET", f"{self.BASE_URL}/user")
