from pydantic import BaseModel, Field, ConfigDict, field_validator
from beanie import Document, PydanticObjectId
from enum import StrEnum

from typing import Optional, Any
from datetime import datetime
import pymongo
from pymongo import IndexModel, ASCENDING, DESCENDING
import pytz


class StreamLink(BaseModel):
    size: int
    name: str
    url: str

class Episode(BaseModel):
    episode_number: int
    filename: str | None = None
    size: int | None = None
    file_index: int | None = None
    title: str | None = None
    released: datetime | None = None


class Season(BaseModel):
    season_number: int
    episodes: list[Episode]

# Enums
class MediaType(StrEnum):
    MOVIE = "movie"
    SERIES = "series"
    TV = "tv"
    EVENTS = "events"


class TorrentType(StrEnum):
    PUBLIC = "public"
    SEMI_PRIVATE = "semi-private"
    PRIVATE = "private"
    WEB_SEED = "web-seed"


class NudityStatus(StrEnum):
    NONE = "None"
    MILD = "Mild"
    MODERATE = "Moderate"
    SEVERE = "Severe"
    UNKNOWN = "Unknown"
    DISABLE = "Disable"

class TorrentStreams(Document):
    model_config = ConfigDict(extra="allow")

    id: str
    meta_id: str
    torrent_name: str
    size: int
    season: Optional[Season] = None
    filename: Optional[str] = None
    file_index: Optional[int] = None
    announce_list: list[str]
    languages: list[str]
    source: str
    catalog: list[str]
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    resolution: Optional[str] = None
    codec: Optional[str] = None
    quality: Optional[str] = None
    audio: Optional[str] = None
    seeders: Optional[int] = None
    torrent_type: Optional[TorrentType] = TorrentType.PUBLIC
    is_blocked: Optional[bool] = False
    torrent_file: bytes | None = None
    cached: bool = Field(default=False, description="Whether the torrent is cached in Debrid")

    def __eq__(self, other):
        if not isinstance(other, TorrentStreams):
            return False
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

    @field_validator("id", mode="after")
    def validate_id(cls, v):
        return v.lower()

    @field_validator("created_at", mode="after")
    def validate_created_at(cls, v):
        # convert to UTC
        return v.astimezone(pytz.utc)

    @field_validator("audio", mode="before")
    def validate_audio(cls, v):
        # Ensure audio is a string
        if v and isinstance(v, list):
            return v[0]
        return v

    class Settings:
        indexes = [
            IndexModel(
                [
                    ("meta_id", ASCENDING),
                    ("created_at", DESCENDING),
                    ("catalog", ASCENDING),
                ]
            )
        ]

    def get_episode(self, season_number: int, episode_number: int) -> Optional[Episode]:
        """
        Returns the Episode object for the given season and episode number.
        """
        if self.season and self.season.season_number == season_number:
            for episode in self.season.episodes:
                if episode.episode_number == episode_number:
                    return episode
        return None