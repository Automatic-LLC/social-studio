"""Supabase: the posts table (PostgREST) and the media bucket (Storage). Uses the project's secret key.

Only Social Studio's own Supabase project goes here. The project connected to Claude on Aaron's desktop belongs to
another business: never point SUPABASE_URL at it.
"""
from __future__ import annotations

import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from . import http


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def clean_url(url: str) -> str:
    """The project URL as Supabase shows it, forgiving common paste slips ("https:https://...", "/rest/v1", spaces)."""
    url = url.strip().strip('"').rstrip("/")
    i = url.rfind("https://")
    url = url[i:] if i > 0 else url
    for tail in ("/rest/v1", "/storage/v1"):
        if url.endswith(tail):
            url = url[: -len(tail)]
    return url


class Store:
    def __init__(self, url: str, key: str, bucket: str = "media", session=None):
        if not url or not key:
            raise RuntimeError("SUPABASE_URL / SUPABASE_KEY not set; see SETUP.md")
        self.url = clean_url(url)
        self.bucket = bucket
        self.session = session
        # New-style keys (sb_secret_...) go in apikey only; legacy JWT keys also need the Bearer header.
        self.headers = {"apikey": key}
        if not key.startswith("sb_"):
            self.headers["Authorization"] = f"Bearer {key}"

    def _req(self, method: str, path: str, **kw):
        headers = {**self.headers, **kw.pop("headers", {})}
        return http.request(method, f"{self.url}{path}", session=self.session, headers=headers, **kw)

    # -- posts -----------------------------------------------------------------------------------------------
    def posts(self, **filters) -> list[dict]:
        """GET /posts with PostgREST filters, e.g. account="eq.ur_dailydog", status="eq.scheduled"."""
        params = {"select": "*", "order": "post_at.asc.nullslast,id.asc", **filters}
        return self._req("GET", "/rest/v1/posts", params=params).json()

    def due(self, now: datetime) -> list[dict]:
        return self.posts(status="in.(scheduled,publishing)", post_at=f"lte.{iso(now)}")

    def taken(self, account: str, since: datetime) -> list[dict]:
        """Posts that hold a slot from `since` on: scheduled, being published or already out."""
        return self.posts(account=f"eq.{account}", status="in.(scheduled,publishing,posted)",
                          post_at=f"gte.{iso(since)}")

    def reserve(self, account: str, kind: str) -> list[dict]:
        return self.posts(account=f"eq.{account}", status="eq.reserve", kind=f"eq.{kind}",
                          order="created_at.asc,id.asc")

    def used_refs(self, account: str) -> set[str]:
        """source_ref of every post the account ever queued (stock clips are never used twice)."""
        rows = self.posts(account=f"eq.{account}", source_ref="not.is.null", select="source_ref", order="id.asc")
        return {r["source_ref"] for r in rows}

    def add_post(self, row: dict) -> dict:
        r = self._req("POST", "/rest/v1/posts", json=row, headers={"Prefer": "return=representation"})
        return r.json()[0]

    def update_post(self, post_id: int, **fields) -> None:
        self._req("PATCH", "/rest/v1/posts", params={"id": f"eq.{post_id}"}, json=fields)

    def log(self, post_id: int | None, event: str, detail: dict | None = None) -> None:
        self._req("POST", "/rest/v1/post_log",
                  json={"post_id": post_id, "event": event, "detail": detail or {}})

    # -- media -----------------------------------------------------------------------------------------------
    def public_url(self, path: str) -> str:
        return f"{self.url}/storage/v1/object/public/{self.bucket}/{quote(path)}"

    def upload(self, local: Path, path: str) -> str:
        ctype = mimetypes.guess_type(str(local))[0] or "application/octet-stream"
        self._req("POST", f"/storage/v1/object/{self.bucket}/{quote(path)}", data=Path(local).read_bytes(),
                  headers={"Content-Type": ctype, "x-upsert": "true"}, timeout=300)
        return self.public_url(path)

    def delete_media(self, paths: list[str]) -> None:
        if paths:
            self._req("DELETE", f"/storage/v1/object/{self.bucket}", json={"prefixes": paths})
