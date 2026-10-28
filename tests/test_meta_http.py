import pytest

from social_studio import http
from social_studio.meta import Meta, MetaError


class Resp:
    def __init__(self, status, body):
        self.status_code = status
        self._body = body
        self.text = str(body)

    def json(self):
        return self._body


class Session:
    def __init__(self, *replies):
        self.replies = list(replies)
        self.sent = []

    def request(self, method, url, **kw):
        self.sent.append((method, url, kw))
        return self.replies.pop(0)


def meta(*replies):
    s = Session(*replies)
    return Meta("TOKEN123", session=s, sleep=lambda x: None), s


def test_reel_container_params_and_token_not_in_url():
    m, s = meta(Resp(200, {"id": "c1"}))
    assert m.container("1784", kind="reel", url="https://x/a.mp4", caption="hi", collaborators=["bob"],
                       extra={"is_ai_generated": "true"}) == "c1"
    method, url, kw = s.sent[0]
    assert method == "POST" and url.endswith("/1784/media") and "TOKEN123" not in url
    d = kw["data"]
    assert d["media_type"] == "REELS" and d["video_url"] == "https://x/a.mp4" and d["share_to_feed"] == "true"
    assert d["collaborators"] == '["bob"]' and d["is_ai_generated"] == "true" and d["caption"] == "hi"


def test_story_has_no_caption_and_carousel_item_flags():
    m, s = meta(Resp(200, {"id": "c1"}), Resp(200, {"id": "c2"}))
    m.container("1", kind="story", url="https://x/a.jpg", caption="nope")
    m.container("1", kind="image", url="https://x/b.jpg", carousel_item=True, caption="nope")
    assert "caption" not in s.sent[0][2]["data"] and s.sent[0][2]["data"]["image_url"]
    assert s.sent[1][2]["data"]["is_carousel_item"] == "true" and "caption" not in s.sent[1][2]["data"]


def test_retries_5xx_then_succeeds():
    m, s = meta(Resp(500, {}), Resp(200, {"id": "m1"}))
    assert m.publish("1", "c1") == "m1" and len(s.sent) == 2


def test_permanent_error_raises_without_token():
    m, s = meta(Resp(400, {"error": {"message": "bad access_token=TOKEN123", "code": 100}}))
    with pytest.raises(http.HttpError) as e:
        m.publish("1", "c1")
    assert "TOKEN123" not in str(e.value) and len(s.sent) == 1


def test_wait_ready_states():
    m, _ = meta(Resp(200, {"status_code": "IN_PROGRESS"}), Resp(200, {"status_code": "FINISHED"}))
    assert m.wait_ready("c1", max_seconds=60) is True
    m, _ = meta(Resp(200, {"status_code": "ERROR"}))
    with pytest.raises(MetaError):
        m.wait_ready("c1")
    m, _ = meta(Resp(200, {"status_code": "IN_PROGRESS"}))
    assert m.wait_ready("c1", max_seconds=0) is False


def test_facebook_reel_flow():
    m, s = meta(Resp(200, {"access_token": "PAGETOK"}), Resp(200, {"video_id": "v1"}), Resp(200, {}),
                Resp(200, {"success": True}))
    assert m.facebook_reel("1000", "https://x/a.mp4", "hi") == "v1"
    upload = s.sent[2]
    assert "rupload.facebook.com" in upload[1] and upload[2]["headers"]["file_url"] == "https://x/a.mp4"
    assert s.sent[3][2]["data"]["upload_phase"] == "finish" and s.sent[3][2]["data"]["access_token"] == "PAGETOK"


def test_no_token_refuses():
    with pytest.raises(MetaError):
        Meta("")
