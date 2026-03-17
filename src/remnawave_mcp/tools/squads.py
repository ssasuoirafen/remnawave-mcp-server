from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..api_client import RemnawaveApiClient, handle_error


def register(mcp: FastMCP, api: RemnawaveApiClient) -> None:

    @mcp.tool(
        name="remnawave_list_internal_squads",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    )
    async def list_internal_squads() -> str:
        """List all internal squads (inbound groups). Shows name, user count, and inbound count."""
        try:
            data = await api.request("GET", "/api/internal-squads")
            resp = data["response"]
            squads = resp.get("internalSquads", [])
            total = resp.get("total", len(squads))

            if not squads:
                return "No internal squads found."

            lines = [f"# Internal Squads ({total})", ""]
            for s in squads:
                lines.append(f"## {s['name']}")
                lines.append(f"- **UUID**: {s['uuid']}")
                info = s.get("info", {})
                lines.append(f"- **Members**: {info.get('membersCount', 0)}")
                lines.append(f"- **Inbounds**: {info.get('inboundsCount', 0)}")
                inbounds = s.get("inbounds", [])
                if inbounds:
                    lines.append(f"- **Inbound tags**: {', '.join(ib['tag'] for ib in inbounds)}")
                lines.append("")
            return "\n".join(lines)
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="remnawave_list_external_squads",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    )
    async def list_external_squads() -> str:
        """List all external squads (tariff plans). Shows name and user count."""
        try:
            data = await api.request("GET", "/api/external-squads")
            resp = data["response"]
            squads = resp.get("externalSquads", [])
            total = resp.get("total", len(squads))

            if not squads:
                return "No external squads found."

            lines = [f"# External Squads ({total})", ""]
            for s in squads:
                lines.append(f"## {s['name']}")
                lines.append(f"- **UUID**: {s['uuid']}")
                if s.get("description"):
                    lines.append(f"- **Description**: {s['description']}")
                info = s.get("info", {})
                lines.append(f"- **Members**: {info.get('membersCount', 0)}")
                lines.append("")
            return "\n".join(lines)
        except Exception as e:
            return handle_error(e)
