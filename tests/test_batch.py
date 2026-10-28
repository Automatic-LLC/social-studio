from datetime import timedelta
from pathlib import Path

import pytest
import yaml

from social_studio.batch import Batch, PlanError, check_plan

GOOD = "Corgi zoomies at 6am, every single day 😂 Does yours do this?"


def write_plan(tmp_path, items):
    (tmp_path / "clips").mkdir(exist_ok=True)
    (tmp_path / "clips" / "a.mp4").write_bytes(b"x")
    p = tmp_path / "week1.yaml"
    p.write_text(yaml.safe_dump({"account": "ur_dailydog", "items": items}, allow_unicode=True), encoding="utf-8")
    return p


def fakes():
    renders = []

    def render(spec, handle, font=None):
        renders.append(spec)
        Path(spec.out).write_bytes(b"mp4")
        return spec.out

    def search(query, key):
        return [{"id": 1, "user": "Ann"}, {"id": 2, "user": "Bo"}]

    def download(hit, dest):
        Path(dest).mkdir(parents=True, exist_ok=True)
        f = Path(dest) / f"pexels_{hit['id']}.mp4"
        f.write_bytes(b"x")
        return f

    return renders, dict(render=render, search=search, download=download)


def test_plan_problems_are_all_listed(settings, tmp_path):
    acct = settings.accounts["ur_dailydog"]
    plan = {"items": [{"clip": "missing.mp4", "caption": "pawsome"}, {"caption": GOOD},
                      {"clip": "clips/a.mp4", "caption": GOOD, "source": "submission"}]}
    write_plan(tmp_path, [])
    probs = check_plan(plan, acct, tmp_path)
    assert any("item 1: no file" in p for p in probs) and any("item 1: caption banned" in p for p in probs)
    assert any("item 2: give exactly one" in p for p in probs) and any("item 3: a submission" in p for p in probs)


def test_preview_then_go(settings, store, now, tmp_path):
    acct = settings.accounts["ur_dailydog"]
    plan = write_plan(tmp_path, [
        {"clip": "clips/a.mp4", "text": "POV: walk", "caption": GOOD, "hashtags": "zoomies"},
        {"pexels": "golden retriever", "caption": GOOD, "hashtags": "general"},
        {"clip": "clips/a.mp4", "caption": GOOD, "hashtags": "general", "reserve": True, "start": 1},
    ])
    store.add(post_at=(now + timedelta(days=1)).isoformat(), source_ref="pexels:1")  # clip 1 already used
    renders, fx = fakes()
    b = Batch(settings, store, acct, plan, tmp_path / "out", pexels_key="k", **fx)
    entries = b.build()
    sched = b.schedule(entries, now)
    page = b.preview(sched)
    assert page.is_file() and "golden" not in page.read_text() and "Video by Bo on Pexels" in page.read_text()
    assert entries[1]["source_ref"] == "pexels:2" and renders[1].credit == "Video: Bo / Pexels"
    assert [at is None for _, at in sched] == [False, False, True]
    # The existing post holds Nov 3 (account time), so the batch takes Nov 2 and Nov 4.
    from zoneinfo import ZoneInfo
    days = [at.astimezone(ZoneInfo(acct.timezone)).day for _, at in sched if at]
    assert days == [2, 4]

    # --go: renders are cached, posts are queued with the human check passed.
    b2 = Batch(settings, store, acct, plan, tmp_path / "out", pexels_key="k", **fx)
    rows = b2.go(b2.schedule(b2.build(), now))
    assert len(renders) == 3
    assert [r["status"] for r in rows] == ["scheduled", "scheduled", "reserve"]
    assert all(r["qa_passed"] and r["caption_ok"] for r in rows) and rows[1]["source_ref"] == "pexels:2"
    assert rows[1]["caption"].endswith("Video by Bo on Pexels")


def test_pexels_needs_key(settings, store, tmp_path):
    plan = write_plan(tmp_path, [{"pexels": "dog", "caption": GOOD}])
    _, fx = fakes()
    with pytest.raises(PlanError):
        Batch(settings, store, settings.accounts["ur_dailydog"], plan, tmp_path / "out", **fx).build()


def test_wrong_account(settings, store, tmp_path):
    p = tmp_path / "x.yaml"
    p.write_text("account: someone_else\nitems: []\n")
    with pytest.raises(PlanError):
        Batch(settings, store, settings.accounts["ur_dailydog"], p, tmp_path)
