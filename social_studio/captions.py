"""Caption rules, so captions (AI-written or not) can't drift: one statement plus an optional question, a word
range, 1-2 emojis, 3-5 hashtags and a ban list. Limits come from the account's `captions:` block."""
from __future__ import annotations

import re

_EMO = "\U0001F000-\U0001F1E5\U0001F200-\U0001F3FA\U0001F400-\U0001FAFF☀-➿⬀-⯿←-⇿〰〽"
_MOD = "\U0001F3FB-\U0001F3FF️"
EMOJI_RE = re.compile(
    rf"[\U0001F1E6-\U0001F1FF]{{2}}"                       # a flag is two regional letters
    rf"|[{_EMO}][{_MOD}]*(?:‍[{_EMO}][{_MOD}]*)*"     # one emoji with skin tone / joined parts
)
HASHTAG_RE = re.compile(r"#\w+")
HANDLE_RE = re.compile(r"@[\w.]+")
WORD_RE = re.compile(r"[\w'/-]*\w[\w'/-]*")
IG_MAX_CHARS = 2200

DEFAULTS = dict(min_words=6, max_words=20, min_emojis=1, max_emojis=2, min_hashtags=3, max_hashtags=5, banned=[])


def emojis(text: str) -> list[str]:
    return EMOJI_RE.findall(text)


def split(caption: str) -> tuple[str, list[str]]:
    """(the text line, the hashtags). Hashtags may sit at the end or on their own lines."""
    tags = HASHTAG_RE.findall(caption)
    text = " ".join(HASHTAG_RE.sub("", caption).split())
    return text, tags


def words(text: str) -> list[str]:
    plain = EMOJI_RE.sub(" ", HANDLE_RE.sub(" ", text))
    return WORD_RE.findall(plain)


def check(caption: str, rules: dict | None = None) -> list[str]:
    """Problems with the caption; an empty list means it passes."""
    r = {**DEFAULTS, **(rules or {})}
    text, tags = split(caption)
    problems: list[str] = []
    if len(caption) > IG_MAX_CHARS:
        problems.append(f"over {IG_MAX_CHARS} characters")
    n = len(words(text))
    if not r["min_words"] <= n <= r["max_words"]:
        problems.append(f"{n} words (want {r['min_words']}-{r['max_words']})")
    e = len(emojis(text))
    if not r["min_emojis"] <= e <= r["max_emojis"]:
        problems.append(f"{e} emojis (want {r['min_emojis']}-{r['max_emojis']})")
    t = len(tags)
    if not r["min_hashtags"] <= t <= r["max_hashtags"]:
        problems.append(f"{t} hashtags (want {r['min_hashtags']}-{r['max_hashtags']})")
    if len({x.lower() for x in tags}) != t:
        problems.append("repeated hashtag")
    chunks = [c for c in re.findall(r"[^.!?]+[.!?]*", EMOJI_RE.sub(" ", text)) if WORD_RE.search(c)]
    questions = sum(c.rstrip().endswith("?") for c in chunks)
    statements = len(chunks) - questions
    if statements > 1 or questions > 1:
        problems.append("more than one sentence plus one question")
    low = text.lower().replace("’", "'")
    for bad in r["banned"]:
        if re.search(rf"(?<!\w){re.escape(bad.lower())}(?!\w)", low):
            problems.append(f"banned phrase: {bad}")
    return problems


def build(text: str, hashtags: list[str]) -> str:
    return f"{text.strip()}\n\n{' '.join(hashtags)}"
