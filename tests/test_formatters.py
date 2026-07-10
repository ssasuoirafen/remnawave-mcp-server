"""Formatter unit tests against synthetic 2.8.0-shaped payloads (no real user data)."""

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
