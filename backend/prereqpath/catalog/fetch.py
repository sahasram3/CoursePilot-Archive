"""Polite, cached fetcher for catalog.unc.edu.

- Honors robots.txt and additionally refuses /archives/ outright: archived
  catalogs must come from a legitimately obtained copy, never from crawling.
- Rate limited, identifies itself, caches raw HTML under data/raw/ so parsing
  can be re-run offline. Cached pages carry their retrieval time and SHA-256.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from .. import DATA_DIR

BASE = "https://catalog.unc.edu"
USER_AGENT = "CoursePilot/1.0 (student degree-planning project; polite, cached, robots-aware)"
FORBIDDEN_PREFIXES = ("/archives/",)
MIN_DELAY_SECONDS = 1.5


@dataclass
class Page:
    url: str
    html: str
    retrieved_at: str
    sha256: str
    from_cache: bool


class CatalogFetcher:
    def __init__(self, cache_dir: Path | None = None, *, refresh: bool = False,
                 offline: bool = False, delay: float = MIN_DELAY_SECONDS):
        self.cache_dir = cache_dir or DATA_DIR / "raw"
        self.refresh = refresh
        self.offline = offline
        self.delay = max(delay, MIN_DELAY_SECONDS)
        self._last_request = 0.0
        self._robots: RobotFileParser | None = None
        self._client: httpx.Client | None = None

    # ------------------------------------------------------------------ policy
    def _check_allowed(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != "catalog.unc.edu":
            raise ValueError(f"Refusing non-catalog URL: {url}")
        if parsed.path.startswith(FORBIDDEN_PREFIXES):
            raise PermissionError(f"Archived catalog paths are never crawled: {url}")
        if self.offline:
            return
        if self._robots is None:
            robots = RobotFileParser()
            robots.parse(self._get(BASE + "/robots.txt").splitlines())
            self._robots = robots
        if not self._robots.can_fetch(USER_AGENT, url):
            raise PermissionError(f"Disallowed by robots.txt: {url}")

    def _get(self, url: str) -> str:
        if self._client is None:
            self._client = httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30,
                                        follow_redirects=False)
        wait = self._last_request + self.delay - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        response = self._client.get(url)
        self._last_request = time.monotonic()
        if response.status_code != 200:
            raise RuntimeError(f"GET {url} returned HTTP {response.status_code}")
        return response.text

    # ------------------------------------------------------------------- cache
    def _cache_path(self, url: str) -> Path:
        slug = re.sub(r"[^a-z0-9]+", "_", urlparse(url).path.lower()).strip("_") or "root"
        return self.cache_dir / f"{slug}.html"

    def fetch(self, url: str) -> Page:
        self._check_allowed(url)
        path = self._cache_path(url)
        meta_path = path.with_suffix(".json")
        if path.exists() and meta_path.exists() and not self.refresh:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            html = path.read_text(encoding="utf-8")
            return Page(url, html, meta["retrieved_at"], meta["sha256"], True)
        if self.offline:
            raise FileNotFoundError(f"Not cached and offline: {url}")
        html = self._get(url)
        retrieved = datetime.now(timezone.utc).isoformat(timespec="seconds")
        digest = hashlib.sha256(html.encode("utf-8")).hexdigest()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")
        meta_path.write_text(json.dumps({"url": url, "retrieved_at": retrieved, "sha256": digest}),
                             encoding="utf-8")
        return Page(url, html, retrieved, digest, False)
