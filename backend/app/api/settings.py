from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.llm_config import LLMConfig, load_config, save_config

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsResponse(BaseModel):
    provider: str
    api_key_set: bool  # Don't expose the actual key
    ollama_url: str
    model_name: str
    effective_model: str
    kraken_enabled: bool
    kraken_available: bool


class SettingsUpdate(BaseModel):
    provider: str | None = None
    api_key: str | None = None
    ollama_url: str | None = None
    model_name: str | None = None
    kraken_enabled: bool | None = None


def _check_kraken() -> bool:
    try:
        import kraken  # noqa: F401
        return True
    except ImportError:
        return False


@router.get("", response_model=SettingsResponse)
async def get_settings():
    config = load_config()
    return SettingsResponse(
        provider=config.provider,
        api_key_set=bool(config.api_key),
        ollama_url=config.ollama_url,
        model_name=config.model_name,
        effective_model=config.effective_model,
        kraken_enabled=config.kraken_enabled,
        kraken_available=_check_kraken(),
    )


@router.put("", response_model=SettingsResponse)
async def update_settings(data: SettingsUpdate):
    config = load_config()

    if data.provider is not None:
        if data.provider not in ("claude", "ollama", "none"):
            raise HTTPException(status_code=400, detail="Provider must be: claude, ollama, or none")
        config.provider = data.provider
    if data.api_key is not None:
        config.api_key = data.api_key
    if data.ollama_url is not None:
        config.ollama_url = data.ollama_url
    if data.model_name is not None:
        config.model_name = data.model_name
    if data.kraken_enabled is not None:
        config.kraken_enabled = data.kraken_enabled

    save_config(config)

    return SettingsResponse(
        provider=config.provider,
        api_key_set=bool(config.api_key),
        ollama_url=config.ollama_url,
        model_name=config.model_name,
        effective_model=config.effective_model,
        kraken_enabled=config.kraken_enabled,
        kraken_available=_check_kraken(),
    )


@router.post("/test-connection")
async def test_connection():
    """Test connection to the configured LLM provider."""
    config = load_config()

    if config.provider == "claude":
        if not config.api_key:
            return {"status": "error", "message": "No API key configured"}
        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=config.api_key)
            # Quick model list check
            msg = await client.messages.create(
                model=config.effective_model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Say OK"}],
            )
            return {"status": "ok", "message": f"Connected to {config.effective_model}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    elif config.provider == "ollama":
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{config.ollama_url}/api/tags")
                resp.raise_for_status()
                models = [m["name"] for m in resp.json().get("models", [])]
                return {
                    "status": "ok",
                    "message": f"Ollama connected. {len(models)} models available.",
                    "models": models,
                }
        except Exception as e:
            return {"status": "error", "message": f"Cannot connect to Ollama at {config.ollama_url}: {e}"}

    return {"status": "ok", "message": "No LLM provider configured (Kraken-only mode)"}
