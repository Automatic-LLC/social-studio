"""What has worked on an account: a short Markdown report from our own posts' stats (Meta Graph API only)."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from statistics import median
from zoneinfo import ZoneInfo

FORMAT = {"REELS": "Reel", "CAROUSEL_ALBUM": "Carousel", "IMAGE": "Photo", "VIDEO": "Video", "STORY": "Story"}


def _fmt(post: dict) -> str:
    if post.get("media_product_type") == "REELS":
        return "Reel"
    return FORMAT.get(post.get("media_type", ""), post.get("media_type", "?"))


def _score(post: dict) -> int:
    return int(post.get("views") or post.get("reach") or post.get("like_count") or 0)


def report(profile: dict, posts: list[dict], tz: str = "America/Chicago", top: int = 10) -> str:
    """posts: media() rows, each merged with its media_insights()."""
    z = ZoneInfo(tz)
    lines = [f"# @{profile.get('username', '?')} ({datetime.now(z):%Y-%m-%d})", "",
             f"- Followers {profile.get('followers_count', '?')}, following {profile.get('follows_count', '?')}, "
             f"posts {profile.get('media_count', '?')}",
             f"- Name: {profile.get('name') or '-'}; link: {profile.get('website') or '-'}",
             f"- Bio: {(profile.get('biography') or '-').replace(chr(10), ' / ')}", ""]
    if not posts:
        return "\n".join(lines + ["No posts found."])
    by_fmt = defaultdict(list)
    for p in posts:
        by_fmt[_fmt(p)].append(p)
    lines += [f"## By format (last {len(posts)} posts, median)", "", "| Format | Posts | Views | Reach | Likes | Shares | Saves |",
              "|---|---|---|---|---|---|---|"]
    for f, ps in sorted(by_fmt.items(), key=lambda kv: -len(kv[1])):
        def med(k):
            vals = [p[k] for p in ps if p.get(k) is not None]
            return f"{median(vals):.0f}" if vals else "-"
        lines.append(f"| {f} | {len(ps)} | {med('views')} | {med('reach')} | {med('like_count')} | {med('shares')} "
                     f"| {med('saved')} |")
    hours = defaultdict(list)
    for p in posts:
        if p.get("timestamp"):
            t = datetime.strptime(p["timestamp"], "%Y-%m-%dT%H:%M:%S%z").astimezone(z)
            hours[f"{t:%a} {t:%H}:00"].append(_score(p))
    lines += ["", f"## Top {top} posts", ""]
    for p in sorted(posts, key=_score, reverse=True)[:top]:
        cap = " ".join((p.get("caption") or "").split())[:90]
        lines.append(f"- **{_score(p)}** {_fmt(p)} {p.get('timestamp', '')[:10]}: {cap} ({p.get('permalink', '')})")
    best = sorted(hours.items(), key=lambda kv: -median(kv[1]))[:5]
    lines += ["", "## Best posting times so far (median views, account time)", ""]
    lines += [f"- {k}: {median(v):.0f} ({len(v)} posts)" for k, v in best]
    return "\n".join(lines) + "\n"
