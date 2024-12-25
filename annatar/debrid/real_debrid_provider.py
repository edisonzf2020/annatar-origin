import asyncio
from typing import AsyncGenerator, Optional

from annatar.debrid import rd
from annatar.debrid.debrid_service import DebridService
from annatar.debrid.models import StreamLink


class RealDebridProvider(DebridService):
    # def __init__(self, api_key: str, source_ip: Optional[str] = None):
    #     """Initialize the provider with API key and optional source IP."""
    #     super().__init__(api_key=api_key, source_ip=source_ip)  # 调用父类的初始化方法
    #     self.api_key = api_key
    #     self.source_ip = source_ip

    def __str__(self) -> str:
        return "RealDebridProvider"

    def short_name(self) -> str:
        return "RD"

    def name(self) -> str:
        return "real-debrid.com"

    def id(self) -> str:
        return "real_debrid"

    def shared_cache(self):
        return True

    async def get_stream_links(
        self,
        torrents: list[str],
        stop: asyncio.Event,
        max_results: int,
        season: int = 0,
        episode: int = 0,
    ) -> AsyncGenerator[StreamLink, None]:
        async for sl in rd.get_stream_links(
            torrents=torrents,
            debrid_token=self.api_key,
            stop=stop,
            max_results=max_results,
            season=season,
            episode=episode,
        ):
            yield sl

    async def get_stream_for_torrent(
        self,
        info_hash: str,
        file_id: int,
        debrid_token: str,
    ) -> Optional[StreamLink]:
        return await rd.get_stream_for_torrent(
            info_hash=info_hash,
            file_id=file_id,
            debrid_token=debrid_token,
            source_ip=self.source_ip,
        )
