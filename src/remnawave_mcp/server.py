from __future__ import annotations

import sys
from importlib.metadata import PackageNotFoundError, version

from mcp.server.mcpserver import MCPServer

from .api_client import RemnawaveApiClient
from .tools import config_profiles, hosts, nodes, squads, subscriptions, system, users

try:
    _VERSION = version("remnawave-mcp-server")
except PackageNotFoundError:  # running from a source tree without an install
    _VERSION = "0.0.0+dev"

# mcp 2.x defaults version to "" (1.x reported the SDK's own version), so set it
# explicitly or clients see a blank version in serverInfo.
mcp = MCPServer("remnawave-mcp", version=_VERSION)

try:
    api = RemnawaveApiClient()
except RuntimeError as e:
    print(f"Fatal: {e}", file=sys.stderr)
    sys.exit(1)

users.register(mcp, api)
nodes.register(mcp, api)
hosts.register(mcp, api)
system.register(mcp, api)
squads.register(mcp, api)
subscriptions.register(mcp, api)
config_profiles.register(mcp, api)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
