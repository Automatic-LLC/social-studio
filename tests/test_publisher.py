from datetime import timedelta

from social_studio.meta import MetaError
from social_studio.publisher import Publisher


def make(settings, store, meta):
    alerts = []
    p = Publisher(settings, store, {"ur_dailydog": meta}, lambda *a, **k: alerts.append(a))
    return p, alerts


def iso(dt):
    return dt.isoformat()


def test_posts_a_due_reel_to_instagram_and_facebook(settings, store, meta, now):
    post = store.add(post_at=iso(now - timedelta(minutes=5)))
    pub, alerts = make(settings, store, meta)
    assert pub.run(now)["posted"] == 1
    row = store.rows[post["id"]]
    assert row["status"] == "posted" and row["ig_media_id"] == "m-c1" and row["fb_video_id"] == "fb1"
    assert ("container", {"kind": "reel", "url": "https://store.test/media/ur_dailydog/x.mp4", "caption": "hi",
                          "collaborators": None, "extra": None}) in meta.calls
    assert store.deleted == ["ur_dailydog/x.mp4"] and alerts == []


def test_future_posts_wait(settings, store, meta, now):
    store.add(post_at=iso(now + timedelta(hours=1)))
    pub, _ = make(settings, store, meta)
    assert pub.run(now)["posted"] == 0 and meta.calls == []


def test_kill_switch(settings, store, meta, now):
    settings.paused = True
    store.add(post_at=iso(now))
    pub, _ = make(settings, store, meta)
    pub.run(now)
    assert meta.calls == []


def test_disabled_or_unset_account_never_posts(settings, store, meta, now):
    store.add(post_at=iso(now))
    settings.accounts["ur_dailydog"].enabled = False
    pub, _ = make(settings, store, meta)
    pub.run(now)
    settings.accounts["ur_dailydog"].enabled = True
    settings.accounts["ur_dailydog"].ig_user_id = ""
    pub.run(now)
    assert meta.calls == []


def test_gate_blocks_unchecked_posts(settings, store, meta, now):
    post = store.add(post_at=iso(now), qa_passed=False)
    pub, alerts = make(settings, store, meta)
    pub.run(now)
    assert store.rows[post["id"]]["status"] == "failed" and meta.calls == [] and alerts


def test_ai_posts_carry_the_label(settings, store, meta, now):
    store.add(post_at=iso(now), is_ai=True)
    pub, _ = make(settings, store, meta)
    pub.run(now)
    assert meta.calls[0][1]["extra"] == {settings.ai_label_param: "true"}


def test_late_post_is_skipped(settings, store, meta, now):
    post = store.add(post_at=iso(now - timedelta(hours=7)))
    pub, alerts = make(settings, store, meta)
    pub.run(now)
    assert store.rows[post["id"]]["status"] == "skipped" and meta.calls == [] and alerts


def test_processing_video_resumes_next_run(settings, store, meta, now):
    post = store.add(post_at=iso(now))
    meta.status = "IN_PROGRESS"
    pub, _ = make(settings, store, meta)
    assert pub.run(now)["waiting"] == 1
    assert store.rows[post["id"]]["status"] == "publishing" and store.rows[post["id"]]["ig_container"] == "c1"
    meta.status = "FINISHED"
    assert pub.run(now + timedelta(minutes=15))["posted"] == 1
    assert sum(c[0] == "container" for c in meta.calls) == 1  # reused, not rebuilt


def test_already_published_container_is_not_posted_twice(settings, store, meta, now):
    post = store.add(post_at=iso(now), status="publishing", ig_container="c9")
    meta.status = "PUBLISHED"
    pub, _ = make(settings, store, meta)
    pub.run(now)
    assert store.rows[post["id"]]["status"] == "posted"
    assert not any(c[0] == "publish" for c in meta.calls)


def test_failures_retry_then_fail_with_alert(settings, store, meta, now):
    post = store.add(post_at=iso(now))
    meta.fail_publish = MetaError("boom access_token=SECRET123")
    pub, alerts = make(settings, store, meta)
    for i in range(3):
        pub.run(now + timedelta(minutes=15 * i))
    row = store.rows[post["id"]]
    assert row["status"] == "failed" and row["attempts"] == 3
    assert "SECRET123" not in row["last_error"] and "SECRET123" not in str(alerts)


def test_facebook_failure_keeps_instagram_post(settings, store, meta, now):
    post = store.add(post_at=iso(now))
    meta.fail_fb = MetaError("fb down")
    pub, alerts = make(settings, store, meta)
    pub.run(now)
    row = store.rows[post["id"]]
    assert row["status"] == "posted" and "fb down" in row["fb_error"] and alerts


def test_carousel_builds_children(settings, store, meta, now):
    store.add(post_at=iso(now), kind="carousel", media=[{"path": "a.jpg"}, {"path": "b.jpg"}])
    pub, _ = make(settings, store, meta)
    pub.run(now)
    kinds = [c[1].get("kind") for c in meta.calls if c[0] == "container"]
    assert kinds == ["image", "image", "carousel"] and not any(c[0] == "fb" for c in meta.calls)


def test_reserve_fills_a_killed_slot(settings, store, meta, now):
    # 18:00 Chicago on Nov 3 = 00:00 UTC Nov 4
    slot = now.replace(day=4, hour=0)
    killed = store.add(post_at=iso(slot), status="killed")
    spare = store.add(status="reserve")
    pub, _ = make(settings, store, meta)
    pub.fill_from_reserve(settings.accounts["ur_dailydog"], now)
    assert store.rows[spare["id"]]["status"] == "scheduled"
    assert store.rows[killed["id"]]["status"] == "killed"
    # A day that already has its reel keeps it; the reserve is not used twice for one day.
    days = {store.rows[r]["post_at"][:10] for r in store.rows if store.rows[r]["status"] == "scheduled"}
    assert len(days) == 1


def test_queue_alarm(settings, store, meta, now):
    store.add(post_at=iso(now + timedelta(days=5)))
    pub, alerts = make(settings, store, meta)
    assert pub.check_queue(now)["ur_dailydog"] == 5.0
    assert any("Queue low" in a[0] for a in alerts) and any("Reserve low" in a[0] for a in alerts)
