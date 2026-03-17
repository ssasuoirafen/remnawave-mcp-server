from __future__ import annotations

import os
from typing import Any

import httpx

DEFAULT_TIMEOUT = 30.0


class RemnawaveApiClient:
    def __init__(self) -> None:
        base_url = os.environ.get("REMNAWAVE_API_URL", "")
        username = os.environ.get("REMNAWAVE_API_USERNAME", "")
        password = os.environ.get("REMNAWAVE_API_PASSWORD", "")

        if not all([base_url, username, password]):
            raise RuntimeError(
                "Missing required env vars: REMNAWAVE_API_URL, REMNAWAVE_API_USERNAME, REMNAWAVE_API_PASSWORD"
            )

        self._base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._access_token: str | None = None
        self._http = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=DEFAULT_TIMEOUT,
            verify=False,
        )

    async def close(self) -> None:
        await self._http.aclose()

    async def _login(self) -> None:
        res = await self._http.post(
            "/api/auth/login",
            json={"username": self._username, "password": self._password},
            headers={"X-Remnawave-Client-Type": "browser"},
        )
        res.raise_for_status()
        self._access_token = res.json()["response"]["accessToken"]

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Remnawave-Client-Type": "browser",
        }
        if self._access_token:
            h["Authorization"] = f"Bearer {self._access_token}"
        return h

    async def request(
        self,
        method: str,
        path: str,
        body: Any = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        if not self._access_token:
            await self._login()

        return await self._do_request(method, path, body, params)

    async def _do_request(
        self,
        method: str,
        path: str,
        body: Any = None,
        params: dict[str, Any] | None = None,
        is_retry: bool = False,
    ) -> Any:
        clean_params = None
        if params:
            clean_params = {k: v for k, v in params.items() if v is not None}

        res = await self._http.request(
            method,
            path,
            json=body,
            params=clean_params,
            headers=self._headers(),
        )

        if res.status_code == 401 and not is_retry:
            await self._login()
            return await self._do_request(method, path, body, params, is_retry=True)

        if not res.is_success:
            detail = res.text
            try:
                detail = res.json().get("message", detail)
            except Exception:
                pass
            raise RuntimeError(f"API error {res.status_code} {method} {path}: {detail}")

        return res.json()


def format_bytes(n: int | float) -> str:
    if n == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    value = float(n)
    while value >= 1024 and i < len(units) - 1:
        value /= 1024
        i += 1
    return f"{value:.2f} {units[i]}" if i > 0 else f"{int(value)} {units[i]}"


def handle_error(e: Exception) -> str:
    return f"Error: {e}"
