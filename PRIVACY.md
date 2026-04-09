# whoop-mcp privacy policy

whoop-mcp is a personal, single-user tool. It is operated solely by the
repository owner for their own Whoop account. It is not a hosted service
and has no other users.

## Data accessed

Workouts, sleep, and recovery data from the authenticated user's own Whoop
account, retrieved via the Whoop API v2 under the scopes `read:workout`,
`read:sleep`, `read:recovery`, and `offline`.

## Storage

OAuth access and refresh tokens are cached locally at
`~/.whoop-mcp/tokens.json` with `0600` file permissions inside a `0700`
directory. No Whoop workout, sleep, or recovery data is persisted to disk
by this tool — responses are held only in memory for the duration of a
single request.

## Transmission

Whoop data is transmitted only between Whoop's servers
(`api.prod.whoop.com`) and the local machine running this tool, over HTTPS.
No data is sent to any third party, analytics provider, logging service, or
external integration.

## Sharing

None. There are no analytics, telemetry, remote logging, or external
integrations of any kind.

## Retention

Tokens persist locally until the user deletes `~/.whoop-mcp/tokens.json`
or revokes access in the Whoop developer dashboard. There is no remote
copy of any data.

## Contact

https://github.com/sgee107
