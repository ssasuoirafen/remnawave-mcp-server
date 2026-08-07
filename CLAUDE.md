# Remnawave MCP Server

## Project Overview <!-- last reviewed: 2026-08-07 -->

MCP (Model Context Protocol) server for the Remnawave VPN panel API. Written in Python 3.12+ using FastMCP (`mcp[cli]`), httpx, and Pydantic 2.0+. Targets panel 3.2.x (verified live against 3.2.1 on 2026-08-07; see "3.x compatibility"). The panel no longer serves an OpenAPI spec: `/docs-json` returns the SPA HTML on 3.x (docs config was removed from env) - verify endpoint shapes empirically against the live panel or the `remnawave/backend` source at the deployed tag.

Python policy: package supports 3.12+ (see `requires-python` and `classifiers`); local development is pinned to 3.14 via `.python-version`. Keep these three in sync when bumping: bump `classifiers` whenever `.python-version` moves to a new minor; bump `requires-python` only when intentionally dropping older versions.

Used by the `xray-vpn` project (see its `.mcp.json` / `settings.json`) to manage users, nodes, hosts, stats.

## Commands

```bash
# Install dependencies
uv sync

# Run the server standalone
uv run remnawave-mcp

# Run via MCP inspector (for debugging)
npx @modelcontextprotocol/inspector uv run remnawave-mcp
```

## Environment Variables

- `REMNAWAVE_API_URL` - panel root URL (no `/api` suffix; the client prefixes `/api/...` on every request)
- `REMNAWAVE_API_USERNAME` - login username
- `REMNAWAVE_API_PASSWORD` - login password
- `REMNAWAVE_TLS_VERIFY` - optional; `false`/`0`/`no` disables TLS verification for self-signed panel certs (default: verification on)

## Architecture

**Entry point**: `src/remnawave_mcp/server.py` - creates FastMCP instance, initializes API client, registers all tool modules.

**API client**: `src/remnawave_mcp/api_client.py` - async HTTP client with bearer token auth and auto-refresh on 401. Provides `request()`, `format_bytes()`, `handle_error()`, and `RemnawaveApiError` (RuntimeError subclass with `.status_code` for tools that branch on HTTP status). `request()` returns `None` for 204/empty-body responses.

**Tool modules**: `src/remnawave_mcp/tools/` - each module exports `register(mcp, api)` that registers `@mcp.tool()` async functions. Modules: users, nodes, system, hosts, squads, subscriptions, config_profiles.

### Tool module pattern

Every tool module follows the same structure:
1. Pydantic `BaseModel` input classes with `Field` descriptions and validation
2. Private `_format_*()` functions that render API responses as markdown strings
3. `register()` function that defines and decorates async tool functions

API responses are always wrapped in `{"response": ...}` - tools unwrap with `data["response"]` before formatting. Paginated list endpoints nest further: e.g. `data["response"]["users"]` + `data["response"]["total"]` in `users.py`.

Tool annotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`) are set per tool to signal side effects to the MCP client.

All tools return `str` (markdown). Errors are caught and formatted via `handle_error()`.

## Known Quirks

- TLS verification is ON by default (the live panel cert was confirmed valid 2026-07-10); `REMNAWAVE_TLS_VERIFY=false` restores the old `verify=False` behavior for self-signed panels.
- Env vars (`REMNAWAVE_API_URL`, credentials) are validated at import - the client is constructed at module level in `server.py`, so missing vars exit at startup with a clear `Fatal: ...` message on stderr (not deferred to the first tool call).
- No logging configured - errors only surface as tool return strings via `handle_error()`.
- API client auto-refreshes bearer token on 401 with a single retry. No backoff.
- The old single-node restart upstream bug (hardcoded `forceRestart: false`) is FIXED on panel 2.8.0: `POST /api/nodes/{uuid}/actions/restart` now REQUIRES `{"forceRestart": bool}` in the body (calls without a body get 400 "Validation failed") and honors it - verified live 2026-07-10 on 2.8.0 (`xrayUptime` reset after `forceRestart=true`; not yet re-verified on 3.x). The tool sends it by default; `force_cycle=true` (disable+enable) remains as a heavier fallback.
- Enable immediately after disable races the panel's async disable pipeline - the enable returns 200 but `isDisabled` can revert to true. `restart_node force_cycle` therefore sleeps between the calls and verifies/retries the enable; keep that pattern for any future disable→enable sequence.
- `/api/system/health` returns `runtimeMetrics` (per-process Node.js metrics), not `pm2Stats` - same shape on 2.8.0 and 3.2.1. An empty metrics list is rendered with the raw response instead of a "NOT healthy" verdict - the shape has changed before and may change again.

## 3.x compatibility (verified live against 3.2.1 on 2026-08-07)

- **Users are keyed by numeric `id`** - the user `uuid` column is gone (`drop_user_uuid` DB migration). All user tools take `id`; `_format_user` prints `ID`, not UUID. `by-short-uuid`/`by-username` routes still work. PATCH `/api/users` takes `{"id": int, ...}`; renaming via PATCH is not supported by the tools (username is a lookup key only).
- `GET /api/users/by-telegram-id/{id}` and `/by-email/{email}` are REMOVED (404) → `get_user` goes straight to scanning `/api/users/stream` (capped at 10k users).
- User actions (`enable`/`disable`/`revoke`/`reset-traffic`) live at `/api/users/{id}/actions/*` and return the full user object. `DELETE /api/users/{id}` returns 204 with no body.
- `GET /api/nodes` and `GET /api/hosts` return the list DIRECTLY in `response` (no nested `{nodes: []}` wrapper). `internal-squads`/`external-squads`/`config-profiles` keep their `{<name>, total}` wrappers. Nodes still expose `versions.{xray,node}` and keep their `uuid` (plus a new `id`).
- `GET /api/bandwidth-stats/nodes` validates `start`/`end` as plain `YYYY-MM-DD` dates and 400s on ISO datetimes; the tools truncate inputs to the date part.
- `/api/subscription-settings` was reshaped: `profileTitle`/`profileUpdateInterval`/`supportLink`/`happRouting` are gone from the top level; the object now carries `customRemarks` (per-state string lists), `customResponseHeaders` (dict, incl. the Happ routing deeplink), `hwidSettings`, `responseRules`, `randomizeHosts`.
- `GET /api/keygen` returns BOTH `pubKey` and `secretKey` on 3.2.1; the tool prefers `secretKey`.

## Testing

A `tests/test_server.py` registration-count smoke test (`uv run pytest`) asserts the tool surface (count + exact names) - update it when the surface changes. Deeper behavior is verified manually via the MCP inspector (`npx @modelcontextprotocol/inspector`):

- Verify new tools appear in the tool list after registration
- Test read-only tools first (e.g., `remnawave_get_system_stats`) to confirm API connectivity
- Check input validation: Pydantic models reject malformed inputs before API call
- Verify markdown output format matches existing tools' style

## Adding a New Tool Module

1. Create `src/remnawave_mcp/tools/{module_name}.py` following existing pattern
2. Define Pydantic input models with `Field` descriptions
3. Implement `register(mcp, api)` with `@mcp.tool()` async functions
4. Import and call `{module_name}.register(mcp, api)` in `server.py`
5. Set tool annotations (`readOnlyHint`, `destructiveHint`, etc.) per tool

## Usage

Distributed via `uvx --from git+https://github.com/ssasuoirafen/remnawave-mcp-server remnawave-mcp`. See [README.md](README.md) for the full `.mcp.json` example.

## Git

- Single branch (`main`). CI (`.github/workflows/ci.yml`): `uv sync` + pytest + advisory ruff on push/PR
- ruff + pytest in the dev group (`uv sync`); registration smoke test in `tests/`. No pre-commit hooks; ruff is advisory in CI until the pre-existing source lint is cleaned

## Conventions

- Language: user-facing MCP responses in English
- Tool names are prefixed with `remnawave_` (e.g., `remnawave_list_users`)
- Build backend: hatchling
