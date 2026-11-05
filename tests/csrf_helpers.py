"""CSRF-aware test client wrapper (security audit 2026-11-03).

Every POST now needs the X-CSRF-Token header. Rather than editing all
124 client.post call sites, fixtures wrap the Flask test client: the
wrapper fetches /api/csrf-token on first use, injects the header, and
re-fetches + retries once on a CSRF 403 (e.g. after logout rotated
the session). Raw clients are still available for tests that must
prove CSRF enforcement itself (see test_security.py).
"""

import pytest  # noqa: F401  (keeps pytest's import mode happy)


class CsrfClient:
    def __init__(self, client):
        self._c = client
        self._token = None

    def _token_for(self):
        if self._token is None:
            r = self._c.get("/api/csrf-token")
            self._token = r.get_json()["token"]
        return self._token

    def post(self, path, **kw):
        headers = dict(kw.pop("headers", None) or {})
        if "X-CSRF-Token" not in headers:
            headers["X-CSRF-Token"] = self._token_for()
        r = self._c.post(path, headers=headers, **kw)
        if r.status_code == 403:
            try:
                is_csrf = r.get_json().get("error", "").startswith("CSRF")
            except Exception:
                is_csrf = False
            if is_csrf:
                self._token = None
                headers["X-CSRF-Token"] = self._token_for()
                r = self._c.post(path, headers=headers, **kw)
        return r

    def get(self, *args, **kw):
        return self._c.get(*args, **kw)

    def __getattr__(self, name):
        return getattr(self._c, name)


def wrap(client):
    return CsrfClient(client)
