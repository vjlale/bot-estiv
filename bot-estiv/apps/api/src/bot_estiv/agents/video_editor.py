"""VideoEditor: textos + logo + formato 9:16 para historias."""
from __future__ import annotations

import logging
from pathlib import Path
from tempfile import TemporaryDirectory

from ..tools import storage, video

logger = logging.getLogger(__name__)


async def edit_story(input_bytes: bytes, headline: str) -> str:
    with TemporaryDirectory(prefix="bot_estiv_vid_") as td:
        out = video.story_pipeline(input_bytes, headline, Path(td))
    key = storage.new_key("videos/story", "mp4")
    return storage.upload_bytes(out, key, content_type="video/mp4")
