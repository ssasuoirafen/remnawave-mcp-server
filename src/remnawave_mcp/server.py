from __future__ import annotations

import sys

from mcp.server.fastmcp import FastMCP

from .api_client import RemnawaveApiClient
from .tools import hosts, nodes, squads, subscriptions, system, users

mcp = FastMCP("remnawave_mcp")

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


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
