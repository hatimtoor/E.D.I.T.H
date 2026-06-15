"""Configuration loading and the runtime permission matrix.

Config precedence (low -> high): defaults -> config/edith.yaml -> environment variables.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv optional
    pass


# ── Permission matrix ───────────────────────────────────────────────
# Explicit per-capability levels (fixes OpenClaw's "wide permissions -> unauthorized
# actions" grievance). Mirrors Hermes' 5-level control idea but enforced in code.
class PermissionLevel:
    READ_ONLY = 0      # may read, never mutate
    SUGGEST = 1        # may propose actions, requires confirmation
    SANDBOXED = 2      # may act only inside the sandbox
    HOST = 3           # may act on the host (file writes, shell)
    AUTONOMOUS = 4     # unconditional autonomy (use with care)


class BrowserConfig(BaseModel):
    headless: bool = True
    engine: str = "patchright"            # patchright | playwright | camoufox
    proxy: str | None = None
    proxy_pool: list[str] = Field(default_factory=list)
    captcha_key: str | None = None
    min_action_delay_ms: int = 40
    max_action_delay_ms: int = 380
    locale: str = "en-US"
    timezone: str = "America/New_York"


class MemoryConfig(BaseModel):
    db_path: str = ".edith/memory.sqlite"
    profile: str = "default"              # namespacing fixes the "junk drawer" effect
    dedup_threshold: float = 0.92
    embed_dim: int = 256


class SecurityConfig(BaseModel):
    authorization_file: str = "config/authorization.yaml"
    require_authorization: bool = True


class RufloConfig(BaseModel):
    enabled: bool = True
    default_topology: str = "hierarchical"


class Config(BaseModel):
    home: str = ".edith"
    model: str = "anthropic:claude-opus-4-8"
    permission_level: int = PermissionLevel.SANDBOXED
    log_level: str = "INFO"
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    ruflo: RufloConfig = Field(default_factory=RufloConfig)

    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    openrouter_api_key: str | None = None

    @property
    def home_path(self) -> Path:
        return Path(self.home)

    def ensure_home(self) -> Path:
        p = Path(self.home)
        p.mkdir(parents=True, exist_ok=True)
        return p


def _deep_merge(base: dict[str, Any], over: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: str | os.PathLike[str] | None = None) -> Config:
    """Load config from yaml then overlay environment variables."""
    data: dict[str, Any] = {}
    cfg_path = Path(path) if path else Path("config/edith.yaml")
    if cfg_path.exists():
        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}

    cfg = Config(**data)

    cfg.home = os.getenv("EDITH_HOME", cfg.home)
    cfg.model = os.getenv("EDITH_MODEL", cfg.model)
    cfg.log_level = os.getenv("EDITH_LOG_LEVEL", cfg.log_level)
    cfg.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    cfg.openai_api_key = os.getenv("OPENAI_API_KEY")
    cfg.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")

    if proxy := os.getenv("EDITH_PROXY"):
        cfg.browser.proxy = proxy
    if pool := os.getenv("EDITH_PROXY_POOL"):
        cfg.browser.proxy_pool = [p.strip() for p in pool.split(",") if p.strip()]
    if cap := os.getenv("EDITH_CAPTCHA_KEY"):
        cfg.browser.captcha_key = cap
    if ruflo := os.getenv("EDITH_RUFLO_ENABLED"):
        cfg.ruflo.enabled = ruflo.lower() in ("1", "true", "yes", "on")

    return cfg
