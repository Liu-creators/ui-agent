"""
Agent Configuration
"""

import os
import yaml
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AgentConfig:
    # LLM settings
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None

    # Browser settings
    headless: bool = False
    browser_timeout: int = 30000
    slow_mo: int = 0

    # Agent settings
    max_steps: int = 20
    screenshot_mode: bool = True
    dom_mode: bool = True

    # Logging
    log_level: str = "INFO"
    save_screenshots: bool = False
    screenshot_dir: str = "./screenshots"

    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Load config from environment variables."""
        return cls(
            llm_provider=os.getenv("LLM_PROVIDER", "openai"),
            llm_model=os.getenv("LLM_MODEL", "gpt-4o"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_base_url=os.getenv("OPENAI_BASE_URL") or None,
            headless=os.getenv("HEADLESS", "false").lower() == "true",
            browser_timeout=int(os.getenv("BROWSER_TIMEOUT", "30000")),
            slow_mo=int(os.getenv("SLOW_MO", "0")),
            max_steps=int(os.getenv("MAX_STEPS", "20")),
            screenshot_mode=os.getenv("SCREENSHOT_MODE", "true").lower() == "true",
            dom_mode=os.getenv("DOM_MODE", "true").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            save_screenshots=os.getenv("SAVE_SCREENSHOTS", "false").lower() == "true",
            screenshot_dir=os.getenv("SCREENSHOT_DIR", "./screenshots"),
        )

    @classmethod
    def from_file(cls, path: str, overrides: dict = None) -> "AgentConfig":
        """Load config from YAML file, falling back to env vars."""
        cfg = cls.from_env()
        if os.path.exists(path):
            with open(path, "r") as f:
                data = yaml.safe_load(f) or {}
            for k, v in data.items():
                if hasattr(cfg, k):
                    setattr(cfg, k, v)
        if overrides:
            for k, v in overrides.items():
                if hasattr(cfg, k):
                    setattr(cfg, k, v)
        return cfg
