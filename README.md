# whoop-mcp

Personal MCP server that wraps the [Whoop API v2](https://developer.whoop.com) so an MCP client (e.g. Claude Code) can pull your workouts, sleep, and recovery data.

## Setup

### 1. Register a Whoop developer app (one-time)

1. Go to https://developer-dashboard.whoop.com and sign in with your personal Whoop account.
2. Create a new App.
3. Set **Redirect URI** to `http://localhost:8765/callback` (must match exactly).
4. Select scopes: `read:workout`, `read:sleep`, `read:recovery`, `offline`.
5. Copy the **Client ID** and **Client Secret**.

### 2. Install

```bash
cd whoop-mcp
uv venv
source .venv/bin/activate
uv pip install -e .
```

### 3. Configure

```bash
cp .env.example .env
# edit .env and fill in WHOOP_CLIENT_ID / WHOOP_CLIENT_SECRET
```

### 4. One-time login

```bash
whoop-mcp-login
```

This opens a browser to approve access, captures the OAuth callback on `localhost:8765`, and caches tokens at `~/.whoop-mcp/tokens.json` (mode `0600`). The server auto-refreshes tokens using the `offline` scope.

### 5. Wire into Claude Code

Add to `~/.claude.json` or use `claude mcp add`:

```json
{
  "mcpServers": {
    "whoop": {
      "command": "/absolute/path/to/whoop-mcp/.venv/bin/whoop-mcp"
    }
  }
}
```

Restart Claude Code. Tools will appear as:

- `mcp__whoop__list_workouts`
- `mcp__whoop__get_workout`
- `mcp__whoop__list_sleep`
- `mcp__whoop__get_sleep`
- `mcp__whoop__list_recovery`

## Tools

All list tools accept `start`, `end` (ISO-8601 datetimes), `limit`, and `next_token` (opaque pagination token). Single-item tools take a UUID.

## Verification

- `ls -l ~/.whoop-mcp/tokens.json` — should show `-rw-------`.
- Sanity check from the repo root:
  ```bash
  python -c "import asyncio; from whoop_mcp.client import WhoopClient; \
    print(asyncio.run((lambda: (lambda c: c.list_workouts(limit=1))(WhoopClient()))()))"
  ```
- To test the refresh path, edit `expires_at` in `tokens.json` to a past timestamp and re-run the sanity check.
- To test the auth-error path, move `tokens.json` aside and call a tool — you should see a structured `{"error": "not_authenticated", ...}` response.

## Notes

- Uses endpoint prefix `/developer/v2/...`. If Whoop moves to bare `/v2/...`, change `API_PREFIX` in `src/whoop_mcp/client.py`.
- v1 of this server intentionally returns raw dicts — Whoop response schemas evolve and strict Pydantic models are not worth the churn.
