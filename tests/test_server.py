"""Registration spec: asserts the exact MCP tool surface (count + names) of the server."""

import os

# The API client is constructed at import time in server.py and reads these env
# vars in its __init__ (no network call happens there), so set dummies first.
os.environ.setdefault("REMNAWAVE_API_URL", "https://panel.test")
os.environ.setdefault("REMNAWAVE_API_USERNAME", "test")
os.environ.setdefault("REMNAWAVE_API_PASSWORD", "test")

from remnawave_mcp import server  # noqa: E402

EXPECTED_TOOL_NAMES = {
    # users (9)
    "remnawave_list_users",
    "remnawave_get_user",
    "remnawave_create_user",
    "remnawave_update_user",
    "remnawave_delete_user",
    "remnawave_enable_user",
    "remnawave_disable_user",
    "remnawave_revoke_user",
    "remnawave_reset_user_traffic",
    # nodes (7)
    "remnawave_list_nodes",
    "remnawave_get_node",
    "remnawave_update_node",
    "remnawave_enable_node",
    "remnawave_disable_node",
    "remnawave_restart_node",
    "remnawave_restart_all_nodes",
    # system (6)
    "remnawave_get_system_stats",
    "remnawave_get_system_health",
    "remnawave_get_bandwidth_stats",
    "remnawave_get_node_metrics",
    "remnawave_get_node_users_usage",
    "remnawave_get_keygen",
    # subscriptions (1)
    "remnawave_get_subscription_settings",
    # config profiles (3)
    "remnawave_list_config_profiles",
    "remnawave_get_config_profile",
    "remnawave_update_config_profile",
    # squads (3)
    "remnawave_list_internal_squads",
    "remnawave_update_internal_squad",
    "remnawave_list_external_squads",
    # hosts (5)
    "remnawave_list_hosts",
    "remnawave_get_host",
    "remnawave_create_host",
    "remnawave_update_host",
    "remnawave_delete_host",
}


async def _registered_tool_names() -> set[str]:
    # Public API on purpose: the private _tool_manager is exactly the kind of internal
    # that shifts under a major SDK bump.
    return {tool.name for tool in await server.mcp.list_tools()}


async def test_registered_tool_count():
    assert len(await _registered_tool_names()) == 34


async def test_registered_tool_names():
    assert await _registered_tool_names() == EXPECTED_TOOL_NAMES
