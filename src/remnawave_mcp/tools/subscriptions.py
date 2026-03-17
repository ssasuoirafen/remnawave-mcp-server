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
                        lines.append(f"  - {ib['tag']} ({ib['type']}/{network}, port {port}) [{ib['uuid']}]")
                lines.append("")
            return "\n".join(lines)
        except Exception as e:
            return handle_error(e)
