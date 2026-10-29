from datetime import timedelta

import pytest

from social_studio import http
from social_studio.make import MakeError, MakeHook
from social_studio.publisher import Publisher

from test_meta_http import Resp, Session


class FakeHook:
    def __init__(self, reply=None, error=None):
        self.sent, self.reply, self.error = [], reply or {}, error

    def post(self, payload):
        self.sent.append(payload)
        if self.error:
            raise self.error
        return self.reply


def make_pub(settings, store, hook):
    settings.accounts["ur_dailydog"].publish_via = "make"
    settings.accounts["ur_dailydog"].ig_user_id = ""  # Make needs no Meta ids
    alerts = []
    return Publisher(settings, store, {}, lambda *a, **k: alerts.append(a), hooks={"ur_dailydog": hook}), alerts


def test_due_post_goes_to_make(settings, store, now):
    post = store.add(post_at=now.isoformat(), is_ai=True)
    hook = FakeHook({"id": "1789"})
    pub, alerts = make_pub(settings, store, hook)
    assert pub.run(now)["posted"] == 1
    sent = hook.sent[0]
    assert sent["kind"] == "reel" and sent["media_url"] == "https://store.test/media/ur_dailydog/x.mp4"
    assert sent["is_ai"] is True and sent["sample"] is False and sent["caption"] == "hi"
    row = store.rows[post["id"]]
    assert row["status"] == "posted" and row["ig_media_id"] == "1789" and store.deleted == [] and not alerts


def test_make_gates_still_apply(settings, store, now):
    store.add(post_at=now.isoformat(), qa_passed=False)
    hook = FakeHook()
    pub, _ = make_pub(settings, store, hook)
    pub.run(now)
    assert hook.sent == []
    settings.paused = True
    store.add(post_at=now.isoformat())
    pub.run(now)
    assert hook.sent == []


def test_make_error_retries_then_fails(settings, store, now):
    post = store.add(post_at=now.isoformat())
    pub, alerts = make_pub(settings, store, FakeHook(error=http.HttpError(400, "Scenario failed")))
    for i in range(3):
        pub.run(now + timedelta(minutes=15 * i))
    row = store.rows[post["id"]]
    assert row["status"] == "failed" and row["attempts"] == 3 and alerts


def test_no_answer_is_never_retried(settings, store, now):
    post = store.add(post_at=now.isoformat())
    hook = FakeHook(error=http.HttpError(0, "ReadTimeout"))
    pub, alerts = make_pub(settings, store, hook)
    pub.run(now)
    pub.run(now + timedelta(minutes=15))
    assert len(hook.sent) == 1 and store.rows[post["id"]]["status"] == "failed"
    assert any("Check Instagram" in a[0] for a in alerts)


def test_media_cleaned_up_two_days_later(settings, store, now):
    old = store.add(status="posted", posted_at=(now - timedelta(hours=50)).isoformat(), media=[{"path": "a.mp4"}])
    new = store.add(status="posted", posted_at=(now - timedelta(hours=2)).isoformat(), media=[{"path": "b.mp4"}])
    pub, _ = make_pub(settings, store, FakeHook())
    pub.run(now)
    assert store.deleted == ["a.mp4"] and store.rows[old["id"]]["media"] == [] and store.rows[new["id"]]["media"]


def test_hook_client():
    s = Session(Resp(200, {"id": "9"}))
    assert MakeHook("https://hook.make.com/abc", session=s).post({"a": 1}) == {"id": "9"}
    assert s.sent[0][2]["json"] == {"a": 1}

    class Accepted(Resp):
        def json(self):
            raise ValueError

    assert MakeHook("https://hook.make.com/abc", session=Session(Accepted(200, "Accepted"))).post({}) == {}
    s = Session(Resp(500, {}), Resp(200, {}))
    with pytest.raises(http.HttpError):
        MakeHook("https://hook.make.com/abc", session=s).post({})
    assert len(s.sent) == 1  # one try only: a retry could post twice
    with pytest.raises(MakeError):
        MakeHook("")
