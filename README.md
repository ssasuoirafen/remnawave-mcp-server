# remnawave-mcp-server

MCP server for [Remnawave](https://github.com/remnawave/panel) panel API. Manage VPN users, nodes, hosts, and system stats from Claude Code or any MCP-compatible client.

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

> Note: `remnawave_restart_node` (single node) is broken upstream - the panel reports the event as sent, but the node-side processor hardcodes `forceRestart=false`, so XRay is not actually restarted when the config hash matches. Prefer `remnawave_disable_node` + `remnawave_enable_node`, or `remnawave_restart_all_nodes` (which sends `forceRestart=true`).

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

## Configuration

### Claude Code (`.mcp.json`)

```json
{
  "mcpServers": {
    "remnawave-mcp": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/ssasuoirafen/remnawave-mcp-server", "remnawave-mcp"],
      "env": {
        "REMNAWAVE_API_URL": "https://panel.example.com",
        "REMNAWAVE_API_USERNAME": "your-username",
        "REMNAWAVE_API_PASSWORD": "your-password"
      }
    }
  }
}
```

| Variable | Description |
|----------|-------------|
| `REMNAWAVE_API_URL` | Panel root URL, no `/api` suffix - the server prefixes `/api/...` on every request (e.g. `https://panel.example.com`) |
| `REMNAWAVE_API_USERNAME` | Admin username |
| `REMNAWAVE_API_PASSWORD` | Admin password |

> Note: the panel client connects with TLS verification disabled (`verify=False`) by design, so it works with internal panels that use self-signed certificates. Make sure you trust the network path to your panel.

## Development

```bash
git clone https://github.com/ssasuoirafen/remnawave-mcp-server.git
cd remnawave-mcp-server
uv sync
```

## License

MIT
