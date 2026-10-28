"""Meta Graph API: Instagram publishing (image, carousel, Reel, Story) and Facebook Page Reels.

Every Meta call lives in this file, so an API change is fixed in one place. The token goes in the request
body or a header, never in a URL, and errors are scrubbed before anyone logs them (http.scrub).
"""
from __future__ import annotations

import json
import time

from . import http

READY = "FINISHED"
DEAD = {"ERROR", "EXPIRED"}


class MetaError(Exception):
    pass


class Meta:
    def __init__(self, token: str, version: str = "v24.0", session=None, sleep=time.sleep):
        if not token:
            raise MetaError("no Meta token set (META_TOKEN); see SETUP.md")
        self.token = token
        self.version = version
        self.base = f"https://graph.facebook.com/{version}"
        self.session = session
        self.sleep = sleep

    # -- low level -------------------------------------------------------------------------------------------
    def _get(self, path: str, token: str | None = None, **params) -> dict:
        r = http.request("GET", f"{self.base}/{path}", session=self.session, sleep=self.sleep,
                         params=params, headers={"Authorization": f"Bearer {token or self.token}"})
        return r.json()

    def _post(self, path: str, token: str | None = None, **data) -> dict:
        data = {k: v for k, v in data.items() if v is not None}
        data["access_token"] = token or self.token
        r = http.request("POST", f"{self.base}/{path}", session=self.session, sleep=self.sleep, data=data)
        return r.json()

    # -- account checks --------------------------------------------------------------------------------------
    def whoami(self) -> dict:
        return self._get("me", fields="id,name")

    def pages(self) -> list[dict]:
        """Pages this token can manage, each with its linked Instagram account (id, username) when there is one."""
        out = self._get("me/accounts", fields="id,name,instagram_business_account{id,username}")
        return out.get("data", [])

    def publishing_limit(self, ig_user_id: str) -> dict:
        out = self._get(f"{ig_user_id}/content_publishing_limit", fields="quota_usage,config")
        return (out.get("data") or [{}])[0]

    # -- reading our own account -----------------------------------------------------------------------------
    def profile(self, ig_user_id: str) -> dict:
        return self._get(ig_user_id, fields="username,name,biography,website,followers_count,follows_count,"
                                            "media_count")

    def media(self, ig_user_id: str, limit: int = 50) -> list[dict]:
        """Our latest posts, newest first (follows paging until `limit`)."""
        fields = "id,caption,media_type,media_product_type,timestamp,permalink,like_count,comments_count"
        out = self._get(f"{ig_user_id}/media", fields=fields, limit=min(limit, 50))
        items = list(out.get("data", []))
        after = (out.get("paging") or {}).get("cursors", {}).get("after")
        while after and len(items) < limit and (out.get("paging") or {}).get("next"):
            out = self._get(f"{ig_user_id}/media", fields=fields, limit=min(limit - len(items), 50), after=after)
            items += out.get("data", [])
            after = (out.get("paging") or {}).get("cursors", {}).get("after")
        return items[:limit]

    def media_insights(self, media_id: str, metrics=("views", "reach", "saved", "shares", "total_interactions")) -> dict:
        """{metric: value} for one post; metrics Meta refuses for that post type are left out."""
        try:
            out = self._get(f"{media_id}/insights", metric=",".join(metrics))
        except http.HttpError:
            if len(metrics) == 1:
                return {}
            got: dict = {}
            for m in metrics:  # one at a time, so one unsupported metric doesn't hide the rest
                got.update(self.media_insights(media_id, (m,)))
            return got
        return {d["name"]: (d.get("values") or [{}])[0].get("value", d.get("total_value", {}).get("value"))
                for d in out.get("data", [])}

    # -- Instagram -------------------------------------------------------------------------------------------
    def container(self, ig_user_id: str, *, kind: str, url: str | None = None, caption: str | None = None,
                  children: list[str] | None = None, carousel_item: bool = False,
                  collaborators: list[str] | None = None, extra: dict | None = None) -> str:
        """Create a media container and return its id. kind: image, video (carousel slide only), reel, story,
        carousel."""
        p: dict = {}
        is_video = url is not None and url.lower().split("?")[0].endswith((".mp4", ".mov"))
        if kind == "reel":
            p.update(media_type="REELS", video_url=url, share_to_feed="true")
        elif kind == "story":
            p.update(media_type="STORIES", **({"video_url": url} if is_video else {"image_url": url}))
        elif kind == "carousel":
            p.update(media_type="CAROUSEL", children=",".join(children or []))
        elif kind in ("image", "video"):
            if is_video:
                p.update(media_type="VIDEO", video_url=url)
            else:
                p.update(image_url=url)
        else:
            raise MetaError(f"unknown kind {kind!r}")
        if carousel_item:
            p["is_carousel_item"] = "true"
        else:
            if caption is not None and kind != "story":
                p["caption"] = caption
            if collaborators and kind != "story":
                p["collaborators"] = json.dumps(collaborators[:3])
        for k, v in (extra or {}).items():
            p[k] = v
        out = self._post(f"{ig_user_id}/media", **p)
        if "id" not in out:
            raise MetaError(f"no container id in reply: {http.scrub(out)}")
        return out["id"]

    def container_status(self, container_id: str) -> str:
        return self._get(container_id, fields="status_code").get("status_code", "")

    def wait_ready(self, container_id: str, max_seconds: float = 300, every: float = 10) -> bool:
        """True once Meta has processed the container; False if still working after max_seconds (try next run)."""
        waited = 0.0
        while True:
            status = self.container_status(container_id)
            if status == READY:
                return True
            if status in DEAD:
                raise MetaError(f"container {container_id} is {status}")
            if waited >= max_seconds:
                return False
            self.sleep(every)
            waited += every

    def publish(self, ig_user_id: str, container_id: str) -> str:
        out = self._post(f"{ig_user_id}/media_publish", creation_id=container_id)
        if "id" not in out:
            raise MetaError(f"no media id in reply: {http.scrub(out)}")
        return out["id"]

    def permalink(self, media_id: str) -> str:
        try:
            return self._get(media_id, fields="permalink").get("permalink", "")
        except http.HttpError:
            return ""

    # -- Facebook Page Reels ---------------------------------------------------------------------------------
    def page_token(self, page_id: str) -> str:
        tok = self._get(page_id, fields="access_token").get("access_token", "")
        if not tok:
            raise MetaError(f"no Page token for page {page_id}: is the Page assigned to the system user?")
        return tok

    def facebook_reel(self, page_id: str, video_url: str, description: str) -> str:
        """Upload a hosted video as a Facebook Reel on the Page (start, upload by URL, finish). Returns video id."""
        ptok = self.page_token(page_id)
        start = self._post(f"{page_id}/video_reels", token=ptok, upload_phase="start")
        video_id = start.get("video_id")
        if not video_id:
            raise MetaError(f"Facebook Reel start gave no video id: {http.scrub(start)}")
        http.request("POST", f"https://rupload.facebook.com/video-upload/{self.version}/{video_id}",
                     session=self.session, sleep=self.sleep,
                     headers={"Authorization": f"OAuth {ptok}", "file_url": video_url})
        done = self._post(f"{page_id}/video_reels", token=ptok, upload_phase="finish", video_id=video_id,
                          video_state="PUBLISHED", description=description)
        if not done.get("success", True):
            raise MetaError(f"Facebook Reel finish failed: {http.scrub(done)}")
        return video_id
