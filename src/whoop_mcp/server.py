"""FastMCP server exposing Whoop workouts, sleep, and recovery as tools."""

from __future__ import annotations

from typing import Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from .auth import NotAuthenticatedError
from .client import WhoopClient

load_dotenv()

mcp = FastMCP("whoop")


def _not_authenticated_error(err: NotAuthenticatedError) -> dict[str, Any]:
    return {
        "error": "not_authenticated",
        "message": f"{err}. Run `whoop-mcp-login` to authenticate.",
    }


async def _with_client(fn):
    try:
        async with WhoopClient() as client:
            return await fn(client)
    except NotAuthenticatedError as err:
        return _not_authenticated_error(err)


@mcp.tool()
async def list_workouts(
    start: str | None = None,
    end: str | None = None,
    limit: int = 25,
    next_token: str | None = None,
) -> dict:
    """List the user's Whoop workouts.

    Args:
        start: ISO-8601 datetime lower bound (inclusive), e.g. "2026-04-01T00:00:00Z".
        end: ISO-8601 datetime upper bound (exclusive).
        limit: Max records per page (Whoop default/max applies).
        next_token: Opaque pagination token from a previous response.
    """
    return await _with_client(
        lambda c: c.list_workouts(start=start, end=end, limit=limit, next_token=next_token)
    )


@mcp.tool()
async def get_workout(workout_id: str) -> dict:
    """Fetch a single workout by its UUID."""
    return await _with_client(lambda c: c.get_workout(workout_id))


@mcp.tool()
async def list_sleep(
    start: str | None = None,
    end: str | None = None,
    limit: int = 25,
    next_token: str | None = None,
) -> dict:
    """List the user's Whoop sleep records. `start`/`end` are ISO-8601 datetimes."""
    return await _with_client(
        lambda c: c.list_sleep(start=start, end=end, limit=limit, next_token=next_token)
    )


@mcp.tool()
async def get_sleep(sleep_id: str) -> dict:
    """Fetch a single sleep record by its UUID."""
    return await _with_client(lambda c: c.get_sleep(sleep_id))


@mcp.tool()
async def list_recovery(
    start: str | None = None,
    end: str | None = None,
    limit: int = 25,
    next_token: str | None = None,
) -> dict:
    """List the user's Whoop recovery records. `start`/`end` are ISO-8601 datetimes."""
    return await _with_client(
        lambda c: c.list_recovery(start=start, end=end, limit=limit, next_token=next_token)
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
