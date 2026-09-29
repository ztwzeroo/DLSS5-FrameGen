"""Check GitHub for a newer release tag. Informational only; never blocks."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable

RELEASE_API = "https://api.github.com/repos/ztwzeroo/DLSS5-FrameGen/releases/latest"


@dataclass(frozen=True)
class UpdateInfo:
    status: str  # "latest" | "available" | "unknown"
    latest_tag: str = ""
    url: str = ""


def parse_tag(tag: str) -> tuple[int, ...]:
    parts: list[int] = []
    for p in tag.strip().lower().lstrip("v").split("."):
        try:
            parts.append(int(p))
        except ValueError:
            break
    return tuple(parts) or (0,)


def check_update(
    current: str,
    fetch_bytes: Callable[[str], bytes] | None = None,
) -> UpdateInfo:
    fetch = fetch_bytes or _default_fetch
    try:
        rel = json.loads(fetch(RELEASE_API).decode("utf-8"))
        tag = str(rel.get("tag_name", ""))
        url = str(rel.get("html_url", ""))
    except Exception:  # noqa: BLE001 — 任何网络/解析失败都不阻塞
        return UpdateInfo("unknown")
    if not tag:
        return UpdateInfo("unknown")
    status = "available" if parse_tag(tag) > parse_tag(current) else "latest"
    return UpdateInfo(status, tag, url)


def _default_fetch(url: str) -> bytes:
    import urllib.request

    req = urllib.request.Request(url, headers={"User-Agent": "dlss-combo/0.2"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read()
