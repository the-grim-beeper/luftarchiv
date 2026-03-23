"""
LLM configuration for extraction.

Supports three providers:
- claude: Anthropic Claude API (default)
- ollama: Local Ollama instance
- none: Skip LLM extraction (Kraken-only)

Config is stored in a JSON file alongside the database, not in the DB itself
(API keys should not be in the database).
"""

import json
from pathlib import Path
from pydantic import BaseModel

CONFIG_PATH = Path(__file__).resolve().parents[2] / "data" / "llm_config.json"


class LLMConfig(BaseModel):
    provider: str = "claude"  # "claude" | "ollama" | "none"
    api_key: str = ""  # Anthropic API key (for claude provider)
    ollama_url: str = "http://localhost:11434"  # Ollama API endpoint
    model_name: str = ""  # Model to use — auto-selected per provider if empty
    kraken_enabled: bool = False  # Whether to run Kraken OCR first

    @property
    def effective_model(self) -> str:
        if self.model_name:
            return self.model_name
        if self.provider == "claude":
            return "claude-sonnet-4-20250514"
        if self.provider == "ollama":
            return "llama3.2-vision"
        return ""


def load_config() -> LLMConfig:
    """Load config from disk, falling back to defaults + env vars."""
    config = LLMConfig()

    # Load from file if exists
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text())
            config = LLMConfig(**data)
        except (json.JSONDecodeError, Exception):
            pass

    # Environment variables override file config (for Docker/Railway)
    import os
    env_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if env_key and not config.api_key:
        config.api_key = env_key

    return config


def save_config(config: LLMConfig) -> None:
    """Save config to disk."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(config.model_dump_json(indent=2))
