"""Token cache and refresh logic for the Whoop API."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import httpx
from pydantic import BaseModel

TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
TOKEN_DIR = Path.home() / ".whoop-mcp"
TOKEN_PATH = TOKEN_DIR / "tokens.json"

# Refresh slightly before actual expiry to avoid races.
EXPIRY_SKEW_SECONDS = 60


class NotAuthenticatedError(Exception):
    """Raised when no valid tokens are available."""


class TokenSet(BaseModel):
    access_token: str
    refresh_token: str
    expires_at: int  # unix seconds
    scope: str | None = None


def load_tokens() -> TokenSet | None:
    if not TOKEN_PATH.exists():
        return None
    try:
        data = json.loads(TOKEN_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    try:
        return TokenSet.model_validate(data)
    except Exception:
        return None


def save_tokens(ts: TokenSet) -> None:
    TOKEN_DIR.mkdir(mode=0o700, exist_ok=True)
    # Write then chmod to ensure 0600.
    TOKEN_PATH.write_text(ts.model_dump_json())
    os.chmod(TOKEN_PATH, 0o600)


def _token_set_from_response(payload: dict, fallback_refresh: str | None = None) -> TokenSet:
    expires_in = int(payload.get("expires_in", 3600))
    return TokenSet(
        access_token=payload["access_token"],
        refresh_token=payload.get("refresh_token") or fallback_refresh or "",
        expires_at=int(time.time()) + expires_in,
        scope=payload.get("scope"),
    )


async def refresh(client_id: str, client_secret: str, refresh_token: str) -> TokenSet:
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        # Whoop requires scope on refresh per their docs.
        "scope": "offline",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            TOKEN_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        payload = resp.json()
    return _token_set_from_response(payload, fallback_refresh=refresh_token)


def _client_creds() -> tuple[str, str]:
    client_id = os.environ.get("WHOOP_CLIENT_ID")
    client_secret = os.environ.get("WHOOP_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise NotAuthenticatedError(
            "WHOOP_CLIENT_ID / WHOOP_CLIENT_SECRET not set. "
            "Populate .env or the environment."
        )
    return client_id, client_secret


async def get_valid_access_token() -> str:
    """Return a valid access token, refreshing if necessary."""
    ts = load_tokens()
    if ts is None:
        raise NotAuthenticatedError(
            "No cached Whoop tokens. Run `whoop-mcp-login` to authenticate."
        )

    now = int(time.time())
    if ts.expires_at - now > EXPIRY_SKEW_SECONDS:
        return ts.access_token

    client_id, client_secret = _client_creds()
    new_ts = await refresh(client_id, client_secret, ts.refresh_token)
    save_tokens(new_ts)
    return new_ts.access_token


async def force_refresh() -> str:
    """Force a refresh regardless of expiry. Used on 401 retry path."""
    ts = load_tokens()
    if ts is None:
        raise NotAuthenticatedError(
            "No cached Whoop tokens. Run `whoop-mcp-login` to authenticate."
        )
    client_id, client_secret = _client_creds()
    new_ts = await refresh(client_id, client_secret, ts.refresh_token)
    save_tokens(new_ts)
    return new_ts.access_token
