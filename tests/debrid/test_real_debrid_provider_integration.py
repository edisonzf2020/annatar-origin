"""Integration tests for RealDebridProvider class using real API."""
import os
import pytest
import asyncio
import aiohttp
from dotenv import load_dotenv

from annatar.debrid.real_debrid_provider import RealDebridProvider
from annatar.debrid.models import StreamLink
from annatar.debrid.exceptions import ProviderException

# 加载环境变量
load_dotenv()

def test_env_variables():
    """Test that environment variables are loaded correctly."""
    api_key = os.getenv("REAL_DEBRID_API_KEY")
    assert api_key is not None, "REAL_DEBRID_API_KEY not found in environment"

# 跳过所有测试如果没有 API key
pytestmark = [
    pytest.mark.skipif(
        not os.getenv("REAL_DEBRID_API_KEY"),
        reason="REAL_DEBRID_API_KEY not set in environment"
    ),
    pytest.mark.asyncio  # 标记所有测试为异步
]

@pytest.fixture
async def provider():
    """Async fixture for RealDebridProvider."""
    api_key = os.getenv("REAL_DEBRID_API_KEY")
    if not api_key:
        pytest.skip("REAL_DEBRID_API_KEY not set")
    
    provider = RealDebridProvider(api_key=api_key, source_ip="1.1.1.1")
    await provider.initialize_headers()
    try:
        yield provider
    finally:
        if hasattr(provider, '_session') and provider._session:
            await provider._session.close()

async def test_provider_properties(provider):
    """Test provider's basic properties."""
    async with provider as p:
        assert p.id() == "real_debrid"
        assert p.name() == "real-debrid.com"
        assert p.short_name() == "RD"
        assert isinstance(p.shared_cache(), bool)

async def test_get_active_torrents_real_api(provider):
    """Test getting active torrents from real API."""
    async with provider as p:
        try:
            result = await p.get_active_torrents()
            assert isinstance(result, (dict, list))  # 可能返回字典或列表
        except ProviderException as e:
            if "Bad token" in str(e):
                pytest.skip("API key is invalid or expired")
            raise

async def test_get_user_info(provider):
    """Test getting user information."""
    async with provider as p:
        try:
            result = await p.get_user_info()
            assert isinstance(result, dict)
            assert "id" in result
        except ProviderException as e:
            if "Bad token" in str(e):
                pytest.skip("API key is invalid or expired")
            raise

async def test_get_stream_links(provider):
    """Test getting stream links."""
    async with provider as p:
        stop = asyncio.Event()
        count = 0
        async for link in p.get_stream_links(
            torrents=["test_torrent"],
            stop=stop,
            max_results=1
        ):
            assert isinstance(link, StreamLink)
            assert link.name
            assert link.size > 0
            assert link.url
            count += 1
            break  # 只测试第一个结果
        assert count == 1

async def test_invalid_api_key():
    """Test behavior with invalid API key."""
    invalid_provider = RealDebridProvider(api_key="invalid_key", source_ip="1.1.1.1")
    await invalid_provider.initialize_headers()
    try:
        with pytest.raises(ProviderException) as exc_info:
            await invalid_provider.get_user_info()
        assert "Bad token" in str(exc_info.value)
    finally:
        if hasattr(invalid_provider, '_session') and invalid_provider._session:
            await invalid_provider._session.close()

async def test_add_and_get_torrent_info(provider):
    """Test adding a torrent and getting its info.
    注意：这个测试需要一个有效的种子文件。
    """
    pytest.skip("Needs actual torrent file to test")
