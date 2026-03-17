from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from ..api_client import RemnawaveApiClient, format_bytes, handle_error


def _format_node(n: dict) -> str:
    if n.get("isDisabled"):
        status = "DISABLED"
    elif n.get("isConnected"):
        status = "CONNECTED"
    elif n.get("isConnecting"):
        status = "CONNECTING"
    else:
        status = "DISCONNECTED"

    lines = [
        f"## {n['name']} ({n.get('countryCode', 'XX')})",
        f"- **UUID**: {n['uuid']}",
        f"- **Status**: {status}",
        f"- **Address**: {n['address']}{':' + str(n['port']) if n.get('port') else ''}",
    ]

    if n.get("xrayVersion"):
        lines.append(f"- **XRay**: {n['xrayVersion']}")
    if n.get("nodeVersion"):
        lines.append(f"- **Node version**: {n['nodeVersion']}")
    if n.get("xrayUptime"):
        lines.append(f"- **Uptime**: {n['xrayUptime']}")
    if n.get("usersOnline") is not None:
        lines.append(f"- **Users online**: {n['usersOnline']}")

    if n.get("isTrafficTrackingActive") and n.get("trafficLimitBytes"):
        used = n.get("trafficUsedBytes", 0) or 0
        lines.append(f"- **Traffic**: {format_bytes(used)} / {format_bytes(n['trafficLimitBytes'])}")

    tags = n.get("tags", [])
    if tags:
        lines.append(f"- **Tags**: {', '.join(tags)}")
    if n.get("cpuModel"):
        lines.append(f"- **CPU**: {n['cpuModel']} ({n.get('cpuCount', '?')} cores)")
    if n.get("totalRam"):
        lines.append(f"- **RAM**: {n['totalRam']}")
    if n.get("lastStatusMessage"):
        lines.append(f"- **Last status**: {n['lastStatusMessage']}")

    inbounds = n.get("configProfile", {}).get("activeInbounds", [])
    if inbounds:
        parts = [f"{i['tag']} ({i['type']}/{i.get('network') or 'tcp'})" for i in inbounds]
        lines.append(f"- **Inbounds**: {', '.join(parts)}")

    return "\n".join(lines)


class NodeUuidInput(BaseModel):
    uuid: str = Field(..., description="Node UUID")


def register(mcp: FastMCP, api: RemnawaveApiClient) -> None:

    @mcp.tool(
        name="remnawave_list_nodes",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    )
    async def list_nodes() -> str:
        """List all XRay nodes with connection status, traffic, version info, and hardware specs."""
        try:
            data = await api.request("GET", "/api/nodes")
            nodes = data["response"]

            if not nodes:
                return "No nodes found."

            lines = [f"# Nodes ({len(nodes)})", ""]
            for n in nodes:
                lines.append(_format_node(n))
                lines.append("")
            return "\n".join(lines)
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="remnawave_get_node",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    )
    async def get_node(params: NodeUuidInput) -> str:
        """Get detailed info about a single node by UUID."""
        try:
            data = await api.request("GET", f"/api/nodes/{params.uuid}")
            return _format_node(data["response"])
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="remnawave_enable_node",
        annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    )
    async def enable_node(params: NodeUuidInput) -> str:
        """Enable a disabled node, allowing it to accept connections."""
        try:
            data = await api.request("POST", f"/api/nodes/{params.uuid}/actions/enable")
            return f"Node enabled.\n\n{_format_node(data['response'])}"
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="remnawave_disable_node",
        annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    )
    async def disable_node(params: NodeUuidInput) -> str:
        """Disable a node, stopping it from accepting new connections."""
        try:
            data = await api.request("POST", f"/api/nodes/{params.uuid}/actions/disable")
            return f"Node disabled.\n\n{_format_node(data['response'])}"
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="remnawave_restart_node",
        annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    )
    async def restart_node(params: NodeUuidInput) -> str:
        """[BROKEN] Restart XRay on a specific node. API returns eventSent=true but node ignores it. Use disable+enable as workaround."""
        try:
            data = await api.request("POST", f"/api/nodes/{params.uuid}/actions/restart")
            if data["response"].get("eventSent"):
                return f"Node {params.uuid} restart event sent (NOTE: this endpoint is broken in Remnawave - use disable+enable instead)."
            return f"Node restart response: {data['response']}"
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="remnawave_restart_all_nodes",
        annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    )
    async def restart_all_nodes() -> str:
        """[BROKEN] Restart XRay on ALL nodes. API returns eventSent=true but nodes ignore it. Use disable+enable per node as workaround."""
        try:
            await api.request("POST", "/api/nodes/actions/restart-all")
            return "All nodes restart event sent (NOTE: this endpoint is broken in Remnawave - use disable+enable per node instead)."
        except Exception as e:
            return handle_error(e)
