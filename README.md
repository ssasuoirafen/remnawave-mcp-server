# Remnawave MCP Server

MCP server for [Remnawave](https://github.com/remnawave/panel) panel API. Manage VPN users, nodes, hosts, and system stats from Claude Code or any MCP-compatible client.

## Features

- **Users** - list, create, update, delete, enable/disable, revoke, reset traffic
- **Nodes** - list, get details, enable/disable, restart
- **Hosts** - list and inspect subscription hosts
- **Squads** - list internal (inbound groups) and external (tariff plans)
- **Subscriptions** - view settings, list config profiles
- **System** - stats, health, bandwidth, real-time node metrics

## Installation

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/ssasuoirafen/remnawave-mcp-server.git
cd remnawave-mcp-server
uv sync
```

## Configuration

Set environment variables for your Remnawave panel:

| Variable | Description |
|----------|-------------|
| `REMNAWAVE_API_URL` | Panel API URL (e.g. `https://panel.example.com/api`) |
| `REMNAWAVE_API_USERNAME` | Admin username |
| `REMNAWAVE_API_PASSWORD` | Admin password |

## Usage

### Claude Code

Add to your `.claude/settings.json` or `.claude/settings.local.json`:

```json
{
  "mcpServers": {
    "remnawave": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "/path/to/remnawave-mcp-server", "remnawave-mcp-server"],
      "env": {
        "REMNAWAVE_API_URL": "https://panel.example.com/api",
        "REMNAWAVE_API_USERNAME": "admin",
        "REMNAWAVE_API_PASSWORD": "password"
      }
    }
  }
}
```

### Standalone

```bash
uv run remnawave-mcp-server
```

## Tools

### Users
| Tool | Description |
|------|-------------|
| `remnawave_list_users` | List users with pagination |
| `remnawave_get_user` | Get user by UUID, username, telegram ID, or email |
| `remnawave_create_user` | Create new user |
| `remnawave_update_user` | Update user properties |
| `remnawave_delete_user` | Permanently delete user |
| `remnawave_enable_user` | Enable disabled user |
| `remnawave_disable_user` | Disable user (suspend VPN) |
| `remnawave_revoke_user` | Revoke subscription, regenerate credentials |
| `remnawave_reset_user_traffic` | Reset traffic counter to zero |

### Nodes
| Tool | Description |
|------|-------------|
| `remnawave_list_nodes` | List all XRay nodes |
| `remnawave_get_node` | Get node details by UUID |
| `remnawave_enable_node` | Enable node |
| `remnawave_disable_node` | Disable node |
| `remnawave_restart_node` | Restart single node |
| `remnawave_restart_all_nodes` | Restart all nodes |

### Hosts
| Tool | Description |
|------|-------------|
| `remnawave_list_hosts` | List all subscription hosts |
| `remnawave_get_host` | Get host details by UUID |

### Squads
| Tool | Description |
|------|-------------|
| `remnawave_list_internal_squads` | List inbound groups |
| `remnawave_list_external_squads` | List tariff plans |

### Subscriptions
| Tool | Description |
|------|-------------|
| `remnawave_get_subscription_settings` | View global subscription settings |
| `remnawave_list_config_profiles` | List XRay config profiles |

### System
| Tool | Description |
|------|-------------|
| `remnawave_get_system_stats` | User counts, traffic, server resources |
| `remnawave_get_system_health` | Process health (CPU, memory) |
| `remnawave_get_bandwidth_stats` | Bandwidth over time range |
| `remnawave_get_node_metrics` | Real-time node metrics |

## License

MIT
