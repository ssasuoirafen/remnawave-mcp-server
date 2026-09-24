from __future__ import annotations

import json

from mcp.server.mcpserver import MCPServer

from ..api_client import RemnawaveApiClient, handle_error


def _fmt_val(v: object, limit: int = 100) -> str:
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    return s[:limit] + ("..." if len(s) > limit else "")


def _format_settings(s: dict) -> str:
    lines = [
        "# Subscription Settings",
        "",
        f"- **UUID**: {s.get('uuid', '?')}",
        f"- **Serve JSON at base subscription**: {s.get('serveJsonAtBaseSubscription', False)}",
        f"- **Randomize hosts**: {s.get('randomizeHosts', False)}",
        f"- **Show custom remarks**: {s.get('isShowCustomRemarks', False)}",
    ]

    remarks = s.get("customRemarks") or {}
    if remarks:
        lines += ["", "## Custom remarks (per user state)"]
        for state, msgs in remarks.items():
            joined = " / ".join(msgs) if isinstance(msgs, list) else str(msgs)
            lines.append(f"- **{state}**: {joined}")

    headers = s.get("customResponseHeaders") or {}
    if headers:
        lines += ["", "## Custom response headers"]
        if isinstance(headers, dict):
            lines.extend(f"- **{k}**: {_fmt_val(v)}" for k, v in headers.items())
        else:
            lines.append(f"- {_fmt_val(headers)}")

    hwid = s.get("hwidSettings")
    if hwid:
        dumped = json.dumps(hwid, ensure_ascii=False, indent=2)
        lines += ["", "## HWID settings", "```json", dumped, "```"]

    rules = s.get("responseRules")
    if rules:
        count = len(rules) if isinstance(rules, list) else "?"
        lines += ["", f"## Response rules ({count})", "```json", _fmt_val(rules, 1500), "```"]

    return "\n".join(lines)


def register(mcp: MCPServer, api: RemnawaveApiClient) -> None:

    @mcp.tool(
        name="remnawave_get_subscription_settings",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    )
    async def get_subscription_settings() -> str:
        """Get global subscription settings: base-subscription behavior, per-state custom
        remarks, custom response headers (incl. the Happ routing deeplink), HWID settings,
        response rules. Long values are truncated: each header value to 100 characters and
        the response-rules JSON to 1,500, so full header values and large rule sets are not
        available from this tool."""
        try:
            data = await api.request("GET", "/api/subscription-settings")
            return _format_settings(data["response"])
        except Exception as e:
            return handle_error(e)
