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
    # nodes (6)
    "remnawave_list_nodes",
    "remnawave_get_node",
    "remnawave_enable_node",
    "remnawave_disable_node",
    "remnawave_restart_node",
    "remnawave_restart_all_nodes",
    # system (4)
    "remnawave_get_system_stats",
    "remnawave_get_system_health",
    "remnawave_get_bandwidth_stats",
    "remnawave_get_node_metrics",
    # subscriptions (2)
    "remnawave_get_subscription_settings",
    "remnawave_list_config_profiles",
    # squads (2)
    "remnawave_list_internal_squads",
    "remnawave_list_external_squads",
    # hosts (2)
    "remnawave_list_hosts",
    "remnawave_get_host",
}


def _registered_tool_names() -> set[str]:
    return {tool.name for tool in server.mcp._tool_manager.list_tools()}


def test_registered_tool_count():
    assert len(_registered_tool_names()) == 25


def test_registered_tool_names():
    assert _registered_tool_names() == EXPECTED_TOOL_NAMES
