"""Async HTTP client for the Whoop developer API (v2)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from . import auth
from .auth import NotAuthenticatedError

BASE_URL = "https://api.prod.whoop.com"
API_PREFIX = "/developer/v2"


def _iso(value: str | datetime | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return value


class WhoopClient:
    """Minimal async wrapper over the Whoop v2 data endpoints."""

    def __init__(self) -> None:
        self._http = httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> "WhoopClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.aclose()

    async def _request(
        self, method: str, path: str, *, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        token = await auth.get_valid_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        clean_params = (
            {k: v for k, v in params.items() if v is not None} if params else None
        )

        resp = await self._http.request(
            method, path, params=clean_params, headers=headers
        )

        if resp.status_code == 401:
            # Force-refresh once and retry.
            token = await auth.force_refresh()
            headers["Authorization"] = f"Bearer {token}"
            resp = await self._http.request(
                method, path, params=clean_params, headers=headers
            )
            if resp.status_code == 401:
                raise NotAuthenticatedError(
                    "Whoop API returned 401 after token refresh. "
                    "Run `whoop-mcp-login` to re-authenticate."
                )

        resp.raise_for_status()
        if not resp.content:
            return {}
        return resp.json()

    # ---- Workouts ---------------------------------------------------------

    async def list_workouts(
        self,
        start: str | datetime | None = None,
        end: str | datetime | None = None,
        limit: int = 25,
        next_token: str | None = None,
    ) -> dict[str, Any]:
        params = {
            "start": _iso(start),
            "end": _iso(end),
            "limit": limit,
            "nextToken": next_token,
        }
        return await self._request("GET", f"{API_PREFIX}/activity/workout", params=params)

    async def get_workout(self, workout_id: str) -> dict[str, Any]:
        return await self._request("GET", f"{API_PREFIX}/activity/workout/{workout_id}")

    # ---- Sleep ------------------------------------------------------------

    async def list_sleep(
        self,
        start: str | datetime | None = None,
        end: str | datetime | None = None,
        limit: int = 25,
        next_token: str | None = None,
    ) -> dict[str, Any]:
        params = {
            "start": _iso(start),
            "end": _iso(end),
            "limit": limit,
            "nextToken": next_token,
        }
        return await self._request("GET", f"{API_PREFIX}/activity/sleep", params=params)

    async def get_sleep(self, sleep_id: str) -> dict[str, Any]:
        return await self._request("GET", f"{API_PREFIX}/activity/sleep/{sleep_id}")

    # ---- Recovery ---------------------------------------------------------

    async def list_recovery(
        self,
        start: str | datetime | None = None,
        end: str | datetime | None = None,
        limit: int = 25,
        next_token: str | None = None,
    ) -> dict[str, Any]:
        params = {
            "start": _iso(start),
            "end": _iso(end),
            "limit": limit,
            "nextToken": next_token,
        }
        return await self._request("GET", f"{API_PREFIX}/recovery", params=params)
