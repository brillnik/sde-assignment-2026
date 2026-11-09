"""Thin HTTP client for the simulator. Retries transient failures (connect errors, 5xx) with backoff; 4xx are
returned to the caller as ApiError because they carry meaning (409 stale_base_version, 402 no credits, 403...)."""
import time

import httpx


class ApiError(Exception):
    def __init__(self, status, body):
        super().__init__(f"{status} {body}")
        self.status = status
        self.body = body if isinstance(body, dict) else {"raw": body}

    @property
    def code(self):
        return self.body.get("error") or self.body.get("detail") if isinstance(self.body, dict) else None


class Api:
    def __init__(self, base_url, log=print):
        self.c = httpx.Client(base_url=base_url, timeout=300)
        self.log = log

    def _req(self, method, path, **kw):
        delay = 0.5
        for attempt in range(12):
            try:
                r = self.c.request(method, path, **kw)
            except (httpx.TransportError, httpx.TimeoutException) as e:
                self.log(f"[api] {method} {path} transport error {e!r}; retry {attempt}")
                time.sleep(delay)
                delay = min(delay * 2, 10)
                continue
            if r.status_code >= 500:
                self.log(f"[api] {method} {path} -> {r.status_code}; retry {attempt}")
                time.sleep(delay)
                delay = min(delay * 2, 10)
                continue
            if r.status_code >= 400:
                try:
                    body = r.json()
                except Exception:
                    body = {"raw": r.text[:300]}
                raise ApiError(r.status_code, body)
            return r
        raise ApiError(599, {"error": "unreachable", "detail": f"{method} {path} failed after retries"})

    def get(self, path, **params):
        return self._req("GET", path, params=params or None).json()

    def post(self, path, body):
        return self._req("POST", path, json=body).json()

    def put(self, path, body):
        return self._req("PUT", path, json=body).json()

    def text(self, path):
        return self._req("GET", path).text

    def wait_ready(self, timeout=120):
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                self.c.get("/health").raise_for_status()
                return
            except Exception:
                time.sleep(1)
        raise RuntimeError("simulator not reachable")
