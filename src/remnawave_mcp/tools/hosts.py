from __future__ import annotations

from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel, Field

from ..api_client import RemnawaveApiClient, handle_error


def _format_host(h: dict) -> str:
    status = "DISABLED" if h.get("isDisabled") else "ENABLED"
    if h.get("isHidden"):
        status += " (hidden)"

    lines = [
        f"## {h['remark']}",
        f"- **UUID**: {h['uuid']}",
        f"- **Address**: {h['address']}:{h['port']}",
        f"- **Status**: {status}",
    ]

    if h.get("sni"):
        lines.append(f"- **SNI**: {h['sni']}")
    if h.get("host"):
        lines.append(f"- **Host**: {h['host']}")
    if h.get("path"):
        lines.append(f"- **Path**: {h['path']}")
    if h.get("alpn"):
        lines.append(f"- **ALPN**: {h['alpn']}")
    if h.get("fingerprint"):
        lines.append(f"- **Fingerprint**: {h['fingerprint']}")
    lines.append(f"- **Security**: {h.get('securityLayer', 'DEFAULT')}")

    inbound = h.get("inbound") or {}
    if inbound:
        lines.append(
            f"- **Inbound**: {inbound.get('configProfileInboundUuid', '?')} "
            f"(profile {inbound.get('configProfileUuid', '?')})"
        )
    if h.get("serverDescription"):
        lines.append(f"- **Server**: {h['serverDescription']}")
    if h.get("tag"):
        lines.append(f"- **Tag**: {h['tag']}")

    nodes = h.get("nodes", [])
    if nodes:
        parts = [
            (n.get("name") or n.get("uuid") or "?") if isinstance(n, dict) else str(n)
            for n in nodes
        ]
        lines.append(f"- **Nodes**: {', '.join(parts)}")

    return "\n".join(lines)


class HostUuidInput(BaseModel):
    uuid: str = Field(..., description="Host UUID")


class CreateHostInput(BaseModel):
    remark: str = Field(..., description="Host name shown in subscription apps")
    address: str = Field(..., description="Address (domain or IP) clients connect to")
    port: int = Field(..., ge=1, le=65535, description="Port clients connect to")
    config_profile_uuid: str = Field(..., description="Config profile UUID")
    config_profile_inbound_uuid: str = Field(
        ..., description="Inbound UUID within that profile (see remnawave_list_config_profiles)"
    )
    sni: str | None = Field(default=None, description="TLS SNI")
    host: str | None = Field(default=None, description="HTTP Host header")
    path: str | None = Field(default=None, description="WebSocket/xhttp path")
    alpn: str | None = Field(
        default=None,
        description="ALPN: h3, h2, http/1.1, h2,http/1.1, h3,h2,http/1.1, or h3,h2",
    )
    fingerprint: str | None = Field(default=None, description="uTLS fingerprint (e.g. chrome)")
    security_layer: str | None = Field(default=None, description="DEFAULT, TLS, or NONE")
    is_disabled: bool = Field(default=False, description="Create disabled")
    is_hidden: bool = Field(default=False, description="Hide from subscription output")
    server_description: str | None = Field(default=None, description="Internal description")
    tags: list[str] | None = Field(default=None, description="Host tags")
    nodes: list[str] | None = Field(default=None, description="Node UUIDs this host is limited to")


class UpdateHostInput(BaseModel):
    uuid: str = Field(..., description="Host UUID")
    remark: str | None = Field(default=None, description="Host name shown in subscription apps")
    address: str | None = Field(default=None, description="Address clients connect to")
    port: int | None = Field(default=None, ge=1, le=65535, description="Port clients connect to")
    config_profile_uuid: str | None = Field(
        default=None, description="Config profile UUID (set together with config_profile_inbound_uuid)"
    )
    config_profile_inbound_uuid: str | None = Field(
        default=None, description="Inbound UUID (set together with config_profile_uuid)"
    )
    sni: str | None = Field(default=None, description="TLS SNI")
    host: str | None = Field(default=None, description="HTTP Host header")
    path: str | None = Field(default=None, description="WebSocket/xhttp path")
    alpn: str | None = Field(default=None, description="ALPN value")
    fingerprint: str | None = Field(default=None, description="uTLS fingerprint")
    security_layer: str | None = Field(default=None, description="DEFAULT, TLS, or NONE")
    is_disabled: bool | None = Field(default=None, description="Disable/enable the host")
    is_hidden: bool | None = Field(default=None, description="Hide/show in subscription output")
    server_description: str | None = Field(default=None, description="Internal description")
    tags: list[str] | None = Field(default=None, description="Host tags (replaces set)")
    nodes: list[str] | None = Field(default=None, description="Node UUIDs (replaces set)")


def _optional_host_fields(params: CreateHostInput | UpdateHostInput) -> dict:
    body: dict = {}
    for key, value in (
        ("sni", params.sni),
        ("host", params.host),
        ("path", params.path),
        ("alpn", params.alpn),
        ("fingerprint", params.fingerprint),
        ("securityLayer", params.security_layer),
        ("serverDescription", params.server_description),
        ("tags", params.tags),
        ("nodes", params.nodes),
    ):
        if value is not None:
            body[key] = value
    return body


def register(mcp: MCPServer, api: RemnawaveApiClient) -> None:

    @mcp.tool(
        name="remnawave_list_hosts",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    )
    async def list_hosts() -> str:
        """List all subscription hosts with addresses, SNI, security settings, and assigned nodes."""
        try:
            data = await api.request("GET", "/api/hosts")
            hosts = data["response"]

            if not hosts:
                return "No hosts found."

            lines = [f"# Hosts ({len(hosts)})", ""]
            for h in hosts:
                lines.append(_format_host(h))
                lines.append("")
            return "\n".join(lines)
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="remnawave_get_host",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    )
    async def get_host(params: HostUuidInput) -> str:
        """Get detailed info about a single host by UUID."""
        try:
            data = await api.request("GET", f"/api/hosts/{params.uuid}")
            return _format_host(data["response"])
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="remnawave_create_host",
        annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": True},
    )
    async def create_host(params: CreateHostInput) -> str:
        """Create a subscription host (MUTATES PROD: enabled hosts appear in user
        subscriptions immediately). Requires the config profile + inbound pair the host
        points at (UUIDs via remnawave_list_config_profiles)."""
        try:
            body: dict = {
                "inbound": {
                    "configProfileUuid": params.config_profile_uuid,
                    "configProfileInboundUuid": params.config_profile_inbound_uuid,
                },
                "remark": params.remark,
                "address": params.address,
                "port": params.port,
                "isDisabled": params.is_disabled,
                "isHidden": params.is_hidden,
            }
            body.update(_optional_host_fields(params))
            data = await api.request("POST", "/api/hosts", body)
            return f"Host created.\n\n{_format_host(data['response'])}"
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="remnawave_update_host",
        annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    )
    async def update_host(params: UpdateHostInput) -> str:
        """Update a host (MUTATES PROD: changes flow into user subscriptions). Only
        provided fields change; tags/nodes replace their whole set."""
        try:
            if (params.config_profile_uuid is None) != (params.config_profile_inbound_uuid is None):
                return (
                    "Error: config_profile_uuid and config_profile_inbound_uuid "
                    "must be provided together."
                )
            body: dict = {"uuid": params.uuid}
            if params.config_profile_uuid is not None:
                body["inbound"] = {
                    "configProfileUuid": params.config_profile_uuid,
                    "configProfileInboundUuid": params.config_profile_inbound_uuid,
                }
            if params.remark is not None:
                body["remark"] = params.remark
            if params.address is not None:
                body["address"] = params.address
            if params.port is not None:
                body["port"] = params.port
            if params.is_disabled is not None:
                body["isDisabled"] = params.is_disabled
            if params.is_hidden is not None:
                body["isHidden"] = params.is_hidden
            body.update(_optional_host_fields(params))
            data = await api.request("PATCH", "/api/hosts", body)
            return f"Host updated.\n\n{_format_host(data['response'])}"
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="remnawave_delete_host",
        annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": True},
    )
    async def delete_host(params: HostUuidInput) -> str:
        """Permanently delete a host (MUTATES PROD: it disappears from user
        subscriptions). Cannot be undone."""
        try:
            data = await api.request("DELETE", f"/api/hosts/{params.uuid}")
            if data is None or data.get("response", {}).get("isDeleted"):
                return f"Host {params.uuid} deleted."
            return f"Failed to delete host {params.uuid}."
        except Exception as e:
            return handle_error(e)
