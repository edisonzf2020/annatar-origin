import asyncio
from typing import AsyncGenerator, Optional, Any
import structlog

import aiohttp

from annatar import instrumentation, magnet
from annatar.debrid.debrid_service import DebridService
from annatar.debrid.models import StreamLink
from annatar.debrid.rd_models import (
    DownloadLink,
    TorrentInfo,
)

log = structlog.get_logger(__name__)

class RealDebridProvider(DebridService):
    BASE_URL = "https://api.real-debrid.com/rest/1.0"

    def __init__(self, api_key: str, source_ip: str):
        super().__init__(api_key, source_ip)
        self.headers = {"Authorization": f"Bearer {self.api_key}"}
        log.info("initialized RealDebrid provider", source_ip=source_ip)

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

    async def make_request(
        self,
        method: str,
        url: str,
        data: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> Any:
        if method in ["POST", "PUT"] and self.source_ip:
            data = data or {}
            data["ip"] = self.source_ip

        log.debug(
            "making RD request",
            method=method,
            url=f"{self.BASE_URL}{url}",
            data=data,
            params=params
        )

        async with aiohttp.ClientSession() as session:
            async with session.request(
                method,
                f"{self.BASE_URL}{url}",
                headers=self.headers,
                data=data,
                params=params,
            ) as response:
                if response.status in [401, 403]:
                    log.error(
                        "RD authentication failed",
                        status=response.status,
                        reason=response.reason,
                        url=url,
                    )
                    return None
                try:
                    response.raise_for_status()
                    return await response.json()
                except Exception as e:
                    log.error(
                        "RD request failed",
                        exc_info=e,
                        status=response.status,
                        url=url,
                        data=data,
                    )
                    return None

    async def wait_for_status(self, torrent_id: str, target_status: str) -> Optional[TorrentInfo]:
        """Wait for torrent to reach a specific status"""
        retry_interval = 5  # 使用 5 秒间隔，避免过多请求
        acceptable_statuses = {
            "downloaded": ["downloaded"],
            "waiting_files_selection": ["waiting_files_selection"],
        }
        
        while True:
            torrent_info = await self.get_torrent_info(torrent_id)
            if not torrent_info:
                log.warning("failed to get torrent info", torrent_id=torrent_id)
                return None
            
            # 如果目标是 downloaded，那么 queued 和 downloading 都是可接受的中间状态
            if target_status == "downloaded" and torrent_info.status in ["queued", "downloading"]:
                pass  # 继续等待
            elif torrent_info.status in acceptable_statuses.get(target_status, []):
                log.debug(
                    "torrent reached target status",
                    torrent_id=torrent_id,
                    status=target_status
                )
                return torrent_info
            elif torrent_info.status == "error":
                log.error(
                    "torrent failed with error status",
                    torrent_id=torrent_id
                )
                return None
                
            log.debug(
                "waiting for status",
                torrent_id=torrent_id,
                current_status=torrent_info.status,
                target_status=target_status,
                progress=torrent_info.progress
            )
            await asyncio.sleep(retry_interval)

    async def get_stream_links(
        self,
        torrents: list[str],
        stop: asyncio.Event,
        max_results: int,
        season: int = 0,
        episode: int = 0,
    ) -> AsyncGenerator[StreamLink, None]:
        """Get stream links for torrents"""
        log.info(
            "getting stream links",
            torrents_count=len(torrents),
            season=season,
            episode=episode
        )

        for info_hash in torrents[:max_results]:
            if stop.is_set():
                log.info("stopping stream link generation - received stop signal")
                break

            log.debug("processing torrent", info_hash=info_hash)

            # Add magnet
            torrent_id = await self.add_magnet(info_hash)
            if not torrent_id:
                log.warning("failed to add magnet", info_hash=info_hash)
                continue

            # Get torrent info and wait for file selection
            torrent_info = await self.wait_for_status(torrent_id, "waiting_files_selection")
            if not torrent_info:
                log.warning("failed to get torrent info", torrent_id=torrent_id)
                continue

            # Select and start download
            file_id = await self.select_appropriate_file(torrent_info, season, episode)
            if not file_id:
                log.warning("no appropriate file found", torrent_id=torrent_id)
                continue

            log.debug("starting download", torrent_id=torrent_id, file_id=file_id)
            await self.start_torrent_download(torrent_id, file_id)
            
            # Wait for download
            torrent_info = await self.wait_for_status(torrent_id, "downloaded")
            if not torrent_info:
                log.warning("download failed", torrent_id=torrent_id)
                continue

            download_link = await self.get_download_link(torrent_info.links[0])
            if not download_link:
                log.warning("failed to get download link", torrent_id=torrent_id)
                continue

            log.info(
                "got stream link",
                size=download_link.filesize,
                name=download_link.filename
            )
            
            yield StreamLink(
                size=download_link.filesize,
                name=download_link.filename,
                url=download_link.download
            )

    async def add_magnet(self, info_hash: str) -> Optional[str]:
        """Add a magnet link and return torrent ID"""
        # magnet = f"magnet:?xt=urn:btih:{info_hash}"
        response = await self.make_request(
            "POST", 
            "/torrents/addMagnet",
            data={"magnet": magnet.make_magnet_link(info_hash=info_hash)}
        )
        if response:
            log.debug("added magnet", info_hash=info_hash, torrent_id=response.get("id"))
        return response.get("id") if response else None

    async def get_torrent_info(self, torrent_id: str) -> Optional[TorrentInfo]:
        """Get information about a torrent"""
        response = await self.make_request(
            "GET",
            f"/torrents/info/{torrent_id}"
        )
        if response:
            try:
                info = TorrentInfo.model_validate(response)
                log.debug(
                    "got torrent info",
                    torrent_id=torrent_id,
                    status=info.status,
                    files_count=len(info.files or [])  # 使用 or [] 来处理 None 的情况
                )
                return info
            except Exception as e:
                log.error(
                    "failed to validate torrent info",
                    exc_info=e,
                    torrent_id=torrent_id,
                    response=response
                )
        return None

    async def select_appropriate_file(
        self,
        torrent_info: TorrentInfo,
        season: int = 0,
        episode: int = 0
    ) -> Optional[int]:
        """Select appropriate file based on season/episode if applicable"""
        if not torrent_info.files:
            log.warning("no files in torrent info")
            return None

        if len(torrent_info.files) == 1:
            file_id = torrent_info.files[0].id
            log.debug("selected single file", file_id=file_id)
            return file_id
        
        # TODO: Add your file selection logic here
        file_id = torrent_info.files[0].id
        log.debug(
            "selected first file (default)",
            file_id=file_id,
            season=season,
            episode=episode
        )
        return file_id

    async def start_torrent_download(self, torrent_id: str, file_id: int) -> bool:
        """Start downloading a torrent"""
        try:
            await self.make_request(
                "POST",
                f"{self.BASE_URL}/torrents/selectFiles/{torrent_id}",
                data={"files": str(file_id)}
            )
            return True
        except Exception as e:
            log.warning(
                "failed to start download",
                torrent_id=torrent_id,
                file_id=file_id,
                error=str(e)
            )
            return False

    async def get_download_link(self, link: str) -> Optional[DownloadLink]:
        """Get download link for a file"""
        response = await self.make_request(
            "POST",
            "/unrestrict/link",
            data={"link": link}
        )
        if response:
            try:
                download_link = DownloadLink.model_validate(response)
                log.debug(
                    "got download link",
                    filename=download_link.filename,
                    size=download_link.filesize
                )
                return download_link
            except Exception as e:
                log.error(
                    "failed to validate download link",
                    exc_info=e,
                    response=response
                )
        return None
