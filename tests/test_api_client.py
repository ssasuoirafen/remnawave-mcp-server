"""Unit tests for api_client helpers (no network)."""

import os

os.environ.setdefault("REMNAWAVE_API_URL", "https://panel.test")
os.environ.setdefault("REMNAWAVE_API_USERNAME", "test")
os.environ.setdefault("REMNAWAVE_API_PASSWORD", "test")

from remnawave_mcp.api_client import (  # noqa: E402
    RemnawaveApiClient,
    RemnawaveApiError,
    format_bytes,
)


def test_api_error_carries_status_code():
    err = RemnawaveApiError(404, "API error 404 GET /api/x: not found")
    assert err.status_code == 404
    assert isinstance(err, RuntimeError)
    assert "404" in str(err)


def test_tls_verify_default_on(monkeypatch):
    monkeypatch.delenv("REMNAWAVE_TLS_VERIFY", raising=False)
    assert RemnawaveApiClient()._tls_verify is True


def test_tls_verify_env_opt_out(monkeypatch):
    monkeypatch.setenv("REMNAWAVE_TLS_VERIFY", "false")
    assert RemnawaveApiClient()._tls_verify is False


def test_format_bytes():
    assert format_bytes(0) == "0 B"
    assert format_bytes(1536) == "1.50 KB"
