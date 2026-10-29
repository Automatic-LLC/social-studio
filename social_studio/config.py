"""Settings: config.yaml, accounts/*.yaml and secrets from the environment or a .env file.

Secrets are read from environment variables first (GitHub Actions secrets), then from the first .env file found:
$SOCIAL_STUDIO_ENV, ./.env, C:\\Trading\\SocialStudio.env. They are never printed or logged.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
ENV_FILES = [os.environ.get("SOCIAL_STUDIO_ENV", ""), str(ROOT / ".env"), r"C:\Trading\SocialStudio.env"]
SECRET_NAMES = ("META_TOKEN", "MAKE_WEBHOOK_URL", "SUPABASE_URL", "SUPABASE_KEY", "NTFY_TOPIC", "PEXELS_KEY")


def _read_env_file(path: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def secret(name: str) -> str:
    """The secret's value, or "" when it is not set anywhere."""
    if os.environ.get(name):
        return os.environ[name]
    for path in ENV_FILES:
        if path and Path(path).is_file():
            val = _read_env_file(path).get(name, "")
            if val:
                return val
    return ""


@dataclass
class Account:
    name: str
    handle: str
    enabled: bool = True
    timezone: str = "America/Chicago"
    ig_user_id: str = ""
    fb_page_id: str = ""
    token_env: str = "META_TOKEN"
    publish_via: str = "meta"           # meta: our own Meta app; make: a Make.com scenario (see make.py)
    make_webhook_env: str = "MAKE_WEBHOOK_URL"
    facebook_reels: bool = True
    slots: dict = field(default_factory=dict)
    captions: dict = field(default_factory=dict)
    hashtag_sets: dict = field(default_factory=dict)
    contest: dict = field(default_factory=dict)

    @property
    def token(self) -> str:
        return secret(self.token_env)

    @property
    def make_url(self) -> str:
        return secret(self.make_webhook_env)


@dataclass
class Settings:
    paused: bool = False
    graph_version: str = "v24.0"
    media_bucket: str = "media"
    delete_media_after_post: bool = True
    ai_label_param: str = "is_ai_generated"
    font: str = ""
    publisher: dict = field(default_factory=dict)
    queue: dict = field(default_factory=dict)
    accounts: dict[str, Account] = field(default_factory=dict)

    def pub(self, key: str, default):
        return self.publisher.get(key, default)

    def q(self, key: str, default):
        return self.queue.get(key, default)


def load(root: Path = ROOT) -> Settings:
    raw = yaml.safe_load((root / "config.yaml").read_text(encoding="utf-8")) or {}
    s = Settings(**{k: v for k, v in raw.items() if k in Settings.__dataclass_fields__ and k != "accounts"})
    for path in sorted((root / "accounts").glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        known = {k: v for k, v in data.items() if k in Account.__dataclass_fields__}
        known["ig_user_id"] = str(known.get("ig_user_id") or "")
        known["fb_page_id"] = str(known.get("fb_page_id") or "")
        s.accounts[path.stem] = Account(name=path.stem, **known)
    return s
