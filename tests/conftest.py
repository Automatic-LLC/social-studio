"""Fakes for Supabase and Meta, so no test ever touches a real account."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from social_studio import config  # noqa: E402
from social_studio.publisher import _when  # noqa: E402


class FakeStore:
    def __init__(self):
        self.rows: dict[int, dict] = {}
        self.logs: list[tuple] = []
        self.deleted: list[str] = []
        self.next_id = 1

    def add(self, **row) -> dict:
        base = dict(account="ur_dailydog", kind="reel", status="scheduled", post_at=None, caption="hi",
                    media=[{"path": "ur_dailydog/x.mp4"}], is_ai=False, qa_passed=True, caption_ok=True,
                    collaborators=[], to_facebook=True, attempts=0, ig_container=None,
                    created_at=f"2026-10-01T00:00:{self.next_id:02d}Z")
        base.update(row)
        base["id"] = self.next_id
        self.rows[self.next_id] = base
        self.next_id += 1
        return base

    def due(self, now):
        return sorted((r for r in self.rows.values() if r["status"] in ("scheduled", "publishing")
                       and r["post_at"] and _when(r["post_at"]) <= now), key=lambda r: r["post_at"])

    def taken(self, account, since):
        return [r for r in self.rows.values() if r["account"] == account and r["post_at"]
                and r["status"] in ("scheduled", "publishing", "posted") and _when(r["post_at"]) >= since]

    def reserve(self, account, kind):
        return sorted((r for r in self.rows.values() if r["account"] == account and r["status"] == "reserve"
                       and r["kind"] == kind), key=lambda r: r["created_at"])

    def posts(self, account=None, batch_id=None, **_):
        return [r for r in self.rows.values() if (account is None or f"eq.{r['account']}" == account)
                and (batch_id is None or f"eq.{r.get('batch_id')}" == batch_id)]

    def posted_with_media(self, account, before, after):
        return [r for r in self.rows.values() if r["account"] == account and r["status"] == "posted"
                and r.get("media") and after <= _when(r["posted_at"]) < before]

    def used_refs(self, account):
        return {r["source_ref"] for r in self.rows.values() if r["account"] == account and r.get("source_ref")}

    def upload(self, local, path):
        self.uploaded = getattr(self, "uploaded", []) + [path]
        return self.public_url(path)

    def add_post(self, row):
        return self.add(**row)

    def update_post(self, post_id, **fields):
        self.rows[post_id].update(fields)

    def log(self, post_id, event, detail=None):
        self.logs.append((post_id, event, detail or {}))

    def public_url(self, path):
        return f"https://store.test/media/{path}"

    def delete_media(self, paths):
        self.deleted += paths


class FakeMeta:
    def __init__(self):
        self.calls: list[tuple] = []
        self.status = "FINISHED"
        self.fail_publish = None
        self.fail_fb = None
        self.n = 0

    def container(self, ig, **kw):
        self.n += 1
        self.calls.append(("container", kw))
        return f"c{self.n}"

    def container_status(self, c):
        return self.status

    def wait_ready(self, c, max_seconds=300, every=10):
        return self.status == "FINISHED"

    def publish(self, ig, c):
        if self.fail_publish:
            raise self.fail_publish
        self.calls.append(("publish", c))
        return f"m-{c}"

    def permalink(self, mid):
        return f"https://instagram.test/p/{mid}"

    def facebook_reel(self, page, url, desc):
        if self.fail_fb:
            raise self.fail_fb
        self.calls.append(("fb", url))
        return "fb1"


@pytest.fixture
def settings():
    s = config.load()
    a = s.accounts["ur_dailydog"]
    a.ig_user_id, a.fb_page_id = "1784", "1000"
    s.paused = False
    return s


@pytest.fixture
def store():
    return FakeStore()


@pytest.fixture
def meta():
    return FakeMeta()


@pytest.fixture
def now():
    return datetime(2026, 11, 2, 18, 0, tzinfo=timezone.utc)
