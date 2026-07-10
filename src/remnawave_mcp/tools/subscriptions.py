from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ..api_client import RemnawaveApiClient, handle_error


def register(mcp: FastMCP, api: RemnawaveApiClient) -> None:

    @mcp.tool(
        name="remnawave_get_subscription_settings",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    )
    async def get_subscription_settings() -> str:
        """Get global subscription settings: profile title, update interval, support link, Happ routing, custom headers."""
        try:
            data = await api.request("GET", "/api/subscription-settings")
            s = data["response"]
            lines = [
                "# Subscription Settings",
                "",
                f"- **Profile title**: {s.get('profileTitle', 'N/A')}",
                f"- **Update interval**: {s.get('profileUpdateInterval', 'N/A')} hours",
                f"- **Support link**: {s.get('supportLink') or 'not set'}",
                f"- **JSON at base subscription**: {s.get('serveJsonAtBaseSubscription', False)}",
                f"- **Username in base subscription**: {s.get('addUsernameToBaseSubscription', False)}",
            ]

            webpage_enabled = s.get("isProfileWebpageUrlEnabled", False)
            webpage_url = s.get("profileWebpageUrl")
            lines.append(f"- **Profile webpage URL**: {webpage_url if webpage_enabled and webpage_url else 'disabled'}")

            if s.get("happRouting"):
                lines.append(f"- **Happ routing**: {s['happRouting']}")
            if s.get("happAdsTag"):
                lines.append(f"- **Happ ads tag**: {s['happAdsTag']}")

            headers = s.get("customResponseHeaders", [])
            if headers:
                lines.append(f"- **Custom headers**: {', '.join(headers)}")

            remarks = s.get("expiredUsersRemarks", [])
            if remarks:
                lines.append(f"- **Expired user remarks**: {', '.join(remarks)}")

            return "\n".join(lines)
        except Exception as e:
            return handle_error(e)
