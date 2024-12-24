from typing import Optional, List

from pydantic import BaseModel

class InstantFileSet(BaseModel):
    file_ids: list[int]


class InstantFile(BaseModel):
    id: int
    filename: str
    filesize: int

class StreamableFile(BaseModel):
    id: int
    link: str
    size: int

class TorrentFile(BaseModel):
    id: int
    path: str
    bytes: int
    selected: int = 0


class TorrentInfo(BaseModel):
    added: str
    bytes: int
    filename: str
    hash: str
    host: str
    id: str
    links: list[str]
    progress: float
    split: int
    status: str

    ended: Optional[str] = None
    files: Optional[list[TorrentFile]] = None
    original_bytes: Optional[int] = None
    original_filename: Optional[str] = None
    seeders: Optional[int] = None
    speed: Optional[int] = None

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
