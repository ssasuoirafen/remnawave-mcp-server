from __future__ import annotations

import json

from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel, Field

from ..api_client import RemnawaveApiClient, format_bytes, handle_error


def _format_health(resp: dict) -> str:
    metrics = resp.get("runtimeMetrics") or []
    if not metrics:
        # The API answered 200 - do not declare the panel dead on an unknown shape.
        return (
            "Panel responded, but no runtime metrics were returned. "
            "The /api/system/health response shape may have changed in this panel version.\n\n"
            f"Raw response:\n```json\n{json.dumps(resp, indent=2)}\n```"
        )

    lines = ["# System Health", "", f"{len(metrics)} panel process(es) reporting:", ""]
    for m in metrics:
        p99 = m.get("eventLoopP99Ms")
        p99_str = f"{p99:.2f} ms" if isinstance(p99, (int, float)) else "n/a"
        uptime = int(m.get("uptime", 0))
        lines.append(
            f"- **{m.get('instanceType', 'unknown')}** (pid {m.get('pid', '?')}): "
            f"RSS {format_bytes(m.get('rss', 0))}, "
            f"heap {format_bytes(m.get('heapUsed', 0))} / {format_bytes(m.get('heapTotal', 0))}, "
            f"event loop p99 {p99_str}, up {uptime // 3600}h {(uptime % 3600) // 60}m"
        )
    return "\n".join(lines)


def _format_bandwidth(resp: dict) -> str:
    categories = resp.get("categories") or []
    series = resp.get("series") or []
    sparkline = resp.get("sparklineData") or []
    if not series and not sparkline:
        return "No bandwidth stats available for this range."

    lines = ["# Bandwidth Stats", ""]
    if categories:
        lines.append(f"**Range**: {categories[0]} → {categories[-1]} ({len(categories)} days)")
    lines.append(f"**All nodes total**: {format_bytes(sum(sparkline))}")
    lines.append("")
    for s in series:
        lines.append(f"## {s.get('name', s.get('uuid', 'unknown'))} ({s.get('countryCode', 'XX')})")
        lines.append(f"- **Total**: {format_bytes(s.get('total', 0))}")
        daily = s.get("data") or []
        if categories and len(daily) == len(categories):
            peak = max(range(len(daily)), key=daily.__getitem__)
            lines.append(f"- **Peak day**: {categories[peak]} ({format_bytes(daily[peak])})")
        lines.append("")
    return "\n".join(lines)


def _format_node_users_usage(resp: dict) -> str:
    categories = resp.get("categories") or []
    sparkline = resp.get("sparklineData") or []
    top_users = resp.get("topUsers") or []
    if not sparkline and not top_users:
        return "No usage recorded for this node in the given range."

    lines = ["# Node Usage (per user)", ""]
    if categories:
        lines.append(f"**Range**: {categories[0]} → {categories[-1]}")
    lines.append(f"**Node total**: {format_bytes(sum(sparkline))}")
    if categories and len(sparkline) == len(categories):
        lines.append("")
        lines.append("## Daily totals")
        lines.extend(
            f"- {day}: {format_bytes(val)}"
            for day, val in zip(categories, sparkline, strict=True)
        )
    if top_users:
        lines.append("")
        lines.append(f"## Top {len(top_users)} users")
        lines.extend(
            f"- **{u.get('username', '?')}**: {format_bytes(u.get('total', 0))}" for u in top_users
        )
    return "\n".join(lines)


_DATE_DESC = "date YYYY-MM-DD (a full ISO datetime is truncated to its date part)"


class BandwidthInput(BaseModel):
    start: str = Field(..., description=f"Start {_DATE_DESC}")
    end: str = Field(..., description=f"End {_DATE_DESC}")
    top_nodes_limit: int = Field(
        default=10, ge=1, le=100, description="Max nodes in the per-node breakdown"
    )


class NodeUsersUsageInput(BaseModel):
    uuid: str = Field(..., description="Node UUID")
    start: str = Field(..., description=f"Start {_DATE_DESC}")
    end: str = Field(..., description=f"End {_DATE_DESC}")
    top_users_limit: int = Field(
        default=10, ge=1, le=100, description="Max users in the breakdown"
    )


def register(mcp: MCPServer, api: RemnawaveApiClient) -> None:

    @mcp.tool(
        name="remnawave_get_system_stats",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    )
    async def get_system_stats() -> str:
        """Get system-wide statistics: user counts by status, online stats, node count, total traffic, server CPU/memory."""
        try:
            data = await api.request("GET", "/api/system/stats")
            s = data["response"]

            users = s.get("users", {})
            status_counts = users.get("statusCounts", {})
            online = s.get("onlineStats", {})
            nodes = s.get("nodes", {})
            memory = s.get("memory", {})

            lines = [
                "# System Statistics",
                "",
                "## Users",
                f"- **Total**: {users.get('totalUsers', 0)}",
                f"- **Active**: {status_counts.get('ACTIVE', 0)}",
                f"- **Disabled**: {status_counts.get('DISABLED', 0)}",
                f"- **Limited**: {status_counts.get('LIMITED', 0)}",
                f"- **Expired**: {status_counts.get('EXPIRED', 0)}",
                "",
                "## Online",
                f"- **Now**: {online.get('onlineNow', 0)}",
                f"- **Last day**: {online.get('lastDay', 0)}",
                f"- **Last week**: {online.get('lastWeek', 0)}",
                f"- **Never online**: {online.get('neverOnline', 0)}",
                "",
                "## Infrastructure",
                f"- **Nodes online**: {nodes.get('totalOnline', 0)}",
                f"- **Lifetime traffic**: {format_bytes(int(nodes.get('totalBytesLifetime', 0)))}",
                f"- **Server memory**: {format_bytes(memory.get('used', 0))} / {format_bytes(memory.get('total', 0))}",
                f"- **Uptime**: {int(s.get('uptime', 0)) // 3600}h {(int(s.get('uptime', 0)) % 3600) // 60}m",
            ]
            return "\n".join(lines)
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="remnawave_get_system_health",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    )
    async def get_system_health() -> str:
        """Check panel health. Shows Node.js runtime metrics (RSS, heap, event loop lag,
        uptime) per panel process (api/scheduler/processor)."""
        try:
            data = await api.request("GET", "/api/system/health")
            return _format_health(data["response"])
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="remnawave_get_bandwidth_stats",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    )
    async def get_bandwidth_stats(params: BandwidthInput) -> str:
        """Get historical bandwidth for all nodes over a date range: per-node totals,
        peak days, and the fleet-wide total."""
        try:
            data = await api.request(
                "GET",
                "/api/bandwidth-stats/nodes",
                params={
                    # 3.x validates these as plain dates and rejects ISO datetimes.
                    "start": params.start[:10],
                    "end": params.end[:10],
                    "topNodesLimit": params.top_nodes_limit,
                },
            )
            return _format_bandwidth(data["response"])
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="remnawave_get_node_users_usage",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    )
    async def get_node_users_usage(params: NodeUsersUsageInput) -> str:
        """Historical per-user traffic on ONE node over a date range (daily totals + top
        users). Complements remnawave_get_bandwidth_stats (all nodes) and
        remnawave_get_node_metrics (realtime)."""
        try:
            data = await api.request(
                "GET",
                f"/api/bandwidth-stats/nodes/{params.uuid}/users",
                params={
                    "start": params.start[:10],
                    "end": params.end[:10],
                    "topUsersLimit": params.top_users_limit,
                },
            )
            return _format_node_users_usage(data["response"])
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="remnawave_get_keygen",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    )
    async def get_keygen() -> str:
        """Get the panel's node provisioning key (SECRET_KEY env for remnanode).
        SENSITIVE: anyone holding this key can connect a node to the panel. Handles both
        field names: pubKey (<=2.8.x) and secretKey (2.9.0+)."""
        try:
            data = await api.request("GET", "/api/keygen")
            resp = data["response"]
            key = resp.get("secretKey") or resp.get("pubKey")
            if not key:
                return f"Unexpected keygen response shape, keys: {sorted(resp)}"
            return (
                f"# Node SECRET_KEY\n\n```\n{key}\n```\n\n"
                "Use as the SECRET_KEY env var when provisioning a remnanode."
            )
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="remnawave_get_node_metrics",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    )
    async def get_node_metrics() -> str:
        """Get real-time metrics for all nodes: users online, traffic per inbound (upload/download)."""
        try:
            data = await api.request("GET", "/api/system/nodes/metrics")
            nodes = data["response"].get("nodes", [])

            if not nodes:
                return "No node metrics available."

            lines = ["# Node Metrics", ""]
            for n in nodes:
                lines.append(f"## {n.get('nodeName', n.get('nodeUuid', 'unknown'))}")
                lines.append(f"- **Users online**: {n.get('usersOnline', 0)}")

                for ib in n.get("inboundsStats", []):
                    tag = ib.get("tag", "unknown")
                    up = ib.get("upload", "0")
                    down = ib.get("download", "0")
                    lines.append(f"- **{tag}**: up {up}, down {down}")
                lines.append("")
            return "\n".join(lines)
        except Exception as e:
            return handle_error(e)
