import pytest
from unittest.mock import Mock, patch, AsyncMock
import aiohttp
from aiohttp import FormData

from annatar.debrid.real_debrid_provider import RealDebridProvider
from annatar.debrid.exceptions import ProviderException

@pytest.fixture
def provider():
    return RealDebridProvider(api_key="test_key", source_ip="1.1.1.1")

@pytest.fixture
def mock_response():
    mock = Mock()
    mock.status = 200
    mock.json = AsyncMock(return_value={"success": True})
    mock.text = AsyncMock(return_value="response text")
    return mock

@pytest.mark.asyncio
async def test_make_request_with_source_ip(provider, mock_response):
    """测试 make_request 方法在 POST/PUT 请求中正确添加 source_ip"""
    with patch.object(provider, '_make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"success": True}
        
        # 测试 POST 请求
        await provider.make_request("POST", "test_url", data={"test": "data"})
        mock_request.assert_called_with(
            method="POST",
            url="test_url",
            data={"test": "data", "ip": "1.1.1.1"}
        )
        
        # 测试 PUT 请求
        await provider.make_request("PUT", "test_url")
        mock_request.assert_called_with(
            method="PUT",
            url="test_url",
            data={"ip": "1.1.1.1"}
        )

@pytest.mark.asyncio
async def test_add_torrent_file(provider):
    """测试添加种子文件功能"""
    with patch.object(provider, 'make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"id": "test_id"}
        test_bytes = b"test torrent content"
        
        result = await provider.add_torrent_file(test_bytes)
        
        # 验证调用参数
        args = mock_request.call_args
        assert args[0][0] == "PUT"  # 验证 HTTP 方法
        assert "torrents/addTorrent" in args[0][1]  # 验证 URL
        assert isinstance(args[1]["data"], FormData)  # 验证数据类型
        assert result == {"id": "test_id"}

@pytest.mark.asyncio
async def test_handle_service_specific_errors(provider):
    """测试特定服务错误处理"""
    with pytest.raises(ProviderException, match="Invalid API key"):
        await provider._handle_service_specific_errors({"error": "bad_token"}, 401)
        
    with pytest.raises(ProviderException, match="Invalid magnet link"):
        await provider._handle_service_specific_errors({"error_code": 30}, 400)

@pytest.mark.asyncio
async def test_encode_token_data():
    """测试 token 数据编码"""
    result = RealDebridProvider.encode_token_data(
        code="test_code",
        client_id="test_client",
        client_secret="test_secret"
    )
    assert isinstance(result, str)
    assert len(result) > 0

@pytest.mark.asyncio
async def test_initialize_headers(provider):
    """测试头部初始化"""
    await provider.initialize_headers()
    assert "Authorization" in provider.headers
    assert provider.headers["Authorization"].startswith("Bearer ")

@pytest.mark.asyncio
async def test_get_active_torrents(provider):
    """测试获取活动种子列表"""
    with patch.object(provider, 'make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = [{"id": "1", "status": "downloading"}]
        
        result = await provider.get_active_torrents()
        
        mock_request.assert_called_with(
            "GET",
            f"{provider.BASE_URL}/torrents",
        )
        assert isinstance(result, list)
        assert result[0]["id"] == "1"

@pytest.mark.asyncio
async def test_error_handling(provider):
    """测试错误处理"""
    with pytest.raises(ProviderException):
        await provider._handle_service_specific_errors(
            {"error": "unknown_error"},
            500
        )

@pytest.mark.asyncio
async def test_get_torrent_info(provider):
    """测试获取种子信息"""
    with patch.object(provider, 'make_request', new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"id": "test_id", "status": "downloaded"}
        
        result = await provider.get_torrent_info("test_id")
        
        mock_request.assert_called_with(
            "GET",
            f"{provider.BASE_URL}/torrents/info/test_id",
        )
        assert result["id"] == "test_id"
