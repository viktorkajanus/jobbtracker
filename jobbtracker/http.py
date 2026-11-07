from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

USER_AGENT = "jobbtracker/0.1 (+https://github.com/; personal job search tool)"


class Http:
    def __init__(self, timeout: float = 30, delay: float = 0.3, retries: int = 2):
        self.timeout = timeout
        self.delay = delay
        self.retries = retries

    def _request(self, url: str, data: bytes | None = None, headers: dict | None = None) -> bytes:
        req = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT, **(headers or {})})
        for attempt in range(self.retries + 1):
            time.sleep(self.delay * (1 + 4 * attempt))
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return resp.read()
            except urllib.error.HTTPError as e:
                if e.code < 500 and e.code != 429 or attempt == self.retries:
                    raise
            except (TimeoutError, urllib.error.URLError):
                if attempt == self.retries:
                    raise
        raise AssertionError("unreachable")

    def get_text(self, url: str) -> str:
        return self._request(url).decode("utf-8", errors="replace")

    def get_json(self, url: str):
        return json.loads(self._request(url, headers={"Accept": "application/json"}))

    def post_json(self, url: str, body: dict):
        data = json.dumps(body).encode()
        return json.loads(self._request(url, data, {"Content-Type": "application/json", "Accept": "application/json"}))
