from social_studio.insights import report

from test_meta_http import Resp, meta


def test_report():
    posts = [
        {"id": "1", "media_type": "VIDEO", "media_product_type": "REELS", "timestamp": "2026-10-20T23:00:00+0000",
         "caption": "Corgi zoomies 😂 #corgi", "permalink": "https://ig/p/1", "like_count": 40, "views": 5000,
         "reach": 3000, "shares": 12, "saved": 4},
        {"id": "2", "media_type": "CAROUSEL_ALBUM", "timestamp": "2026-10-21T17:00:00+0000", "caption": "Types of dogs",
         "permalink": "https://ig/p/2", "like_count": 30, "reach": 900},
    ]
    text = report({"username": "ur_dailydog", "followers_count": 3012, "biography": "Daily dogs\nComedy"}, posts)
    assert "Followers 3012" in text and "Daily dogs / Comedy" in text
    assert "| Reel | 1 | 5000 |" in text and "| Carousel | 1 | - | 900 |" in text
    assert text.index("**5000**") < text.index("**900**")
    assert "Tue 18:00" in text  # 23:00 UTC Tue Oct 20 = 6 pm Central


def test_insights_skip_unsupported_metric():
    m, s = meta(Resp(400, {"error": {"message": "bad metric", "code": 100}}),
                Resp(200, {"data": [{"name": "views", "values": [{"value": 10}]}]}),
                Resp(400, {"error": {"message": "bad metric", "code": 100}}))
    assert m.media_insights("1", ("views", "shares")) == {"views": 10}
