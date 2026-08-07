"""Formatter unit tests against synthetic 3.x-shaped payloads (no real user data)."""

import os

os.environ.setdefault("REMNAWAVE_API_URL", "https://panel.test")
os.environ.setdefault("REMNAWAVE_API_USERNAME", "test")
os.environ.setdefault("REMNAWAVE_API_PASSWORD", "test")

from remnawave_mcp.tools.system import (  # noqa: E402
    _format_bandwidth,
    _format_health,
    _format_node_users_usage,
)

HEALTH = {
    "runtimeMetrics": [
        {
            "rss": 302505984,
            "heapUsed": 97524544,
            "heapTotal": 110354432,
            "eventLoopP99Ms": 1.354,
            "uptime": 240519.8,
            "pid": 132,
            "instanceId": "0",
            "instanceType": "api",
        },
        {
            "rss": 216526848,
            "heapUsed": 90426352,
            "heapTotal": 103014400,
            "eventLoopP99Ms": 1.264,
            "uptime": 240519.4,
            "pid": 146,
            "instanceId": "0",
            "instanceType": "scheduler",
        },
    ]
}


def test_health_reports_processes():
    out = _format_health(HEALTH)
    assert "api" in out and "scheduler" in out
    assert "NOT healthy" not in out


def test_health_empty_metrics_not_false_alarm():
    out = _format_health({"runtimeMetrics": []})
    assert "NOT healthy" not in out
    assert "shape may have changed" in out


BANDWIDTH = {
    "categories": ["2026-07-03", "2026-07-04"],
    "series": [
        {"uuid": "u1", "name": "node-a", "countryCode": "NL", "total": 3072, "data": [1024, 2048]}
    ],
    "sparklineData": [1024, 2048],
    "topNodes": [{"uuid": "u1", "name": "node-a", "countryCode": "NL", "total": 3072}],
}


def test_bandwidth_new_shape():
    out = _format_bandwidth(BANDWIDTH)
    assert "node-a" in out and "3.00 KB" in out and "```" not in out


def test_bandwidth_empty():
    assert "No bandwidth stats" in _format_bandwidth({})


NODE_USERS = {
    "categories": ["2026-07-03", "2026-07-04"],
    "sparklineData": [100, 200],
    "topUsers": [{"color": "#fff", "username": "alice", "total": 300}],
}


def test_node_users_usage():
    out = _format_node_users_usage(NODE_USERS)
    assert "alice" in out and "300" in out


from remnawave_mcp.tools.nodes import _format_node  # noqa: E402

NODE_28 = {
    "uuid": "n-1",
    "name": "node-a",
    "countryCode": "NL",
    "address": "1.2.3.4",
    "port": 2222,
    "isConnected": True,
    "versions": {"xray": "25.1.1", "node": "2.8.0"},
    "xrayUptime": 7260,
    "usersOnline": 3,
    "note": "test note",
    "system": {"info": {"cpuModel": "EPYC", "cpus": 2, "memoryTotal": 2147483648}},
    "configProfile": {
        "activeConfigProfileUuid": "cp-1",
        "activeInbounds": [{"tag": "vless-in", "type": "vless", "network": "tcp"}],
    },
}


def test_format_node_28_shape():
    out = _format_node(NODE_28)
    assert "25.1.1" in out  # versions.xray
    assert "EPYC" in out  # system.info.cpuModel
    assert "2h 1m" in out  # humanized xrayUptime
    assert "cp-1" in out  # active config profile uuid
    assert "vless-in" in out
    assert "test note" in out


from remnawave_mcp.tools.users import _find_user_via_stream, _format_user  # noqa: E402

USER_3X = {
    "id": 24,
    "shortUuid": "shrt123",
    "username": "alice",
    "status": "ACTIVE",
    "expireAt": "2027-01-01T00:00:00.000Z",
    "trafficLimitBytes": 0,
    "createdAt": "2026-06-08T05:08:43.387Z",
    "activeInternalSquads": [{"uuid": "sq-1", "name": "users"}],
    "userTraffic": {"usedTrafficBytes": 1024, "lifetimeUsedTrafficBytes": 2048},
    "subscriptionUrl": "https://sub.test/shrt123",
}


def test_format_user_3x_shape():
    out = _format_user(USER_3X)
    assert "alice" in out and "shrt123" in out
    assert "**ID**: 24" in out  # 3.x dropped user uuid; numeric id is the key
    assert "users" in out  # squad name
    assert "1.00 KB" in out


class _StubApi:
    def __init__(self, pages):
        self._pages = pages
        self.calls = 0

    async def request(self, method, path, body=None, params=None):
        page = self._pages[self.calls]
        self.calls += 1
        return {"response": page}


async def test_stream_fallback_finds_by_telegram_id():
    api = _StubApi(
        [
            {
                "users": [{"username": "a", "telegramId": None, "email": None}],
                "hasMore": True,
                "nextCursor": "c1",
            },
            {
                "users": [{"username": "b", "telegramId": 42, "email": None}],
                "hasMore": False,
                "nextCursor": None,
            },
        ]
    )
    user = await _find_user_via_stream(api, telegram_id="42")
    assert user["username"] == "b"
    assert api.calls == 2


async def test_stream_fallback_not_found():
    api = _StubApi(
        [
            {
                "users": [{"username": "a", "telegramId": 1, "email": "x@y.z"}],
                "hasMore": False,
                "nextCursor": None,
            }
        ]
    )
    assert await _find_user_via_stream(api, email="none@such.tld") is None
