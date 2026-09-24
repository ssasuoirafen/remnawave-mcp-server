from __future__ import annotations

from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel, Field

from ..api_client import RemnawaveApiClient, handle_error


class UpdateInternalSquadInput(BaseModel):
    uuid: str = Field(..., description="Internal squad UUID")
    name: str | None = Field(default=None, description="New squad name")
    inbounds: list[str] | None = Field(
        default=None,
        description=(
            "Inbound UUIDs. REPLACES the squad's entire inbound set - include every "
            "inbound the squad should keep (current UUIDs: remnawave_list_internal_squads)."
        ),
    )


def register(mcp: MCPServer, api: RemnawaveApiClient) -> None:

    @mcp.tool(
        name="remnawave_list_internal_squads",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    )
    async def list_internal_squads() -> str:
        """List all internal squads (inbound groups): squad UUID, name, member count, and
        each inbound's tag and UUID. Squad UUIDs are what active_internal_squads in
        remnawave_create_user / remnawave_update_user take; inbound UUIDs feed
        remnawave_update_internal_squad."""
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
                    lines.append("- **Inbounds**:")
                    lines.extend(f"  - {ib['tag']} [{ib['uuid']}]" for ib in inbounds)
                lines.append("")
            return "\n".join(lines)
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="remnawave_update_internal_squad",
        annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    )
    async def update_internal_squad(params: UpdateInternalSquadInput) -> str:
        """Update an internal squad (MUTATES PROD: changes which inbounds its members
        get). `inbounds` replaces the full set."""
        try:
            if params.name is None and params.inbounds is None:
                return "Error: Provide name and/or inbounds to update."
            body: dict = {"uuid": params.uuid}
            if params.name is not None:
                body["name"] = params.name
            if params.inbounds is not None:
                body["inbounds"] = params.inbounds
            data = await api.request("PATCH", "/api/internal-squads", body)
            s = data["response"]
            info = s.get("info", {})
            lines = [
                "Internal squad updated.",
                "",
                f"## {s['name']}",
                f"- **UUID**: {s['uuid']}",
                f"- **Members**: {info.get('membersCount', 0)}",
                f"- **Inbounds**: {info.get('inboundsCount', 0)}",
            ]
            inbounds = s.get("inbounds", [])
            if inbounds:
                lines.append("- **Inbound tags**: " + ", ".join(ib["tag"] for ib in inbounds))
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
