# Remnawave MCP Server

## Project Overview <!-- last reviewed: 2026-04-26 -->

MCP (Model Context Protocol) server for the Remnawave VPN panel API. Written in Python 3.12+ using FastMCP (`mcp[cli]`), httpx, and Pydantic 2.0+.

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

## Architecture

**Entry point**: `src/remnawave_mcp/server.py` - creates FastMCP instance, initializes API client, registers all tool modules.

**API client**: `src/remnawave_mcp/api_client.py` - async HTTP client with bearer token auth and auto-refresh on 401. Provides `request()`, `format_bytes()`, `handle_error()`.

**Tool modules**: `src/remnawave_mcp/tools/` - each module exports `register(mcp, api)` that registers `@mcp.tool()` async functions. Modules: users, nodes, system, hosts, squads, subscriptions.

### Tool module pattern

Every tool module follows the same structure:
1. Pydantic `BaseModel` input classes with `Field` descriptions and validation
2. Private `_format_*()` functions that render API responses as markdown strings
3. `register()` function that defines and decorates async tool functions

API responses are always wrapped in `{"response": ...}` - tools unwrap with `data["response"]` before formatting. Paginated list endpoints nest further: e.g. `data["response"]["users"]` + `data["response"]["total"]` in `users.py`.

Tool annotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`) are set per tool to signal side effects to the MCP client.

All tools return `str` (markdown). Errors are caught and formatted via `handle_error()`.

## Known Quirks

- `verify=False` in `api_client.py` - SSL verification disabled for internal panel API. Don't "fix" this without confirming panel has a valid cert.
- Env vars (`REMNAWAVE_API_URL`, credentials) are validated at import - the client is constructed at module level in `server.py`, so missing vars exit at startup with a clear `Fatal: ...` message on stderr (not deferred to the first tool call).
- No logging configured - errors only surface as tool return strings via `handle_error()`.
- API client auto-refreshes bearer token on 401 with a single retry. No backoff.
- `remnawave_restart_node` (single node) is broken upstream: backend's `start-node.processor.ts` hardcodes `forceRestart: false`, so XRay is not restarted when the config hash matches. Workaround: disable+enable, or use `remnawave_restart_all_nodes` (which sends `forceRestart: true` by default). Re-check upstream periodically; remove the warning once the per-node endpoint accepts a force flag.

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
