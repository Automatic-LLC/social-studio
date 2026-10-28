"""Pexels stock-video client: search portrait clips, download one, and build the credit line."""
from __future__ import annotations

from pathlib import Path

from social_studio import http

SEARCH_URL = "https://api.pexels.com/videos/search"
TARGET_HEIGHT = 1920


def _best_file(files: list[dict]) -> dict | None:
    """Closest to 1080x1920: the smallest mp4 at least 1920 tall, else the largest one."""
    mp4 = [f for f in files if f.get("file_type") == "video/mp4" and f.get("link")]
    if not mp4:
        return None
    big = [f for f in mp4 if (f.get("height") or 0) >= TARGET_HEIGHT]
    if big:
        return min(big, key=lambda f: ((f.get("height") or 0), (f.get("width") or 0)))
    return max(mp4, key=lambda f: ((f.get("height") or 0), (f.get("width") or 0)))


def search(query: str, key: str, *, per_page: int = 15, orientation: str = "portrait", min_seconds: float = 3,
           max_seconds: float = 60, session=None) -> list[dict]:
    """Videos for `query` within the duration range, each with the best mp4 file picked."""
    if not key:
        raise ValueError("Pexels API key is empty")
    r = http.request("GET", SEARCH_URL, session=session, headers={"Authorization": key},
                     params={"query": query, "orientation": orientation, "size": "medium", "per_page": per_page})
    out: list[dict] = []
    for v in r.json().get("videos", []):
        if not min_seconds <= (v.get("duration") or 0) <= max_seconds:
            continue
        f = _best_file(v.get("video_files") or [])
        if not f:
            continue
        user = v.get("user") or {}
        out.append({
            "id": v["id"], "page_url": v.get("url"), "user": user.get("name"), "user_url": user.get("url"),
            "duration": v["duration"], "link": f["link"], "width": f.get("width"), "height": f.get("height"),
        })
    return out


def download(item: dict, dest_dir: Path, session=None) -> Path:
    """Save the clip as dest_dir/pexels_<id>.mp4 (streamed); an existing file is reused."""
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / f"pexels_{item['id']}.mp4"
    if path.is_file() and path.stat().st_size > 0:
        return path
    part = path.with_suffix(".mp4.part")
    r = http.request("GET", item["link"], session=session, stream=True, timeout=120)
    try:
        with r, open(part, "wb") as fh:
            for chunk in r.iter_content(chunk_size=1 << 20):
                if chunk:
                    fh.write(chunk)
        part.replace(path)
    finally:
        part.unlink(missing_ok=True)
    return path


def credit(item: dict) -> str:
    return f"Video by {item['user']} on Pexels"
