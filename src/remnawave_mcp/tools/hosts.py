from __future__ import annotations

from mcp.server.fastmcp import FastMCP
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
    if h.get("serverDescription"):
        lines.append(f"- **Server**: {h['serverDescription']}")
    if h.get("tag"):
        lines.append(f"- **Tag**: {h['tag']}")

    nodes = h.get("nodes", [])
    if nodes:
        lines.append(f"- **Nodes**: {', '.join(nodes)}")

    return "\n".join(lines)


class HostUuidInput(BaseModel):
    uuid: str = Field(..., description="Host UUID")


def register(mcp: FastMCP, api: RemnawaveApiClient) -> None:

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
