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
from annatar.debrid.rd_models import InstantFile, TorrentInfo, UnrestrictedLink

from annatar.debrid.exceptions import ProviderException

from fastapi import BackgroundTasks

from annatar.debrid.models import TorrentStreams
from annatar.debrid.parser import (
    select_file_index_from_torrent,
    update_torrent_streams_metadata,
)

log = structlog.get_logger(__name__)

class RealDebridProvider(DebridService):
    """Real-Debrid API provider."""

    BASE_URL = "https://api.real-debrid.com/rest/1.0"
    OAUTH_URL = "https://api.real-debrid.com/oauth/v2"
    OPENSOURCE_CLIENT_ID = "X245A4XAIBGVM"

    def __init__(self, api_key: str, source_ip: Optional[str] = None):
        """Initialize the provider with API key and optional source IP."""
        super().__init__(api_key=api_key, source_ip=source_ip)  # 调用父类的初始化方法
        self.api_key = api_key
        self.source_ip = source_ip
        self._session = None
        self._headers = None
        self.headers = {"Authorization": f"Bearer {api_key}"}  # 直接设置认证头

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
        await super().__aexit__(exc_type, exc_val, exc_tb)  # 调用父类的 __aexit__ 方法

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

    async def get_stream_links(
        self,
        torrents: list[str],
        stop: asyncio.Event,
        max_results: int,
        season: int = 0,
        episode: int = 0,
    ) -> AsyncGenerator[StreamLink, None]:
        """Get stream links for a list of torrents.
        
        Args:
            torrents: List of magnet links or info hashes
            stop: Event to stop processing
            max_results: Maximum number of results to return
            season: Season number for TV shows
            episode: Episode number for TV shows
        """
        try:
            log.info(
                "getting RealDebrid stream links",
                torrents_count=len(torrents),
                season=season,
                episode=episode
            )

            # 通过get_user_info 得到用户信息，log用户信息
            # user_info = await self.get_user_info()
            # log.info("got RealDebrid user info", user_info=user_info)

            # 一次性获取所有缓存的种子信息
            # cached_torrents = await self.get_cached_torrents(torrents)
            
            # 通过 get_stream_for_torrent 循环获得流媒体链接
            for torrent in torrents:
                if stop.is_set():
                    break
                # 如果是磁力链接，提取info_hash
                # info_hash = torrent.split("btih:")[-1].split("&")[0].lower() if "magnet:" in torrent else torrent
                # log.info("processing torrent", info_hash=info_hash)
                
                stream_link = await self.get_stream_for_torrent(torrent, 0)
                log.info("got RealDebrid stream link", stream_link=stream_link)
                if stream_link:
                    yield stream_link
        finally:
            # 确保在生成器完成时关闭session
            if self._session:
                await self._session.close()
                self._session = None

    async def get_cached_torrents(self, torrents: list[str]) -> dict[str, dict[str, Any]]:
        """获取多个种子的缓存状态
        
        Args:
            torrents: 种子hash列表
            
        Returns:
            dict: key为种子hash，value为种子信息的字典
        """
        # 获取所有已缓存的种子
        available_torrents = await self.get_user_torrent_list()
        
        # 创建缓存字典，key为小写的hash
        cache_dict = {torrent["hash"].lower(): torrent for torrent in available_torrents}
        
        # 检查每个请求的种子是否在缓存中
        result = {}
        for torrent in torrents:
            # 如果是磁力链接，提取info_hash
            info_hash = torrent.split("btih:")[-1].split("&")[0].lower() if "magnet:" in torrent else torrent.lower()
            if info_hash in cache_dict:
                result[info_hash] = cache_dict[info_hash]
        
        log.info("checked cached torrents", total=len(torrents), cached=len(result))
        return result

    async def get_stream_for_torrent(
        self,
        info_hash: str,
        file_id: int,
    ) -> Optional[StreamLink]:
        """Get a stream link for a specific torrent file.
        
        Args:
            info_hash: Torrent info hash
            file_id: File ID within the torrent
        """
        try:
            # Get torrent info
            torrent_info: TorrentInfo | None = await self.get_available_torrent(info_hash)
            log.info("checked a torrent info response from RealDebrid", info_hash=info_hash, torrent_info=torrent_info)
            if not torrent_info:
                return None

            # 如果种子已下载完成且有链接，直接返回
            if not torrent_info:
                log.info("failed to get RealDebrid torrent info", info_hash=info_hash)
                return None
            if torrent_info.get("links"):
                url: str = f"/rd/{self.api_key}/{info_hash}/{torrent_info.get('id')}/{torrent_info.get('filename')}"
                return StreamLink(
                    name=torrent_info.get("filename"),
                    size=torrent_info.get("bytes"),
                    url=url
                )

            return None

        except (KeyError, IndexError, ProviderException):
            return None

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
        """获取单个种子的缓存状态（已弃用，请使用get_cached_torrents）"""
        available_torrents = await self.get_user_torrent_list()
        info_hash = info_hash.lower()  # 将输入的info_hash转换为小写
        for torrent in available_torrents:
            torrent_hash = torrent["hash"].lower()  # 将RealDebrid返回的hash转换为小写
            if torrent_hash == info_hash:
                return torrent
        return None

    async def _create_download_link(self, link):
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

    async def create_download_link(
        self,
        magnet_link: str,
        torrent_info: dict,
        filename: Optional[str],
        file_index: Optional[int],
        episode: Optional[int],
        season: Optional[int],
        stream: TorrentStreams,
        background_tasks: BackgroundTasks,
        max_retries: int,
        retry_interval: int,
    ) -> str:
        selected_file_index = await select_file_index_from_torrent(
            torrent_info,
            filename,
            episode,
            "files",
            "path",
            "bytes",
            True,
        )

        if filename is None or file_index is None:
            background_tasks.add_task(
                update_torrent_streams_metadata,
                torrent_stream=stream,
                torrent_info=torrent_info,
                file_index=selected_file_index,
                season=season,
                file_key="files",
                name_key="path",
                size_key="bytes",
                remove_leading_slash=True,
                is_index_trustable=True,
            )

        relevant_file = torrent_info["files"][selected_file_index]
        selected_files = [file for file in torrent_info["files"] if file["selected"] == 1]

        if relevant_file not in selected_files or len(selected_files) != len(
            torrent_info["links"]
        ):
            await self.delete_torrent(torrent_info["id"])
            add_magnet_response = await self.add_magnet_link(magnet_link)
            if not add_magnet_response or "id" not in add_magnet_response:
                raise ProviderException(
                    "Failed to add magnet link",
                    "transfer_error.mp4",
                )
            torrent_id = add_magnet_response["id"]
            
            torrent_info = await self.wait_for_status(
                torrent_id, "waiting_files_selection", max_retries, retry_interval
            )
            
            file_id = torrent_info["files"][selected_file_index]["id"]
            if not isinstance(file_id, str):
                raise ProviderException(
                    "Invalid file ID",
                    "transfer_error.mp4",
                )
                
            await self.start_torrent_download(torrent_id, file_ids=file_id)
            
            torrent_info = await self.wait_for_status(
                torrent_id, "downloaded", max_retries, retry_interval
            )
            link_index = 0
        else:
            link_index = selected_files.index(relevant_file)

        if not torrent_info.get("links") or not isinstance(torrent_info["links"], list):
            raise ProviderException(
                "No download links available",
                "transfer_error.mp4",
            )

        response = await self._create_download_link(torrent_info["links"][link_index])
        
        mime_type = response.get("mimeType")
        if not mime_type or not isinstance(mime_type, str) or not mime_type.startswith("video"):
            await self.delete_torrent(torrent_info["id"])
            raise ProviderException(
                f"Requested file is not a video file, deleting torrent and retrying. {mime_type}",
                "torrent_not_downloaded.mp4",
            )

        download_url = response.get("download")
        if not download_url or not isinstance(download_url, str):
            raise ProviderException(
                "No download URL available",
                "transfer_error.mp4",
            )

        return download_url


    async def get_video_url_from_realdebrid(
        self,
        info_hash: str,
        magnet_link: str,
        filename: Optional[str],
        file_index: Optional[int],
        stream: TorrentStreams,
        background_tasks: BackgroundTasks,
        max_retries: int = 5,
        retry_interval: int = 5,
        episode: Optional[int] = None,
        season: Optional[int] = None,
        **kwargs,
    ) -> str:        
        torrent_info = await self.get_available_torrent(info_hash)

        if not torrent_info:
            torrent_info = await self.add_new_torrent(
                magnet_link, info_hash, stream
            )

        torrent_id = torrent_info["id"]
        status = torrent_info["status"]

        if status in ["magnet_error", "error", "virus", "dead"]:
            await self.delete_torrent(torrent_id)
            raise ProviderException(
                f"Torrent cannot be downloaded due to status: {status}",
                "transfer_error.mp4",
            )

        if status not in ["queued", "downloading", "downloaded"]:
            torrent_info = await self.wait_for_status(
                torrent_id,
                "waiting_files_selection",
                max_retries,
                retry_interval,
                torrent_info,
            )
            try:
                await self.start_torrent_download(
                    torrent_info["id"],
                    file_ids="all",
                )
            except ProviderException as error:
                await self.delete_torrent(torrent_id)
                raise ProviderException(
                    f"Failed to start torrent download, {error}", "transfer_error.mp4"
                )

        torrent_info = await self.wait_for_status(
            torrent_id, "downloaded", max_retries, retry_interval
        )

        return await self.create_download_link(            
            magnet_link,
            torrent_info,
            filename,
            file_index,
            episode,
            season,
            stream,
            background_tasks,
            max_retries,
            retry_interval,
        )


    async def add_new_torrent(self, magnet_link, info_hash, stream):
        response = await self.get_active_torrents()
        if response["limit"] == response["nb"]:
            raise ProviderException(
                "Torrent limit reached. Please try again later.", "torrent_limit.mp4"
            )
        if info_hash in response["list"]:
            raise ProviderException(
                "Torrent is already being downloading", "torrent_not_downloaded.mp4"
            )

        if stream.torrent_file:
            torrent_id = (await self.add_torrent_file(stream.torrent_file)).get("id")
        else:
            torrent_id = (await self.add_magnet_link(magnet_link)).get("id")

        if not torrent_id:
            raise ProviderException(
                "Failed to add magnet link to Real-Debrid", "transfer_error.mp4"
            )

        return await self.get_torrent_info(torrent_id)


    async def update_rd_cache_status(
        self, streams: list[TorrentStreams], **kwargs
    ):
        """Updates the cache status of streams based on user's downloaded torrents in RealDebrid."""

        try:
            downloaded_hashes = set(
                await self.fetch_downloaded_info_hashes_from_rd(**kwargs)
            )
            if not downloaded_hashes:
                return
            for stream in streams:
                stream.cached = stream.id in downloaded_hashes

        except ProviderException:
            pass


    async def fetch_downloaded_info_hashes_from_rd(
        self, 
        **kwargs
    ) -> list[str]:
        """Fetches the info_hashes of all torrents downloaded in the RealDebrid account."""
        try:
            available_torrents = await self.get_user_torrent_list()
            return [
                torrent["hash"]
                for torrent in available_torrents
                if torrent["status"] == "downloaded"
            ]

        except ProviderException:
            return []


    async def delete_all_watchlist_rd(self, **kwargs):
        """Deletes all torrents from the RealDebrid watchlist."""
        torrents = await self.get_user_torrent_list()
        semaphore = asyncio.Semaphore(3)

        async def delete_torrent(torrent_id):
            async with semaphore:
                await self.delete_torrent(torrent_id)

        await asyncio.gather(
            *[delete_torrent(torrent["id"]) for torrent in torrents],
            return_exceptions=True,
        )


    async def validate_realdebrid_credentials(self, **kwargs) -> dict:
        """Validates the RealDebrid credentials."""
        try:
            await self.get_user_info()
            return {"status": "success"}
        except ProviderException as error:
            return {
                "status": "error",
                "message": f"Failed to verify RealDebrid credential, error: {error.message}",
            }
