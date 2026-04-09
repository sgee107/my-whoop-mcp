"""One-time CLI OAuth login flow for the Whoop API."""

from __future__ import annotations

import os
import secrets
import sys
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import httpx
from dotenv import load_dotenv

from .auth import TOKEN_PATH, TokenSet, _token_set_from_response, save_tokens

AUTHORIZE_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
SCOPES = "read:workout read:sleep read:recovery offline"

_result: dict[str, str] = {}


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return
        params = urllib.parse.parse_qs(parsed.query)
        code = params.get("code", [None])[0]
        state = params.get("state", [None])[0]
        error = params.get("error", [None])[0]

        if error:
            _result["error"] = error
            body = f"<h1>Whoop login failed</h1><p>{error}</p>"
        elif not code:
            _result["error"] = "missing_code"
            body = "<h1>Whoop login failed</h1><p>Missing authorization code.</p>"
        else:
            _result["code"] = code
            _result["state"] = state or ""
            body = (
                "<h1>Whoop login successful</h1>"
                "<p>You can close this tab and return to the terminal.</p>"
            )

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, format, *args):  # noqa: A002
        # Silence default stderr logging.
        return


def _run_server(port: int) -> HTTPServer:
    server = HTTPServer(("127.0.0.1", port), _CallbackHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def main() -> int:
    load_dotenv()
    client_id = os.environ.get("WHOOP_CLIENT_ID")
    client_secret = os.environ.get("WHOOP_CLIENT_SECRET")
    redirect_uri = os.environ.get("WHOOP_REDIRECT_URI", "http://localhost:8765/callback")

    if not client_id or not client_secret:
        print(
            "ERROR: WHOOP_CLIENT_ID and WHOOP_CLIENT_SECRET must be set in .env or environment.",
            file=sys.stderr,
        )
        return 1

    parsed_redirect = urllib.parse.urlparse(redirect_uri)
    port = parsed_redirect.port or 8765

    state = secrets.token_urlsafe(24)
    auth_params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
        "state": state,
    }
    authorize_url = f"{AUTHORIZE_URL}?{urllib.parse.urlencode(auth_params)}"

    server = _run_server(port)
    print(f"Opening browser to authorize Whoop access...")
    print(f"If it does not open automatically, visit:\n  {authorize_url}")
    webbrowser.open(authorize_url)

    # Wait for callback.
    try:
        import time

        deadline = time.time() + 300  # 5 minutes
        while "code" not in _result and "error" not in _result:
            if time.time() > deadline:
                print("ERROR: Timed out waiting for OAuth callback.", file=sys.stderr)
                return 1
            time.sleep(0.1)
    finally:
        server.shutdown()

    if "error" in _result:
        print(f"ERROR: OAuth failed: {_result['error']}", file=sys.stderr)
        return 1

    if _result.get("state") != state:
        print("ERROR: OAuth state mismatch — possible CSRF.", file=sys.stderr)
        return 1

    code = _result["code"]

    # Exchange the code for tokens.
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    resp = httpx.post(
        TOKEN_URL,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30.0,
    )
    if resp.status_code != 200:
        print(
            f"ERROR: Token exchange failed ({resp.status_code}): {resp.text}",
            file=sys.stderr,
        )
        return 1

    ts: TokenSet = _token_set_from_response(resp.json())
    save_tokens(ts)
    print(f"Success. Tokens cached at {TOKEN_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
