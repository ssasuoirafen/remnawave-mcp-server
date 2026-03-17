from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from ..api_client import RemnawaveApiClient, format_bytes, handle_error


class BandwidthInput(BaseModel):
    start: str = Field(..., description="Start datetime in ISO 8601 (e.g. 2025-03-01T00:00:00.000Z)")
    end: str = Field(..., description="End datetime in ISO 8601 (e.g. 2025-03-15T23:59:59.000Z)")


def register(mcp: FastMCP, api: RemnawaveApiClient) -> None:

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
        """Check if the Remnawave panel is healthy and responding. Shows PM2 process stats (CPU, memory)."""
        try:
            data = await api.request("GET", "/api/system/health")
            processes = data["response"].get("pm2Stats", [])

            if not processes:
                return "System is NOT healthy: no PM2 processes found."

            lines = ["# System Health", "", "All processes running:", ""]
            for p in processes:
                mem_mb = int(p.get("memory", 0)) / 1024 / 1024
                cpu = p.get("cpu", "?")
                lines.append(f"- **{p['name']}**: CPU {cpu}%, Memory {mem_mb:.0f} MB")

            return "\n".join(lines)
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="remnawave_get_bandwidth_stats",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    )
    async def get_bandwidth_stats(params: BandwidthInput) -> str:
        """Get bandwidth statistics for all nodes in a time range. Requires start and end dates in ISO 8601."""
        try:
            data = await api.request(
                "GET",
                "/api/bandwidth-stats/nodes",
                params={"start": params.start, "end": params.end},
            )
            stats = data.get("response", data)

            if not stats:
                return "No bandwidth stats available."

            if isinstance(stats, list):
                lines = ["# Bandwidth Stats", ""]
                for s in stats:
                    lines.append(f"## {s.get('name', s.get('nodeName', s.get('uuid', 'unknown')))}")
                    lines.append(f"- **Total**: {format_bytes(s.get('totalBytes', 0))}")
                    lines.append(f"- **Upload**: {format_bytes(s.get('uploadBytes', 0))}")
                    lines.append(f"- **Download**: {format_bytes(s.get('downloadBytes', 0))}")
                    lines.append("")
                return "\n".join(lines)

            return f"Bandwidth stats:\n```json\n{stats}\n```"
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
