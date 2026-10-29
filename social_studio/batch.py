"""A batch: one plan file of Reels → rendered videos → a preview page → (with --go) queued posts.

    py -m social_studio batch plans/week1.yaml          render + preview only (nothing uploaded)
    py -m social_studio batch plans/week1.yaml --go     upload and schedule what the preview showed

Plan file (paths are relative to the plan file):

    account: ur_dailydog
    items:
      - clip: clips/zoomies.mp4            # a clip we own or have written permission for
        text: "POV: you whispered 'walk' from 3 rooms away"
        caption: "Corgi zoomies at 6am, every single day 😂 Does yours do this?"
        hashtags: zoomies                   # a set name from accounts/<name>.yaml, or a list
        source: own                         # own | submission (credit: "@owner") | pexels (credit: "Jane Doe")
      - pexels: "golden retriever running"  # a stock clip; credited in the caption and on screen
        text: "Me leaving the house vs me hearing my name"
        caption: "Golden retriever logic, zero thoughts just vibes 🐕 What would yours do?"
        hashtags: general
        voiceover: vo/golden.wav            # optional
        music: music/bouncy.mp3             # optional, royalty-free only
        reserve: true                       # optional: goes to the reserve, not a slot

Renders are cached by content, so running the preview and then --go renders each Reel once. Opening the preview is
the human check: --go marks every post qa_passed.
"""
from __future__ import annotations

import hashlib
import html
import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

from . import captions
from .edit import reels
from .publisher import Publisher
from .sources import pexels


class PlanError(Exception):
    pass


def _key(item: dict) -> str:
    return hashlib.sha1(json.dumps(item, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:10]


def _tags(item: dict, acct) -> list[str]:
    tags = item.get("hashtags", "general")
    if isinstance(tags, str):
        if tags not in acct.hashtag_sets:
            raise PlanError(f"no hashtag set {tags!r} in accounts/{acct.name}.yaml")
        return list(acct.hashtag_sets[tags])
    return list(tags)


def check_plan(plan: dict, acct, plan_dir: Path) -> list[str]:
    """Every problem in the plan, so all of them can be fixed in one go."""
    problems = []
    items = plan.get("items") or []
    if not items:
        problems.append("plan has no items")
    for i, it in enumerate(items, 1):
        where = f"item {i}"
        if bool(it.get("clip")) == bool(it.get("pexels")):
            problems.append(f"{where}: give exactly one of clip / pexels")
        for f in ("clip", "voiceover", "music"):
            if it.get(f) and not (plan_dir / it[f]).is_file():
                problems.append(f"{where}: no file {it[f]}")
        if it.get("source") == "submission" and not it.get("credit"):
            problems.append(f"{where}: a submission needs credit: \"@owner\"")
        if it.get("clip") and it.get("source") == "pexels" and not it.get("credit"):
            problems.append(f"{where}: a Pexels clip needs credit: \"<the creator's name on Pexels>\"")
        try:
            cap = captions.build(it.get("caption", ""), _tags(it, acct))
        except PlanError as e:
            problems.append(f"{where}: {e}")
            continue
        for p in captions.check(cap, acct.captions):
            problems.append(f"{where}: caption {p}")
    return problems


class Batch:
    def __init__(self, settings, store, acct, plan_path: Path, out_root: Path, *, pexels_key: str = "",
                 render=reels.render, search=pexels.search, download=pexels.download, font: str | None = None):
        self.s, self.store, self.acct = settings, store, acct
        self.plan_path = Path(plan_path)
        self.plan_dir = self.plan_path.parent
        self.plan = yaml.safe_load(self.plan_path.read_text(encoding="utf-8")) or {}
        if self.plan.get("account", acct.name) != acct.name:
            raise PlanError(f"plan is for {self.plan['account']}, not {acct.name}")
        digest = hashlib.sha1(self.plan_path.read_bytes()).hexdigest()[:6]
        self.batch_id = f"{self.plan_path.stem}-{digest}"
        self.out = Path(out_root) / acct.name / self.batch_id
        self.manifest_path = self.out / "manifest.json"
        self.pexels_key = pexels_key
        self.render, self.search, self.download = render, search, download
        self.font = font

    # -- building ------------------------------------------------------------------------------------------
    def _manifest(self) -> dict:
        if self.manifest_path.is_file():
            return json.loads(self.manifest_path.read_text(encoding="utf-8"))
        return {}

    def _stock(self, it: dict, used: set[str], picked: dict) -> dict:
        key = _key(it)
        if key in picked:
            return picked[key]
        if not self.pexels_key:
            raise PlanError("PEXELS_KEY not set (SETUP.md, section G)")
        for hit in self.search(it["pexels"], self.pexels_key):
            ref = f"pexels:{hit['id']}"
            if ref not in used:
                used.add(ref)
                picked[key] = hit
                return hit
        raise PlanError(f"no unused Pexels clip for {it['pexels']!r}")

    def build(self) -> list[dict]:
        """Render every item (cached) and return one entry per post, in plan order."""
        problems = check_plan(self.plan, self.acct, self.plan_dir)
        if problems:
            raise PlanError("\n".join(problems))
        self.out.mkdir(parents=True, exist_ok=True)
        manifest = self._manifest()
        picked = manifest.get("pexels", {})
        used = self.store.used_refs(self.acct.name) - {f"pexels:{h['id']}" for h in picked.values()}
        entries = []
        for it in self.plan["items"]:
            key = _key(it)
            credit, ref, on_screen = it.get("credit"), None, None
            if it.get("pexels"):
                hit = self._stock(it, used, picked)
                clip = self.download(hit, self.out.parent / "pexels")
                credit, ref = pexels.credit(hit), f"pexels:{hit['id']}"
                on_screen = f"Video: {hit['user']} / Pexels"
            else:
                clip = self.plan_dir / it["clip"]
                if it.get("source") == "pexels":  # downloaded by hand from pexels.com
                    credit = f"Video by {it['credit']} on Pexels"
                    on_screen = f"Video: {it['credit']} / Pexels"
            caption = captions.build(it["caption"], _tags(it, self.acct))
            if it.get("pexels") or it.get("source") == "pexels":
                caption += f"\n{credit}"
            out = self.out / f"{key}.mp4"
            if not out.is_file():
                spec = reels.ReelSpec(
                    clip=Path(clip), out=out, text=it.get("text", ""), start=float(it.get("start", 0)),
                    duration=it.get("duration"),
                    voiceover=self.plan_dir / it["voiceover"] if it.get("voiceover") else None,
                    music=self.plan_dir / it["music"] if it.get("music") else None,
                    keep_clip_audio=it.get("keep_clip_audio", True), credit=on_screen)
                self.render(spec, handle=self.acct.handle, font=self.font)
            entries.append({"key": key, "file": str(out), "caption": caption, "credit": credit, "source_ref": ref,
                            "source": "pexels" if it.get("pexels") else it.get("source", "own"),
                            "is_ai": bool(it.get("ai")), "reserve": bool(it.get("reserve")),
                            "collaborators": it.get("collab") or []})
        self.manifest_path.write_text(json.dumps({"pexels": picked}, indent=1), encoding="utf-8")
        return entries

    def schedule(self, entries: list[dict], now: datetime) -> list[tuple[dict, datetime | None]]:
        """Give each non-reserve entry the next free Reel slot within horizon_days; the rest go to the reserve."""
        pub = Publisher(self.s, self.store, {})
        slots = pub.free_slots(self.acct, now, self.s.q("horizon_days", 21), "reel")
        out = []
        for e in entries:
            out.append((e, None if e["reserve"] or not slots else slots.pop(0)))
        return out

    # -- outputs -------------------------------------------------------------------------------------------
    def preview(self, plan: list[tuple[dict, datetime | None]]) -> Path:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(self.acct.timezone)
        cards = []
        for e, at in plan:
            when = at.astimezone(tz).strftime("%a %b %d, %I:%M %p") if at else "reserve"
            cards.append(f"""<div class="card"><video src="{html.escape(Path(e['file']).name)}" controls
playsinline preload="metadata"></video><p class="when">{html.escape(when)}{' · AI label' if e['is_ai'] else ''}</p>
<pre>{html.escape(e['caption'])}</pre></div>""")
        page = f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Batch preview</title>
<style>body{{font-family:system-ui,sans-serif;margin:16px;background:#faf7f2;color:#222}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:16px}}
.card{{background:#fff;border-radius:12px;padding:10px;box-shadow:0 1px 4px #0002}}
video{{width:100%;border-radius:8px;background:#000}}.when{{font-weight:600;margin:8px 0 4px}}
pre{{white-space:pre-wrap;font:inherit;font-size:.9em;margin:0}}</style></head><body>
<h1>@{html.escape(self.acct.handle)} · {html.escape(self.batch_id)}</h1>
<p>{len(plan)} Reels. Nothing is uploaded yet. Happy? Run the same command with <code>--go</code>.</p>
<div class="grid">{''.join(cards)}</div></body></html>"""
        path = self.out / "preview.html"
        path.write_text(page, encoding="utf-8")
        return path

    def go(self, plan: list[tuple[dict, datetime | None]]) -> list[dict]:
        """Upload and queue. Every post is qa_passed: a person looked at the preview first."""
        if self.store.posts(account=f"eq.{self.acct.name}", batch_id=f"eq.{self.batch_id}", select="id", limit="1"):
            raise PlanError(f"batch {self.batch_id} is already queued (from this PC or the other one); "
                            "change the plan file to make a new batch")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        rows = []
        for e, at in plan:
            path = f"{self.acct.name}/{stamp}/{self.batch_id}-{e['key']}.mp4"
            self.store.upload(Path(e["file"]), path)
            rows.append(self.store.add_post({
                "account": self.acct.name, "kind": "reel", "status": "scheduled" if at else "reserve",
                "post_at": at.isoformat() if at else None, "caption": e["caption"], "media": [{"path": path}],
                "source": e["source"], "credit": e["credit"], "source_ref": e["source_ref"], "is_ai": e["is_ai"],
                "qa_passed": True, "caption_ok": True, "collaborators": e["collaborators"],
                "batch_id": self.batch_id}))
        return rows
