from typing import Optional, List

from pydantic import BaseModel


class TorrentFile(BaseModel):
    id: int
    path: str
    bytes: int
    selected: int = 0


class TorrentInfo(BaseModel):
    id: str
    filename: str
    hash: str
    bytes: int
    host: str
    split: int
    progress: float  # Changed from int to float to match API response
    status: str
    added: str
    files: List[TorrentFile]
    links: List[str]
    ended: Optional[str] = None


class DownloadLink(BaseModel):
    id: str
    mimeType: Optional[str] = None  # Make mimeType optional with default None
    download: str
    filename: str
    filesize: int


class DeviceCode(BaseModel):
    device_code: str
    user_code: str
    verification_url: str
    expires_in: int
    interval: int


class TokenInfo(BaseModel):
    access_token: str
    expires_in: int
    refresh_token: str
    token_type: str


class InstantFile(BaseModel):
    id: int
    filename: str
    size: int


class UnrestrictedLink(BaseModel):
    id: str
    filename: str
    mimeType: str
    filesize: int
    link: str
    host: str
    chunks: int
    crc: int
    download: str
    streamable: int
