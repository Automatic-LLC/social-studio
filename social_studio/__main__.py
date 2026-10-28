"""Social Studio command line. Run from the repo folder:

    py -m social_studio doctor                      check secrets, Meta token, Pages/IG ids, Supabase
    py -m social_studio test-post --account ur_dailydog --file dog.jpg --caption "..." --yes
    py -m social_studio add --account ur_dailydog --kind reel --file clip.mp4 --caption "..." --at "2026-11-02 18:00"
    py -m social_studio list --account ur_dailydog  upcoming queue
    py -m social_studio kill 42                     stop one post (a reserve post takes its slot)
    py -m social_studio publish-due                 what GitHub Actions runs every 15 minutes
    py -m social_studio check-queue                 the daily low-queue alarm
    py -m social_studio batch plans/week1.yaml      render a plan's Reels + preview page (add --go to queue them)
    py -m social_studio profile --account ur_dailydog   what has worked so far (writes out/profile-<account>.md)
"""
from __future__ import annotations

import argparse
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from . import captions, config, http, notify
from .meta import Meta, MetaError
from .publisher import Publisher
from .store import Store


def _store(s) -> Store:
    return Store(config.secret("SUPABASE_URL"), config.secret("SUPABASE_KEY"), s.media_bucket)


def _metas(s) -> dict[str, Meta]:
    return {a.name: Meta(a.token, s.graph_version) for a in s.accounts.values() if a.token}


def _alert(title, message, priority="default"):
    notify.alert(config.secret("NTFY_TOPIC"), title, message, priority)


def _account(s, name):
    if name not in s.accounts:
        sys.exit(f"no account {name!r}; have: {', '.join(s.accounts)}")
    return s.accounts[name]


def cmd_doctor(s, a):
    ok = True
    for name in config.SECRET_NAMES:
        have = bool(config.secret(name))
        ok &= have or name in ("NTFY_TOPIC", "PEXELS_KEY")
        print(f"  {'OK ' if have else '-- '} {name} {'set' if have else 'NOT SET'}")
    token = config.secret("META_TOKEN")
    if token:
        try:
            m = Meta(token, s.graph_version)
            me = m.whoami()
            print(f"  OK  Meta token belongs to: {me.get('name')} ({me.get('id')})")
            for p in m.pages():
                ig = p.get("instagram_business_account") or {}
                print(f"      Page {p.get('name')!r}: fb_page_id {p.get('id')}  "
                      f"ig_user_id {ig.get('id', '(no Instagram linked)')} @{ig.get('username', '')}")
            for acct in s.accounts.values():
                if acct.ig_user_id:
                    lim = m.publishing_limit(acct.ig_user_id)
                    print(f"  OK  @{acct.handle}: used {lim.get('quota_usage')} of "
                          f"{(lim.get('config') or {}).get('quota_total')} posts in 24h")
                else:
                    print(f"  --  @{acct.handle}: put ig_user_id / fb_page_id from above into accounts/{acct.name}.yaml")
        except (MetaError, http.HttpError) as e:
            ok = False
            print(f"  ERR Meta: {http.scrub(str(e))}")
    if config.secret("SUPABASE_URL") and config.secret("SUPABASE_KEY"):
        try:
            _store(s).posts(limit="1")
            print("  OK  Supabase: posts table reachable")
        except http.HttpError as e:
            ok = False
            print(f"  ERR Supabase: {e} (did you run supabase/migrations/001_init.sql?)")
    print("all good" if ok else "fix the items above (SETUP.md)")
    return 0 if ok else 1


def _upload(store: Store, acct, files: list[str]) -> list[dict]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    media = []
    for f in files:
        p = Path(f)
        if not p.is_file():
            sys.exit(f"no file {f}")
        path = f"{acct.name}/{stamp}/{uuid.uuid4().hex[:8]}{p.suffix.lower()}"
        store.upload(p, path)
        media.append({"path": path})
    return media


def cmd_test_post(s, a):
    acct = _account(s, a.account)
    if not acct.ig_user_id:
        sys.exit(f"set ig_user_id in accounts/{acct.name}.yaml first (run doctor)")
    print(f"This posts {a.file} to @{acct.handle} on Instagram for real, with caption: {a.caption!r}")
    if not a.yes:
        print("add --yes to post it")
        return 1
    store, meta = _store(s), Meta(acct.token, s.graph_version)
    media = _upload(store, acct, [a.file])
    url = store.public_url(media[0]["path"])
    kind = "reel" if Path(a.file).suffix.lower() in (".mp4", ".mov") else "image"
    c = meta.container(acct.ig_user_id, kind=kind, url=url, caption=a.caption)
    if not meta.wait_ready(c, max_seconds=600):
        sys.exit("Meta is still processing the file after 10 minutes; try again later")
    mid = meta.publish(acct.ig_user_id, c)
    print(f"posted: {meta.permalink(mid) or mid}")
    store.delete_media([media[0]["path"]])
    return 0


def cmd_add(s, a):
    acct = _account(s, a.account)
    problems = captions.check(a.caption, acct.captions) if a.kind != "story" else []
    if problems and not a.force_caption:
        sys.exit("caption fails the rules: " + "; ".join(problems) + " (or pass --force-caption)")
    if a.reserve:
        post_at = None
    elif a.at:
        post_at = datetime.strptime(a.at, "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo(acct.timezone))
    else:
        sys.exit("give --at 'YYYY-MM-DD HH:MM' (account time) or --reserve")
    store = _store(s)
    row = {
        "account": acct.name, "kind": a.kind, "status": "reserve" if a.reserve else "scheduled",
        "post_at": post_at.isoformat() if post_at else None, "caption": a.caption,
        "media": _upload(store, acct, a.file), "source": a.source, "credit": a.credit, "is_ai": a.ai,
        "qa_passed": True,  # a person added it by hand, so a person checked it
        "caption_ok": True, "collaborators": a.collab or [],
    }
    post = store.add_post(row)
    print(f"added post {post['id']} ({a.kind}, {'reserve' if a.reserve else post_at})")
    return 0


def cmd_list(s, a):
    acct = _account(s, a.account)
    store = _store(s)
    for p in store.posts(account=f"eq.{acct.name}", status="in.(scheduled,publishing,reserve,failed)"):
        when = p["post_at"] or "reserve"
        print(f"{p['id']:>5} {p['status']:<10} {p['kind']:<8} {when:<26} {p['caption'][:50]!r}")
    return 0


def cmd_kill(s, a):
    _store(s).update_post(a.id, status="killed")
    print(f"post {a.id} killed; the next publisher run fills its slot from the reserve")
    return 0


def cmd_publish_due(s, a):
    if not (config.secret("SUPABASE_URL") and config.secret("SUPABASE_KEY") and config.secret("META_TOKEN")):
        print("not set up yet (secrets missing): nothing to do")
        return 0
    print(Publisher(s, _store(s), _metas(s), _alert).run())
    return 0


def cmd_check_queue(s, a):
    if not (config.secret("SUPABASE_URL") and config.secret("SUPABASE_KEY")):
        print("not set up yet (secrets missing): nothing to do")
        return 0
    print(Publisher(s, _store(s), _metas(s), _alert).check_queue())
    return 0


def cmd_batch(s, a):
    from .batch import Batch, PlanError
    plan_path = Path(a.plan)
    if not plan_path.is_file():
        sys.exit(f"no plan file {a.plan}")
    import yaml
    name = (yaml.safe_load(plan_path.read_text(encoding="utf-8")) or {}).get("account", "")
    acct = _account(s, name)
    try:
        b = Batch(s, _store(s), acct, plan_path, Path(a.out), pexels_key=config.secret("PEXELS_KEY"),
                  font=s.font or None)
        entries = b.build()
        plan = b.schedule(entries, datetime.now(timezone.utc))
        page = b.preview(plan)
    except PlanError as e:
        sys.exit(f"plan problems:\n{e}")
    print(f"preview: {page}")
    if not a.go:
        print("open it, then run the same command with --go to upload and schedule")
        return 0
    rows = b.go(plan)
    print(f"queued {len(rows)} posts ({sum(r['status'] == 'reserve' for r in rows)} to the reserve)")
    return 0


def cmd_profile(s, a):
    from .insights import report
    acct = _account(s, a.account)
    if not acct.ig_user_id:
        sys.exit(f"set ig_user_id in accounts/{acct.name}.yaml first (run doctor)")
    m = Meta(acct.token, s.graph_version)
    posts = m.media(acct.ig_user_id, limit=a.posts)
    for p in posts:
        p.update(m.media_insights(p["id"]))
    text = report(m.profile(acct.ig_user_id), posts, acct.timezone)
    out = Path(a.out) / f"profile-{acct.name}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(text)
    print(f"saved to {out} (paste it to Claude: it holds no secrets)")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="social_studio")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor")
    t = sub.add_parser("test-post")
    t.add_argument("--account", required=True)
    t.add_argument("--file", required=True)
    t.add_argument("--caption", default="Test post 🐶")
    t.add_argument("--yes", action="store_true")
    ad = sub.add_parser("add")
    ad.add_argument("--account", required=True)
    ad.add_argument("--kind", choices=["reel", "image", "carousel", "story"], required=True)
    ad.add_argument("--file", nargs="+", required=True)
    ad.add_argument("--caption", default="")
    ad.add_argument("--at")
    ad.add_argument("--reserve", action="store_true")
    ad.add_argument("--ai", action="store_true", help="AI-made: carries Meta's AI label")
    ad.add_argument("--source", default="own", choices=["own", "submission", "pexels", "ai", "contest"])
    ad.add_argument("--credit")
    ad.add_argument("--collab", nargs="*")
    ad.add_argument("--force-caption", action="store_true")
    li = sub.add_parser("list")
    li.add_argument("--account", required=True)
    k = sub.add_parser("kill")
    k.add_argument("id", type=int)
    sub.add_parser("publish-due")
    sub.add_parser("check-queue")
    pr = sub.add_parser("profile")
    pr.add_argument("--account", required=True)
    pr.add_argument("--posts", type=int, default=60)
    pr.add_argument("--out", default=str(config.ROOT / "out"))
    b = sub.add_parser("batch")
    b.add_argument("plan")
    b.add_argument("--go", action="store_true", help="upload and schedule (after checking the preview)")
    b.add_argument("--out", default=str(config.ROOT / "out"))
    a = ap.parse_args(argv)
    s = config.load()
    return globals()["cmd_" + a.cmd.replace("-", "_")](s, a)


if __name__ == "__main__":
    sys.exit(main())
