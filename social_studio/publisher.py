"""The publisher: runs every 15 minutes on GitHub Actions and posts whatever is due.

Rules it never breaks:
- nothing posts while config.yaml `paused` is true, or for an account with `enabled: false`;
- nothing posts unless the post passed the quality check (qa_passed) and the caption rules (caption_ok);
- a post with is_ai set carries Meta's AI label;
- a post far too late (late_limit_hours) is skipped, not posted at a strange hour;
- a post that keeps failing is marked failed after max_attempts and an alert goes to the phone.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from . import http
from .meta import Meta, MetaError

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _when(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


class Publisher:
    def __init__(self, settings, store, metas: dict[str, Meta], alert=lambda *a, **k: None):
        self.s = settings
        self.store = store
        self.metas = metas
        self.alert = alert

    # -- one run -----------------------------------------------------------------------------------------------
    def run(self, now: datetime | None = None) -> dict:
        now = now or datetime.now(timezone.utc)
        out = {"posted": 0, "waiting": 0, "failed": 0, "skipped": 0, "filled": 0}
        if self.s.paused:
            print("paused (config.yaml): nothing posts")
            return out
        for acct in self.s.accounts.values():
            if acct.enabled and acct.ig_user_id:
                out["filled"] += self.fill_from_reserve(acct, now)
        for post in self.store.due(now):
            result = self.publish(post, now)
            out[result] = out.get(result, 0) + 1
        return out

    def publish(self, post: dict, now: datetime) -> str:
        acct = self.s.accounts.get(post["account"])
        pid = post["id"]
        if acct is None or not acct.enabled or not acct.ig_user_id or post["account"] not in self.metas:
            return "skipped"  # account off or not set up: leave the post alone
        late = now - _when(post["post_at"])
        if post["status"] == "scheduled" and late > timedelta(hours=self.s.pub("late_limit_hours", 6)):
            self._finish(post, "skipped", last_error=f"{late} late; skipped")
            self.alert(f"Skipped a late post ({acct.handle})", f"Post {pid} was {late} late, so it did not go out.")
            return "skipped"
        if not post.get("qa_passed") or not post.get("caption_ok"):
            self._finish(post, "failed", last_error="did not pass the quality or caption check")
            self.alert(f"Blocked a post ({acct.handle})", f"Post {pid} had not passed QA/caption checks.")
            return "failed"
        meta = self.metas[post["account"]]
        try:
            media_id = self._instagram(meta, acct, post)
        except (MetaError, http.HttpError) as e:
            return self._attempt_failed(post, acct, e)
        if media_id is None:
            return "waiting"
        fields = {"ig_media_id": media_id or None, "permalink": meta.permalink(media_id) if media_id else None}
        if post["kind"] == "reel" and post.get("to_facebook", True) and acct.facebook_reels and acct.fb_page_id:
            try:
                fields["fb_video_id"] = meta.facebook_reel(acct.fb_page_id, self._urls(post)[0], post["caption"])
            except (MetaError, http.HttpError) as e:
                fields["fb_error"] = http.scrub(str(e))[:500]
                self.alert(f"Facebook Reel failed ({acct.handle})", f"Post {pid} is on Instagram but not Facebook: "
                           f"{fields['fb_error']}")
        self._finish(post, "posted", posted_at=now.isoformat(), last_error=None, **fields)
        if self.s.delete_media_after_post:
            try:
                self.store.delete_media([m["path"] for m in post.get("media") or []])
            except http.HttpError as e:
                print(f"media delete failed for post {pid}: {e}")
        return "posted"

    # -- Instagram steps -------------------------------------------------------------------------------------
    def _urls(self, post: dict) -> list[str]:
        return [self.store.public_url(m["path"]) for m in post.get("media") or []]

    def _instagram(self, meta: Meta, acct, post: dict) -> str | None:
        """Media id once published ("" if Meta published it on an earlier run we lost track of); None while Meta
        is still processing the video (the next run picks it up)."""
        ig = acct.ig_user_id
        container = post.get("ig_container")
        if container:
            status = meta.container_status(container)
            if status == "PUBLISHED":
                return ""
            if status in ("ERROR", "EXPIRED"):
                self.store.update_post(post["id"], ig_container=None)
                raise MetaError(f"container {status}; it will be rebuilt next run")
        else:
            container = self._container(meta, ig, post)
            self.store.update_post(post["id"], ig_container=container, status="publishing")
            self.store.log(post["id"], "container", {"container": container})
        if not meta.wait_ready(container, max_seconds=self.s.pub("container_wait_seconds", 300)):
            return None
        media_id = meta.publish(ig, container)
        self.store.log(post["id"], "published", {"media_id": media_id})
        return media_id

    def _container(self, meta: Meta, ig: str, post: dict) -> str:
        urls = self._urls(post)
        if not urls:
            raise MetaError("post has no media")
        extra = {self.s.ai_label_param: "true"} if post.get("is_ai") else None
        collab = post.get("collaborators") or None
        kind = post["kind"]
        if kind == "carousel":
            if not 2 <= len(urls) <= 10:
                raise MetaError(f"a carousel needs 2-10 items, has {len(urls)}")
            children = [meta.container(ig, kind="image", url=u, carousel_item=True) for u in urls]
            for c in children:
                if not meta.wait_ready(c, max_seconds=self.s.pub("container_wait_seconds", 300)):
                    raise MetaError("carousel slide still processing")
            return meta.container(ig, kind="carousel", children=children, caption=post["caption"],
                                  collaborators=collab, extra=extra)
        return meta.container(ig, kind=kind, url=urls[0], caption=post["caption"], collaborators=collab,
                              extra=extra)

    def _attempt_failed(self, post: dict, acct, err: Exception) -> str:
        msg = http.scrub(str(err))[:500]
        attempts = (post.get("attempts") or 0) + 1
        self.store.log(post["id"], "error", {"error": msg, "attempt": attempts})
        if attempts >= self.s.pub("max_attempts", 3):
            self._finish(post, "failed", attempts=attempts, last_error=msg)
            self.alert(f"Post failed ({acct.handle})", f"Post {post['id']} failed {attempts} times: {msg}",
                       priority="high")
            return "failed"
        self.store.update_post(post["id"], attempts=attempts, last_error=msg)
        return "waiting"

    def _finish(self, post: dict, status: str, **fields) -> None:
        self.store.update_post(post["id"], status=status, **fields)
        self.store.log(post["id"], status, {k: v for k, v in fields.items() if k != "posted_at"})

    # -- the reserve -----------------------------------------------------------------------------------------
    def slots(self, acct, now: datetime, days: int) -> list[tuple[str, datetime]]:
        """(kind, UTC time) of the account's slots from now through the next `days` days."""
        tz = ZoneInfo(acct.timezone)
        local_today = now.astimezone(tz).date()
        cfg = acct.slots or {}
        out = []
        for d in range(days + 1):
            day = local_today + timedelta(days=d)
            for kind in ("reel", "carousel"):
                if kind not in cfg:
                    continue
                if kind == "carousel" and WEEKDAYS[day.weekday()] not in cfg.get("carousel_days", []):
                    continue
                hh, mm = (int(x) for x in str(cfg[kind]).split(":"))
                at = datetime.combine(day, time(hh, mm), tz).astimezone(timezone.utc)
                if at > now:
                    out.append((kind, at))
        return out

    def free_slots(self, acct, now: datetime, days: int, kind: str) -> list[datetime]:
        """UTC times of the account's `kind` slots in the next `days` days whose local day has no such post yet."""
        tz = ZoneInfo(acct.timezone)
        taken = {_when(p["post_at"]).astimezone(tz).date()
                 for p in self.store.taken(acct.name, now - timedelta(days=1)) if p["kind"] == kind}
        return [at for k, at in self.slots(acct, now, days) if k == kind and at.astimezone(tz).date() not in taken]

    def fill_from_reserve(self, acct, now: datetime) -> int:
        """Put reserve posts into empty slots of the next reserve_days days (a killed or failed post's slot, or
        a queue that ran short). Returns how many were placed."""
        days = self.s.q("reserve_days", 3)
        tz = ZoneInfo(acct.timezone)
        taken = {(p["kind"], _when(p["post_at"]).astimezone(tz).date())
                 for p in self.store.taken(acct.name, now - timedelta(days=1))}
        placed = 0
        for kind, at in self.slots(acct, now, days):
            if (kind, at.astimezone(tz).date()) in taken:
                continue
            spare = self.store.reserve(acct.name, kind)
            if not spare:
                continue
            p = spare[0]
            self.store.update_post(p["id"], status="scheduled", post_at=at.isoformat())
            self.store.log(p["id"], "from_reserve", {"slot": at.isoformat()})
            taken.add((kind, at.astimezone(tz).date()))
            placed += 1
        return placed

    # -- daily health check ----------------------------------------------------------------------------------
    def check_queue(self, now: datetime | None = None) -> dict[str, float]:
        """Days of scheduled posts ahead per account; alert when under alarm_days or the reserve is low."""
        now = now or datetime.now(timezone.utc)
        out = {}
        for acct in self.s.accounts.values():
            if not acct.enabled:
                continue
            ahead = [_when(p["post_at"]) for p in self.store.taken(acct.name, now)
                     if p["status"] == "scheduled"]
            days = max(((max(ahead) - now).total_seconds() / 86400) if ahead else 0.0, 0.0)
            out[acct.name] = round(days, 1)
            if days < self.s.q("alarm_days", 14):
                self.alert(f"Queue low ({acct.handle})", f"Only {days:.1f} days of posts scheduled. Run the "
                           "weekly batch on the desktop.", priority="high" if days < 3 else "default")
            spare = len(self.store.reserve(acct.name, "reel"))
            if spare < 5:
                self.alert(f"Reserve low ({acct.handle})", f"{spare} reserve Reels left (aim for 10).")
        return out
