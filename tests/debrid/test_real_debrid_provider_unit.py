"""Unit tests for RealDebridProvider class."""
import os
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from dotenv import load_dotenv

from annatar.debrid.real_debrid_provider import RealDebridProvider
from annatar.debrid.models import StreamLink
from annatar.debrid.exceptions import ProviderException

# 加载环境变量
load_dotenv()

# 从日志中提取的真实测试数据
TEST_DATA = {
    "magnet1": {
        "info_hash": "E1D1B1E4DB737096C510615A234A1ACFE1E7BDC9",
        "torrent_id": "KTFJREOGBU3FO",
        "files_count": 13,
        "status": "waiting_files_selection",
        "file_id": 1
    },
    "magnet2": {
        "info_hash": "F77CD14B548C8191002639DF0779D066CC663FA1",
        "torrent_id": "34MCTQ76NH6VW",
        "files_count": 3,
        "status": "waiting_files_selection",
        "file_id": 1
    }
}

@pytest.fixture
def mock_session():
    """Create a mock aiohttp ClientSession."""
    mock = AsyncMock()
    mock.request = AsyncMock()
    return mock

@pytest.fixture
def provider(mock_session):
    """Create a RealDebridProvider instance."""
    api_key = os.getenv("REAL_DEBRID_API_KEY", "test_key")
    provider = RealDebridProvider(api_key=api_key, source_ip="1.1.1.1")
    provider._session = mock_session  # 使用 _session 而不是 session
    provider.headers = {"Authorization": f"Bearer {api_key}"}
    return provider

@pytest.mark.asyncio
async def test_add_magnet(provider, mock_session):
    """Test adding a magnet link."""
    magnet_data = TEST_DATA["magnet1"]
    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "id": magnet_data["torrent_id"],
        "uri": f"magnet:?xt=urn:btih:{magnet_data['info_hash']}"
    }
    mock_session.request.return_value.__aenter__.return_value = mock_response

    # 使用正确的方法名 add_magnet_link
    magnet_link = f"magnet:?xt=urn:btih:{magnet_data['info_hash']}"
    result = await provider.add_magnet_link(magnet_link)
    assert result["id"] == magnet_data["torrent_id"]
    assert result["uri"] == magnet_link
