from __future__ import annotations

import json

from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel, Field

from ..api_client import RemnawaveApiClient, handle_error


class ConfigProfileUuidInput(BaseModel):
    uuid: str = Field(..., description="Config profile UUID")


class UpdateConfigProfileInput(BaseModel):
    uuid: str = Field(..., description="Config profile UUID")
    name: str | None = Field(default=None, description="New profile name")
    config: str | None = Field(
        default=None,
        description=(
            "Full XRay JSON config as a string. REPLACES the entire config document - "
            "fetch with remnawave_get_config_profile, edit, pass the complete result back."
        ),
    )


def register(mcp: MCPServer, api: RemnawaveApiClient) -> None:

    @mcp.tool(
        name="remnawave_list_config_profiles",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    )
    async def list_config_profiles() -> str:
        """List all XRay config profiles with their inbounds (protocol, transport, port)."""
        try:
            profiles_data = await api.request("GET", "/api/config-profiles")
            inbounds_data = await api.request("GET", "/api/config-profiles/inbounds")

            profiles_resp = profiles_data["response"]
            inbounds_resp = inbounds_data["response"]
            profiles = profiles_resp.get("configProfiles", [])
            inbounds = inbounds_resp.get("inbounds", [])
            total = profiles_resp.get("total", len(profiles))

            if not profiles:
                return "No config profiles found."

            lines = [f"# Config Profiles ({total})", ""]
            for p in profiles:
                lines.append(f"## {p['name']}")
                lines.append(f"- **UUID**: {p['uuid']}")

                profile_inbounds = [i for i in inbounds if i.get("profileUuid") == p["uuid"]]
                if profile_inbounds:
                    lines.append("- **Inbounds**:")
                    for ib in profile_inbounds:
                        network = ib.get("network") or "tcp"
                        port = ib.get("port") or "default"
                        lines.append(
                            f"  - {ib['tag']} ({ib['type']}/{network}, port {port}) [{ib['uuid']}]"
                        )
                lines.append("")
            return "\n".join(lines)
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="remnawave_get_config_profile",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    )
    async def get_config_profile(params: ConfigProfileUuidInput) -> str:
        """Get one config profile with its FULL raw XRay config JSON (inbounds/outbounds/
        routing), registered inbounds with UUIDs, and attached nodes."""
        try:
            data = await api.request("GET", f"/api/config-profiles/{params.uuid}")
            p = data["response"]
            lines = [
                f"# Config Profile: {p['name']}",
                f"- **UUID**: {p['uuid']}",
                f"- **Updated**: {p.get('updatedAt', '?')}",
            ]
            nodes = p.get("nodes") or []
            if nodes:
                lines.append(f"- **Nodes**: {', '.join(n['name'] for n in nodes)}")
            inbounds = p.get("inbounds") or []
            if inbounds:
                lines.append("- **Inbounds**:")
                for ib in inbounds:
                    network = ib.get("network") or "tcp"
                    port = ib.get("port") or "default"
                    lines.append(
                        f"  - {ib['tag']} ({ib['type']}/{network}, port {port}) [{ib['uuid']}]"
                    )
            lines += ["", "## Raw config", "```json", json.dumps(p.get("config"), indent=2), "```"]
            return "\n".join(lines)
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="remnawave_update_config_profile",
        annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": True, "openWorldHint": True},
    )
    async def update_config_profile(params: UpdateConfigProfileInput) -> str:
        """Update a config profile (MUTATES PROD: replaces the XRay config that nodes run;
        a bad config can take user traffic down). `config` overwrites the whole document.
        Nodes apply it on their next config sync/restart."""
        try:
            if params.name is None and params.config is None:
                return "Error: Provide name and/or config to update."
            body: dict = {"uuid": params.uuid}
            if params.name is not None:
                body["name"] = params.name
            if params.config is not None:
                try:
                    parsed = json.loads(params.config)
                except json.JSONDecodeError as je:
                    return f"Error: config is not valid JSON: {je}"
                if not isinstance(parsed, dict):
                    return "Error: config must be a JSON object."
                body["config"] = parsed
            data = await api.request("PATCH", "/api/config-profiles", body)
            p = data["response"]
            return (
                "Config profile updated.\n\n"
                f"- **Name**: {p['name']}\n"
                f"- **UUID**: {p['uuid']}\n"
                f"- **Updated**: {p.get('updatedAt', '?')}"
            )
        except Exception as e:
            return handle_error(e)
