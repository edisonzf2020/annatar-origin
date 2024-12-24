
# from db import schemas
# from db.config import settings
# from utils import const
# from utils.runtime_const import PRIVATE_CIDR
# from db.redis_database import REDIS_ASYNC_CLIENT

def is_video_file(filename: str) -> bool:
    """
    Fast check if a filename is a playable video format supported by
    modern media players (VLC, MPV, etc.)

    Covers all modern containers and formats including
    - Modern streaming formats (HLS, DASH)
    - High-efficiency containers (MKV, MP4, WebM)
    - Professional formats that are commonly playable
    - Network streaming formats

    Args:
        filename: URL or filename to check

    Returns:
        bool: True if the filename is a playable video format
    """
    return filename.lower().endswith(
        (
            # Modern Containers (most common first)
            ".mp4",  # MPEG-4 Part 14
            ".mkv",  # Matroska
            ".webm",  # WebM
            ".m4v",  # MPEG-4
            ".mov",  # QuickTime
            # Streaming Formats
            ".m3u8",  # HLS
            ".m3u",  # Playlist
            ".mpd",  # DASH
            # MPEG Transport Streams
            ".ts",  # Transport Stream
            ".mts",  # MPEG Transport Stream
            ".m2ts",  # Blu-ray Transport Stream
            ".m2t",  # MPEG-2 Transport Stream
            # MPEG Program Streams
            ".mpeg",  # MPEG Program Stream
            ".mpg",  # MPEG Program Stream
            ".mp2",  # MPEG Program Stream
            ".m2v",  # MPEG-2 Video
            ".m4p",  # Protected MPEG-4 Part 14
            # Common Legacy Formats (still widely supported)
            ".avi",  # Audio Video Interleave
            ".wmv",  # Windows Media Video
            ".flv",  # Flash Video
            ".f4v",  # Flash MP4 Video
            ".ogv",  # Ogg Video
            ".ogm",  # Ogg Media
            ".rm",  # RealMedia
            ".rmvb",  # RealMedia Variable Bitrate
            ".asf",  # Advanced Systems Format
            ".divx",  # DivX Video
            # Mobile Formats
            ".3gp",  # 3GPP
            ".3g2",  # 3GPP2
            # DVD/Blu-ray Formats
            ".vob",  # DVD Video Object
            ".ifo",  # DVD Information
            ".bdmv",  # Blu-ray Movie
            # Modern High-Efficiency Formats
            ".hevc",  # High Efficiency Video Coding
            ".av1",  # AOMedia Video 1
            ".vp8",  # WebM VP8
            ".vp9",  # WebM VP9
            # Additional Modern Formats
            ".mxf",  # Material eXchange Format (broadcast)
            ".dav",  # DVR365 Format
            ".swf",  # Shockwave Flash (contains video)
            # Network Streaming
            ".nsv",  # Nullsoft Streaming Video
            ".strm",  # Stream file
            # Additional Container Formats
            ".mvi",  # Motion Video Interface
            ".vid",  # Generic video file
            ".amv",  # Anime Music Video
            ".m4s",  # MPEG-DASH Segment
            ".mqv",  # Sony Movie Format
            ".nuv",  # NuppelVideo
            ".wtv",  # Windows Recorded TV Show
            ".dvr-ms",  # Microsoft Digital Video Recording
            # Playlist Formats
            ".pls",  # Playlist File
            ".cue",  # Cue Sheet
            # Modern Streaming Service Formats
            ".dash",  # DASH
            ".hls",  # HLS Alternative
            ".ismv",  # Smooth Streaming
            ".m4f",  # Protected MPEG-4 Fragment
            ".mp4v",  # MPEG-4 Video
            # Animation Formats (playable in video players)
            ".gif",  # Graphics Interchange Format
            ".gifv",  # Imgur Video Alternative
            ".apng",  # Animated PNG
        )
    )

