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
| `remnawave_update_node` | Update node settings (address, config profile/inbounds, traffic limits, tags, note) |
| `remnawave_enable_node` | Enable node |
| `remnawave_disable_node` | Disable node |
| `remnawave_restart_node` | Restart single node (`force_cycle=true` for a reliable disable+enable cycle) |
| `remnawave_restart_all_nodes` | Restart all nodes |

> Note: the panel's single-node restart endpoint is broken upstream - it reports the event as sent, but the node-side processor hardcodes `forceRestart=false`, so XRay is not actually restarted when the config hash matches. `remnawave_restart_node` with `force_cycle=true` works around this by disabling and re-enabling the node (briefly drops its connections). `remnawave_restart_all_nodes` is unaffected (sends `forceRestart=true`).

### Hosts
| Tool | Description |
|------|-------------|
| `remnawave_list_hosts` | List all subscription hosts |
| `remnawave_get_host` | Get host details by UUID |
| `remnawave_create_host` | Create a host on a config profile inbound |
| `remnawave_update_host` | Update host properties |
| `remnawave_delete_host` | Permanently delete a host |

### Squads
| Tool | Description |
|------|-------------|
| `remnawave_list_internal_squads` | List inbound groups (with inbound UUIDs) |
| `remnawave_update_internal_squad` | Update squad name/inbounds (replaces the inbound set) |
| `remnawave_list_external_squads` | List tariff plans |

### Config Profiles
| Tool | Description |
|------|-------------|
| `remnawave_list_config_profiles` | List XRay config profiles with inbound UUIDs |
| `remnawave_get_config_profile` | Full raw XRay config JSON + inbounds + attached nodes |
| `remnawave_update_config_profile` | Replace a profile's XRay config and/or rename it |

### Subscriptions
| Tool | Description |
|------|-------------|
| `remnawave_get_subscription_settings` | View global subscription settings |

### System
| Tool | Description |
|------|-------------|
| `remnawave_get_system_stats` | User counts, traffic, server resources |
| `remnawave_get_system_health` | Panel process health (runtime metrics per process) |
| `remnawave_get_bandwidth_stats` | Per-node bandwidth over a date range |
| `remnawave_get_node_users_usage` | Per-user traffic on one node over a date range |
| `remnawave_get_node_metrics` | Real-time node metrics |
| `remnawave_get_keygen` | Node provisioning SECRET_KEY (sensitive) |

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
| `REMNAWAVE_TLS_VERIFY` | Optional. Set to `false` for panels with self-signed certificates (TLS verification is on by default) |

> Targets Remnawave panel 2.8.x and carries forward-compat guards for known 2.9.0 changes (bodyless `DELETE` responses, removal of the by-telegram-id/by-email user endpoints, the keygen `pubKey` → `secretKey` rename).

## Development

```bash
git clone https://github.com/ssasuoirafen/remnawave-mcp-server.git
cd remnawave-mcp-server
uv sync
```

## License

MIT
