from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from ..api_client import RemnawaveApiClient, format_bytes, handle_error


def _format_user(u: dict) -> str:
    lines = [
        f"## {u['username']} ({u['shortUuid']})",
        f"- **UUID**: {u['uuid']}",
        f"- **Status**: {u['status']}",
        f"- **Expires**: {u['expireAt']}",
    ]

    limit = u.get("trafficLimitBytes", 0)
    if limit and limit > 0:
        lines.append(f"- **Traffic limit**: {format_bytes(limit)} ({u.get('trafficLimitStrategy', 'NO_RESET')})")
    else:
        lines.append("- **Traffic limit**: unlimited")

    traffic = u.get("userTraffic", {})
    lines.append(f"- **Used traffic**: {format_bytes(traffic.get('usedTrafficBytes', 0))}")
    lines.append(f"- **Lifetime traffic**: {format_bytes(traffic.get('lifetimeUsedTrafficBytes', 0))}")

    if traffic.get("onlineAt"):
        lines.append(f"- **Last online**: {traffic['onlineAt']}")

    if u.get("tag"):
        lines.append(f"- **Tag**: {u['tag']}")
    if u.get("telegramId"):
        lines.append(f"- **Telegram ID**: {u['telegramId']}")
    if u.get("email"):
        lines.append(f"- **Email**: {u['email']}")
    if u.get("description"):
        lines.append(f"- **Description**: {u['description']}")

    squads = u.get("activeInternalSquads", [])
    if squads:
        lines.append(f"- **Squads**: {', '.join(s['name'] for s in squads)}")

    if u.get("subscriptionUrl"):
        lines.append(f"- **Subscription URL**: {u['subscriptionUrl']}")
    lines.append(f"- **Created**: {u['createdAt']}")

    return "\n".join(lines)


class ListUsersInput(BaseModel):
    start: int = Field(default=0, description="Pagination offset", ge=0)
    size: int = Field(default=50, description="Page size", ge=1, le=100)


class GetUserInput(BaseModel):
    uuid: Optional[str] = Field(default=None, description="User UUID")
    short_uuid: Optional[str] = Field(default=None, description="User short UUID")
    username: Optional[str] = Field(default=None, description="Username")
    telegram_id: Optional[str] = Field(default=None, description="Telegram user ID")
    email: Optional[str] = Field(default=None, description="User email")


class CreateUserInput(BaseModel):
    username: str = Field(..., description="Unique username (3-36 chars)", min_length=3, max_length=36, pattern=r"^[a-zA-Z0-9_-]+$")
    expire_at: str = Field(..., description="Expiration date in ISO 8601 (e.g. 2025-12-31T23:59:59.000Z)")
    status: Optional[str] = Field(default=None, description="Initial status: ACTIVE or DISABLED")
    traffic_limit_bytes: Optional[int] = Field(default=None, description="Traffic limit in bytes, 0 = unlimited", ge=0)
    traffic_limit_strategy: Optional[str] = Field(default=None, description="Reset period: NO_RESET, DAY, WEEK, MONTH")
    description: Optional[str] = Field(default=None, description="User description")
    tag: Optional[str] = Field(default=None, description="Tag (uppercase, max 16 chars)", max_length=16, pattern=r"^[A-Z0-9_]+$")
    telegram_id: Optional[int] = Field(default=None, description="Telegram user ID")
    email: Optional[str] = Field(default=None, description="User email")
    hwid_device_limit: Optional[int] = Field(default=None, description="Max allowed devices", ge=0)
    active_internal_squads: Optional[list[str]] = Field(default=None, description="Internal squad UUIDs")


class UpdateUserInput(BaseModel):
    uuid: Optional[str] = Field(default=None, description="User UUID (preferred)")
    username: Optional[str] = Field(default=None, description="Username (identifier if no uuid)")
    status: Optional[str] = Field(default=None, description="ACTIVE or DISABLED")
    expire_at: Optional[str] = Field(default=None, description="New expiration date (ISO 8601)")
    traffic_limit_bytes: Optional[int] = Field(default=None, description="Traffic limit in bytes", ge=0)
    traffic_limit_strategy: Optional[str] = Field(default=None, description="Reset period: NO_RESET, DAY, WEEK, MONTH")
    description: Optional[str] = Field(default=None, description="Description (empty string to clear)")
    tag: Optional[str] = Field(default=None, description="Tag (empty string to clear)")
    telegram_id: Optional[int] = Field(default=None, description="Telegram ID")
    email: Optional[str] = Field(default=None, description="Email")
    hwid_device_limit: Optional[int] = Field(default=None, description="Device limit", ge=0)
    active_internal_squads: Optional[list[str]] = Field(default=None, description="Internal squad UUIDs")


class UserUuidInput(BaseModel):
    uuid: str = Field(..., description="UUID of the user")


def register(mcp: FastMCP, api: RemnawaveApiClient) -> None:

    @mcp.tool(
        name="remnawave_list_users",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    )
    async def list_users(params: ListUsersInput) -> str:
        """List all VPN users with pagination. Returns username, status, traffic usage, expiration date, and squads."""
        try:
            data = await api.request("GET", "/api/users", params={"start": params.start, "size": params.size})
            users = data["response"]["users"]
            total = data["response"]["total"]

            if not users:
                return "No users found."

            lines = [f"# Users ({len(users)} of {total})", ""]
            for u in users:
                lines.append(_format_user(u))
                lines.append("")

            if total > params.start + len(users):
                lines.append(f"*Use start={params.start + params.size} to see more*")

            return "\n".join(lines)
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="remnawave_get_user",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    )
    async def get_user(params: GetUserInput) -> str:
        """Get a single user by UUID, shortUuid, username, telegram ID, or email. Specify exactly one identifier."""
        try:
            if params.uuid:
                path = f"/api/users/{params.uuid}"
            elif params.short_uuid:
                path = f"/api/users/by-short-uuid/{params.short_uuid}"
            elif params.username:
                path = f"/api/users/by-username/{params.username}"
            elif params.telegram_id:
                path = f"/api/users/by-telegram-id/{params.telegram_id}"
            elif params.email:
                path = f"/api/users/by-email/{params.email}"
            else:
                return "Error: Provide at least one identifier (uuid, short_uuid, username, telegram_id, or email)."

            data = await api.request("GET", path)
            return _format_user(data["response"])
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="remnawave_create_user",
        annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": True},
    )
    async def create_user(params: CreateUserInput) -> str:
        """Create a new VPN user. Requires username and expiration date. Returns created user details including subscription URL."""
        try:
            body: dict = {"username": params.username, "expireAt": params.expire_at}
            if params.status:
                body["status"] = params.status
            if params.traffic_limit_bytes is not None:
                body["trafficLimitBytes"] = params.traffic_limit_bytes
            if params.traffic_limit_strategy:
                body["trafficLimitStrategy"] = params.traffic_limit_strategy
            if params.description:
                body["description"] = params.description
            if params.tag:
                body["tag"] = params.tag
            if params.telegram_id is not None:
                body["telegramId"] = params.telegram_id
            if params.email:
                body["email"] = params.email
            if params.hwid_device_limit is not None:
                body["hwidDeviceLimit"] = params.hwid_device_limit
            if params.active_internal_squads:
                body["activeInternalSquads"] = params.active_internal_squads

            data = await api.request("POST", "/api/users", body)
            return f"User created successfully.\n\n{_format_user(data['response'])}"
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="remnawave_update_user",
        annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    )
    async def update_user(params: UpdateUserInput) -> str:
        """Update an existing user. Identify by UUID (preferred) or username. Only provided fields will be changed."""
        try:
            if not params.uuid and not params.username:
                return "Error: Provide uuid or username to identify the user."

            body: dict = {}
            if params.uuid:
                body["uuid"] = params.uuid
            if params.username is not None:
                body["username"] = params.username
            if params.status:
                body["status"] = params.status
            if params.expire_at:
                body["expireAt"] = params.expire_at
            if params.traffic_limit_bytes is not None:
                body["trafficLimitBytes"] = params.traffic_limit_bytes
            if params.traffic_limit_strategy:
                body["trafficLimitStrategy"] = params.traffic_limit_strategy
            if params.description is not None:
                body["description"] = params.description or None
            if params.tag is not None:
                body["tag"] = params.tag or None
            if params.telegram_id is not None:
                body["telegramId"] = params.telegram_id
            if params.email is not None:
                body["email"] = params.email or None
            if params.hwid_device_limit is not None:
                body["hwidDeviceLimit"] = params.hwid_device_limit
            if params.active_internal_squads is not None:
                body["activeInternalSquads"] = params.active_internal_squads

            data = await api.request("PATCH", "/api/users", body)
            return f"User updated successfully.\n\n{_format_user(data['response'])}"
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="remnawave_delete_user",
        annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": True},
    )
    async def delete_user(params: UserUuidInput) -> str:
        """Permanently delete a user by UUID. This action cannot be undone."""
        try:
            data = await api.request("DELETE", f"/api/users/{params.uuid}")
            if data["response"]["isDeleted"]:
                return f"User {params.uuid} deleted."
            return f"Failed to delete user {params.uuid}."
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="remnawave_enable_user",
        annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    )
    async def enable_user(params: UserUuidInput) -> str:
        """Enable a disabled user account, restoring VPN access."""
        try:
            data = await api.request("POST", f"/api/users/{params.uuid}/actions/enable")
            return f"User enabled.\n\n{_format_user(data['response'])}"
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="remnawave_disable_user",
        annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    )
    async def disable_user(params: UserUuidInput) -> str:
        """Disable a user account, suspending VPN access. Can be re-enabled later."""
        try:
            data = await api.request("POST", f"/api/users/{params.uuid}/actions/disable")
            return f"User disabled.\n\n{_format_user(data['response'])}"
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="remnawave_revoke_user",
        annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": True},
    )
    async def revoke_user(params: UserUuidInput) -> str:
        """Revoke a user's subscription, regenerating their credentials. Old subscription links stop working."""
        try:
            data = await api.request("POST", f"/api/users/{params.uuid}/actions/revoke")
            return f"User subscription revoked.\n\n{_format_user(data['response'])}"
        except Exception as e:
            return handle_error(e)

    @mcp.tool(
        name="remnawave_reset_user_traffic",
        annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    )
    async def reset_user_traffic(params: UserUuidInput) -> str:
        """Reset a user's traffic counter to zero."""
        try:
            data = await api.request("POST", f"/api/users/{params.uuid}/actions/reset-traffic")
            return f"Traffic reset.\n\n{_format_user(data['response'])}"
        except Exception as e:
            return handle_error(e)
