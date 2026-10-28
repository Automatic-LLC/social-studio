"""One place for HTTP calls: retries with backoff on network errors, 429 and 5xx; errors never carry tokens."""
from __future__ import annotations

import re
import time

import requests

RETRY_STATUS = {429, 500, 502, 503, 504}
_TOKEN_RE = re.compile(r"(access_token=|OAuth |Bearer |apikey: ?)[^\s&\"']+")


class HttpError(Exception):
    def __init__(self, status: int, message: str, body: dict | None = None):
        super().__init__(f"HTTP {status}: {scrub(message)}")
        self.status = status
        self.body = body or {}


def scrub(text: str) -> str:
    """Remove anything that looks like a token from text bound for logs, alerts or the database."""
    return _TOKEN_RE.sub(r"\1***", str(text))


def request(method: str, url: str, *, session=None, tries: int = 4, backoff: float = 2.0, sleep=time.sleep,
            timeout: float = 60, **kw) -> requests.Response:
    s = session or requests
    last: Exception | None = None
    for i in range(tries):
        try:
            r = s.request(method, url, timeout=timeout, **kw)
        except requests.RequestException as e:
            last = HttpError(0, f"{type(e).__name__}: {e}")
        else:
            if r.status_code < 400:
                return r
            try:
                body = r.json()
            except ValueError:
                body = {}
            msg = (body.get("error") or {}).get("message") if isinstance(body.get("error"), dict) else None
            last = HttpError(r.status_code, msg or body.get("message") or r.text[:300], body)
            # Meta marks some 400s as transient (is_transient / code 2, 4, 17, 32, 613: rate limits, service down).
            err = body.get("error") if isinstance(body.get("error"), dict) else {}
            transient = err.get("is_transient") or err.get("code") in (1, 2, 4, 17, 32, 613)
            if r.status_code not in RETRY_STATUS and not transient:
                raise last
        if i < tries - 1:
            sleep(backoff * (2 ** i))
    assert last is not None
    raise last
