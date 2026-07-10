from __future__ import annotations

import asyncio

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

    # 2.8.0 moved versions under versions.{xray,node}; older panels had flat fields.
    versions = n.get("versions") or {}
    xray_version = versions.get("xray") or n.get("xrayVersion")
    node_version = versions.get("node") or n.get("nodeVersion")
    if xray_version:
        lines.append(f"- **XRay**: {xray_version}")
    if node_version:
        lines.append(f"- **Node version**: {node_version}")
    if n.get("xrayUptime"):
        up = int(n["xrayUptime"])
        lines.append(f"- **XRay uptime**: {up // 3600}h {(up % 3600) // 60}m")
    if n.get("usersOnline") is not None:
        lines.append(f"- **Users online**: {n['usersOnline']}")

    if n.get("isTrafficTrackingActive") and n.get("trafficLimitBytes"):
        used = n.get("trafficUsedBytes", 0) or 0
        lines.append(
            f"- **Traffic**: {format_bytes(used)} / {format_bytes(n['trafficLimitBytes'])}"
        )

    tags = n.get("tags", [])
    if tags:
        lines.append(f"- **Tags**: {', '.join(tags)}")

    # 2.8.0 moved hardware under system.info; older panels had flat fields.
    sys_info = (n.get("system") or {}).get("info") or {}
    cpu_model = sys_info.get("cpuModel") or n.get("cpuModel")
    if cpu_model:
        cores = sys_info.get("cpus") or n.get("cpuCount", "?")
        lines.append(f"- **CPU**: {cpu_model} ({cores} cores)")
    memory_total = sys_info.get("memoryTotal") or n.get("totalRam")
    if memory_total:
        ram = format_bytes(memory_total) if isinstance(memory_total, (int, float)) else memory_total
        lines.append(f"- **RAM**: {ram}")
    if n.get("note"):
        lines.append(f"- **Note**: {n['note']}")
    if n.get("lastStatusMessage"):
        lines.append(f"- **Last status**: {n['lastStatusMessage']}")

    profile = n.get("configProfile") or {}
    if profile.get("activeConfigProfileUuid"):
        lines.append(f"- **Config profile**: {profile['activeConfigProfileUuid']}")
    inbounds = profile.get("activeInbounds") or []
    if inbounds:
        parts = [f"{i['tag']} ({i['type']}/{i.get('network') or 'tcp'})" for i in inbounds]
        lines.append(f"- **Inbounds**: {', '.join(parts)}")

    return "\n".join(lines)


class NodeUuidInput(BaseModel):
    uuid: str = Field(..., description="Node UUID")


class RestartNodeInput(BaseModel):
    uuid: str = Field(..., description="Node UUID")
    force: bool = Field(
        True,
        description=(
            "Sent as forceRestart (a required body field on panel 2.8.0+): skips the "
            "panel's config-hash check so XRay restarts even when the config is unchanged."
        ),
    )
    force_cycle: bool = Field(
        False,
        description=(
            "If true, disable then re-enable the node instead of the restart endpoint. "
            "Heavier hammer (re-establishes the panel-node connection) but briefly drops "
            "the node's active connections."
        ),
    )


class UpdateNodeInput(BaseModel):
    uuid: str = Field(..., description="Node UUID")
    name: str | None = Field(default=None, description="Node name")
    address: str | None = Field(default=None, description="Address the panel reaches the node at")
    port: int | None = Field(default=None, ge=1, le=65535, description="Node API port")
    country_code: str | None = Field(
        default=None, min_length=2, max_length=2, description="ISO country code (e.g. NL)"
    )
    config_profile_uuid: str | None = Field(
        default=None, description="Active config profile UUID (requires active_inbounds)"
    )
    active_inbounds: list[str] | None = Field(
        default=None,
        description=(
            "Inbound UUIDs from that profile to serve on this node "
            "(requires config_profile_uuid; replaces the set)"
        ),
    )
    is_traffic_tracking_active: bool | None = Field(
        default=None, description="Enable/disable traffic tracking"
    )
    traffic_limit_bytes: int | None = Field(
        default=None, ge=0, description="Traffic limit in bytes"
    )
    notify_percent: int | None = Field(
        default=None, ge=0, le=100, description="Notify at % of limit"
    )
    traffic_reset_day: int | None = Field(
        default=None, ge=1, le=31, description="Monthly traffic reset day"
    )
    consumption_multiplier: float | None = Field(
        default=None, gt=0, description="Consumption multiplier"
    )
    tags: list[str] | None = Field(default=None, description="Node tags (replaces set)")
    note: str | None = Field(default=None, description="Note (empty string clears)")


class RestartAllNodesInput(BaseModel):
    force: bool = Field(
        True,
        description="If true, panel skips its config-hash check and forces every node to restart Xray. Default true (mirrors the Remnawave UI 'Restart all' button).",
    )


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
        name="remnawave_update_node",
        annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    )
    async def update_node(params: UpdateNodeInput) -> str:
        """Update node settings (MUTATES PROD). Changing the config profile / inbounds
        re-syncs what the node serves. Only provided fields change."""
        try:
            if (params.config_profile_uuid is None) != (params.active_inbounds is None):
                return "Error: config_profile_uuid and active_inbounds must be provided together."
            body: dict = {"uuid": params.uuid}
            if params.name is not None:
                body["name"] = params.name
            if params.address is not None:
                body["address"] = params.address
            if params.port is not None:
                body["port"] = params.port
            if params.country_code is not None:
                body["countryCode"] = params.country_code.upper()
            if params.config_profile_uuid is not None:
                body["configProfile"] = {
                    "activeConfigProfileUuid": params.config_profile_uuid,
                    "activeInbounds": params.active_inbounds,
                }
            if params.is_traffic_tracking_active is not None:
                body["isTrafficTrackingActive"] = params.is_traffic_tracking_active
            if params.traffic_limit_bytes is not None:
                body["trafficLimitBytes"] = params.traffic_limit_bytes
            if params.notify_percent is not None:
                body["notifyPercent"] = params.notify_percent
            if params.traffic_reset_day is not None:
                body["trafficResetDay"] = params.traffic_reset_day
            if params.consumption_multiplier is not None:
                body["consumptionMultiplier"] = params.consumption_multiplier
            if params.tags is not None:
                body["tags"] = params.tags
            if params.note is not None:
                body["note"] = params.note or None
            data = await api.request("PATCH", "/api/nodes", body)
            return f"Node updated.\n\n{_format_node(data['response'])}"
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="remnawave_restart_node",
        annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    )
    async def restart_node(params: RestartNodeInput) -> str:
        """Restart XRay on one node (MUTATES PROD: interrupts the node briefly). Default
        mode sends forceRestart (panel 2.8.0+ requires it in the body); force=true skips
        the config-hash check like the UI's restart-all. force_cycle=true disables and
        re-enables the node instead - heavier, also re-establishes the panel-node link."""
        try:
            if params.force_cycle:
                await api.request("POST", f"/api/nodes/{params.uuid}/actions/disable")
                # The panel processes disable asynchronously; enabling immediately can be
                # reverted by the still-running disable pipeline. Settle, then verify.
                await asyncio.sleep(3)
                try:
                    await api.request("POST", f"/api/nodes/{params.uuid}/actions/enable")
                    await asyncio.sleep(2)
                    node = (await api.request("GET", f"/api/nodes/{params.uuid}"))["response"]
                    if node.get("isDisabled"):
                        await api.request("POST", f"/api/nodes/{params.uuid}/actions/enable")
                        await asyncio.sleep(2)
                        node = (await api.request("GET", f"/api/nodes/{params.uuid}"))["response"]
                except Exception as e:
                    return (
                        f"CRITICAL: node {params.uuid} was disabled but re-enable FAILED - "
                        f"the node is OFFLINE. Run remnawave_enable_node for it now. Error: {e}"
                    )
                if node.get("isDisabled"):
                    return (
                        f"CRITICAL: node {params.uuid} is still DISABLED after two enable "
                        "attempts. Run remnawave_enable_node for it now."
                    )
                return f"Node force-cycled (disable + enable).\n\n{_format_node(node)}"
            data = await api.request(
                "POST",
                f"/api/nodes/{params.uuid}/actions/restart",
                body={"forceRestart": params.force},
            )
            if data["response"].get("eventSent"):
                return (
                    f"Node {params.uuid} restart event sent "
                    f"(forceRestart={str(params.force).lower()}). "
                    "If XRay does not actually restart, re-run with force_cycle=true."
                )
            return f"Node restart response: {data['response']}"
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="remnawave_restart_all_nodes",
        annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    )
    async def restart_all_nodes(params: RestartAllNodesInput | None = None) -> str:
        """Restart XRay on ALL enabled nodes. By default sends forceRestart=true so the panel skips its config-hash check; pass force=false to use the panel's hash-based decision (which often skips the restart)."""
        try:
            force = params.force if params is not None else True
            await api.request("POST", "/api/nodes/actions/restart-all", body={"forceRestart": force})
            return f"All nodes restart event sent (forceRestart={str(force).lower()})."
        except Exception as e:
            return handle_error(e)
