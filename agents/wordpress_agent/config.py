# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON — all rights reserved.
"""Environment-driven configuration for WordPress.agent.

Secrets live in the environment only (WP_* prefix). On the VPS those come from
the BANKON vault rendered into a root-only env file
(/etc/wordpress-agent/wordpress-agent.env) — never in source, never committed.
The app password is HTTP Basic auth, so the base URL is required to be HTTPS
(loopback hosts excepted, for local testing): a plaintext base URL would put the
Authorization header on the wire in clear.
"""
from __future__ import annotations

from pydantic import Field, HttpUrl, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


class Settings(BaseSettings):
    """All configuration is environment-driven. No secrets in source."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="WP_",
        extra="ignore",
    )

    base_url: HttpUrl = Field(
        ...,
        description="WordPress site base URL (e.g. https://rage.pythai.net). Must be HTTPS unless loopback.",
    )

    @field_validator("base_url")
    @classmethod
    def _require_https(cls, v: HttpUrl) -> HttpUrl:
        host = (v.host or "").lower()
        if v.scheme != "https" and host not in _LOOPBACK_HOSTS:
            raise ValueError(
                f"WP_BASE_URL must use https:// (got {v.scheme}://{host}); "
                "the WordPress Application Password is sent as HTTP Basic auth and would be exposed over plaintext."
            )
        return v
    user: str = Field(
        ...,
        description="WordPress username for the agent identity.",
    )
    app_password: SecretStr = Field(
        ...,
        description="WordPress Application Password (Users -> Profile -> Application Passwords).",
    )
    timeout: float = Field(
        default=30.0,
        description="HTTP request timeout in seconds.",
        ge=1.0,
        le=300.0,
    )
    retry_count: int = Field(
        default=3,
        description="Number of retry attempts on transient failures.",
        ge=0,
        le=10,
    )
    retry_backoff: float = Field(
        default=0.5,
        description="Exponential backoff base in seconds.",
        ge=0.0,
        le=10.0,
    )
    user_agent: str = Field(
        default="mindX-WordpressAgent/0.1 (+https://mindx.pythai.net)",
        description="HTTP User-Agent header sent with every request.",
    )

    server_host: str = Field(
        default="127.0.0.1",
        description="Local IPC server bind host. Default loopback only.",
    )
    server_port: int = Field(
        default=8765,
        description="Local IPC server bind port.",
        ge=1024,
        le=65535,
    )

    @property
    def base_url_str(self) -> str:
        """Return base_url as a trimmed string without trailing slash."""
        return str(self.base_url).rstrip("/")

    @property
    def app_password_value(self) -> str:
        """Return the app password as a plain string for HTTP basic auth."""
        return self.app_password.get_secret_value()
