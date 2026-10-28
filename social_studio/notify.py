"""Phone alerts through ntfy.sh (free app; subscribe to the NTFY_TOPIC topic). Never raises: an alert that
cannot be sent must not stop a post."""
from __future__ import annotations

import requests

from . import http


def alert(topic: str, title: str, message: str, priority: str = "default", click: str | None = None) -> bool:
    if not topic:
        print(f"[alert, no NTFY_TOPIC] {title}: {message}")
        return False
    headers = {"Title": title.encode("utf-8"), "Priority": priority, "Tags": "dog"}
    if click:
        headers["Click"] = click
    try:
        requests.post(f"https://ntfy.sh/{topic}", data=http.scrub(message).encode("utf-8"), headers=headers,
                      timeout=20)
        return True
    except requests.RequestException as e:
        print(f"[alert failed] {type(e).__name__}")
        return False
