"""Posting through a Make.com scenario instead of our own Meta app (account `publish_via: make`).

Make is already approved by Meta, so this needs no Meta developer account: the scenario starts with a Custom webhook,
posts with the "Instagram for Business" modules and (ideally) ends with a Webhook response that returns
{"id": "<Instagram media id>"}. The webhook URL is a secret: anyone who has it can post to the account.
"""
from __future__ import annotations

import time

from . import http


class MakeError(Exception):
    pass


class MakeHook:
    def __init__(self, url: str, session=None, sleep=time.sleep, timeout: float = 300):
        if not url.startswith("https://"):
            raise MakeError("MAKE_WEBHOOK_URL not set (or not an https:// link); see SETUP.md")
        self.url = url
        self.session = session
        self.sleep = sleep
        self.timeout = timeout

    def post(self, payload: dict) -> dict:
        """Send one post to the scenario. One try only: a retry could post twice, so the publisher decides."""
        r = http.request("POST", self.url, json=payload, session=self.session, sleep=self.sleep, tries=1,
                         timeout=self.timeout)
        try:
            body = r.json()
        except ValueError:
            body = {}  # "Accepted": the scenario has no Webhook response module; it runs on its own
        return body if isinstance(body, dict) else {}
