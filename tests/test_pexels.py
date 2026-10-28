import pytest

from social_studio.sources import pexels


class Resp:
    def __init__(self, status=200, body=None, chunks=()):
        self.status_code = status
        self._body = body or {}
        self.text = str(body)
        self.chunks = chunks

    def json(self):
        return self._body

    def iter_content(self, chunk_size=1):
        yield from self.chunks

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class Session:
    def __init__(self, *replies):
        self.replies = list(replies)
        self.sent = []

    def request(self, method, url, **kw):
        self.sent.append((method, url, kw))
        return self.replies.pop(0)


def f(id, w, h, link=None, type="video/mp4"):
    return {"id": id, "quality": "hd", "file_type": type, "width": w, "height": h,
            "link": link or f"https://v/{id}.mp4"}


def video(id, duration, files, user="Jane Doe"):
    return {"id": id, "width": 1080, "height": 1920, "url": f"https://pexels.com/video/{id}/", "duration": duration,
            "user": {"name": user, "url": f"https://pexels.com/@{id}"}, "video_files": files}


def test_search_params_header_and_file_choice():
    s = Session(Resp(body={"videos": [video(1, 10, [f(11, 720, 1280), f(12, 2160, 3840), f(13, 1080, 1920),
                                                    f(14, 1080, 1920, type="video/webm")])]}))
    items = pexels.search("dog walk", "KEY", session=s)
    method, url, kw = s.sent[0]
    assert method == "GET" and url == "https://api.pexels.com/videos/search"
    assert kw["headers"] == {"Authorization": "KEY"}
    assert kw["params"] == {"query": "dog walk", "orientation": "portrait", "size": "medium", "per_page": 15}
    assert items == [{"id": 1, "page_url": "https://pexels.com/video/1/", "user": "Jane Doe",
                      "user_url": "https://pexels.com/@1", "duration": 10, "link": "https://v/13.mp4",
                      "width": 1080, "height": 1920}]


def test_search_picks_largest_when_nothing_reaches_1920():
    s = Session(Resp(body={"videos": [video(1, 10, [f(11, 540, 960), f(12, 720, 1280), f(13, 1080, 1920, type="x")])]}))
    assert pexels.search("x", "KEY", session=s)[0]["link"] == "https://v/12.mp4"


def test_search_filters_duration_and_files():
    vids = [video(1, 2, [f(11, 1080, 1920)]), video(2, 61, [f(21, 1080, 1920)]), video(3, 3, [f(31, 1080, 1920)]),
            video(4, 60, [f(41, 1080, 1920)]), video(5, 20, [f(51, 1080, 1920, type="video/webm")]), video(6, 20, [])]
    s = Session(Resp(body={"videos": vids}))
    assert [i["id"] for i in pexels.search("x", "KEY", session=s)] == [3, 4]


def test_search_needs_key():
    with pytest.raises(ValueError):
        pexels.search("x", "")


def test_download_streams_and_skips_existing(tmp_path):
    item = {"id": 7, "link": "https://v/7.mp4"}
    s = Session(Resp(chunks=[b"ab", b"", b"cd"]))
    p = pexels.download(item, tmp_path / "dl", session=s)
    assert p == tmp_path / "dl" / "pexels_7.mp4" and p.read_bytes() == b"abcd"
    assert s.sent[0][2]["stream"] is True and not list((tmp_path / "dl").glob("*.part"))
    assert pexels.download(item, tmp_path / "dl", session=s) == p and len(s.sent) == 1


def test_download_failure_leaves_nothing(tmp_path):
    s = Session(Resp(404, {"message": "gone"}))
    with pytest.raises(Exception):
        pexels.download({"id": 8, "link": "https://v/8.mp4"}, tmp_path, session=s)
    assert list(tmp_path.iterdir()) == []


def test_credit():
    assert pexels.credit({"user": "Jane Doe"}) == "Video by Jane Doe on Pexels"
