from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from backend.brokers.plan_detector import detect_alpaca_plan
from backend.config import reload_settings, settings
from backend.database import load_state, save_state
from backend.security.audit_logger import AuditLogger
from backend.security.secrets import ensure_env_file, mask_secret, write_onboarding_env_values
from backend.settings.user_settings import UserSettings, default_user_settings


router = APIRouter()


class ProviderGuide(BaseModel):
    id: str
    label: str
    env_key: str | None = None
    recommended: bool = False
    needs_api_key: bool = True
    description: str
    helper_text: str
    setup_url: str
    instructions: list[str]


class ServiceGuide(BaseModel):
    id: str
    label: str
    env_keys: list[str]
    category: Literal["broker", "market_data", "news", "optional"]
    recommended: bool = False
    required_with: str | None = None
    description: str
    helper_text: str
    setup_url: str
    instructions: list[str]


class SetupGuideResponse(BaseModel):
    security_note: str
    quickstart_steps: list[str]
    providers: list[ProviderGuide]
    services: list[ServiceGuide]


class SecretKeyStatus(BaseModel):
    name: str
    configured: bool
    masked_value: str
    message: str


class SaveSetupSecretsRequest(BaseModel):
    ai_provider: Literal["openai", "anthropic", "google", "ollama"] = "openai"
    values: dict[str, str] = Field(default_factory=dict)
    alpaca_mode: Literal["paper", "live"] = "paper"

    @field_validator("values")
    @classmethod
    def trim_values(cls, values: dict[str, str]) -> dict[str, str]:
        return {key: value.strip() for key, value in values.items()}


def provider_guides() -> list[ProviderGuide]:
    return [
        ProviderGuide(
            id="openai",
            label="OpenAI",
            env_key="OPENAI_API_KEY",
            recommended=True,
            description="Fastest path if you want the default hosted AI provider.",
            helper_text="You only need one AI provider to get started.",
            setup_url="https://platform.openai.com/api-keys",
            instructions=[
                "Sign in to your OpenAI account.",
                "Open the API keys page and create a new secret key.",
                "Copy the key once and paste it into FinPilot.",
            ],
        ),
        ProviderGuide(
            id="anthropic",
            label="Anthropic",
            env_key="ANTHROPIC_API_KEY",
            description="Alternative hosted model provider for analysis and strategy chat.",
            helper_text="Choose this if you already use Anthropic for API access.",
            setup_url="https://console.anthropic.com/settings/keys",
            instructions=[
                "Sign in to the Anthropic Console.",
                "Open API Keys and create a new key.",
                "Paste the copied key into FinPilot.",
            ],
        ),
        ProviderGuide(
            id="google",
            label="Google Gemini",
            env_key="GOOGLE_API_KEY",
            description="Hosted Gemini models for users who prefer Google AI Studio.",
            helper_text="Useful if you already manage Gemini keys in Google AI Studio.",
            setup_url="https://aistudio.google.com/app/apikey",
            instructions=[
                "Open Google AI Studio while signed in.",
                "Create an API key in the API keys section.",
                "Paste it into FinPilot and keep the key private.",
            ],
        ),
        ProviderGuide(
            id="ollama",
            label="Ollama",
            needs_api_key=False,
            description="Run a local model on your own machine with no hosted API key.",
            helper_text="Good for privacy-first experiments if Ollama is already installed locally.",
            setup_url="https://ollama.com/download",
            instructions=[
                "Install Ollama on your computer.",
                "Download a model such as llama3.2.",
                "Choose Ollama in FinPilot and keep the default local URL unless you changed it.",
            ],
        ),
    ]


def service_guides() -> list[ServiceGuide]:
    return [
        ServiceGuide(
            id="alpaca",
            label="Alpaca broker",
            env_keys=["ALPACA_API_KEY", "ALPACA_SECRET_KEY"],
            category="broker",
            recommended=True,
            description="Paper trading and, later, staged live trading unlocks.",
            helper_text="Recommended if you want to place paper trades from FinPilot.",
            setup_url="https://app.alpaca.markets/signup",
            instructions=[
                "Create or sign in to your Alpaca account.",
                "Open your API credentials page and copy both the API key and secret key.",
                "Leave FinPilot in paper mode unless you intentionally switch later.",
            ],
        ),
        ServiceGuide(
            id="finnhub",
            label="Finnhub news",
            env_keys=["FINNHUB_API_KEY"],
            category="news",
            description="Adds market news and sentiment signals.",
            helper_text="Optional, but helpful if you want the sentiment agent to use news feeds.",
            setup_url="https://finnhub.io/register",
            instructions=[
                "Create a free Finnhub account.",
                "Open the dashboard and copy your API key.",
                "Paste it into FinPilot to enable Finnhub-backed sentiment data.",
            ],
        ),
        ServiceGuide(
            id="marketaux",
            label="Marketaux",
            env_keys=["MARKETAUX_API_KEY"],
            category="news",
            description="Entity-aware news sentiment for stocks and sectors.",
            helper_text="Optional extra signal for the sentiment agent.",
            setup_url="https://www.marketaux.com/",
            instructions=[
                "Create a Marketaux account.",
                "Find your API key in the account or dashboard area.",
                "Paste it into FinPilot if you want richer news entity scoring.",
            ],
        ),
        ServiceGuide(
            id="fmp",
            label="Financial Modeling Prep",
            env_keys=["FMP_API_KEY"],
            category="market_data",
            description="Earnings surprises, analyst grades, and growth context.",
            helper_text="Optional upgrade for fundamentals and growth signals.",
            setup_url="https://site.financialmodelingprep.com/developer/docs",
            instructions=[
                "Create an FMP account.",
                "Generate or copy your API key from the dashboard.",
                "Paste it into FinPilot to enable FMP-backed fields.",
            ],
        ),
        ServiceGuide(
            id="fred",
            label="FRED",
            env_keys=["FRED_API_KEY"],
            category="market_data",
            description="Optional key for higher FRED rate limits.",
            helper_text="FinPilot already works with FRED without a key, so this one is optional.",
            setup_url="https://fred.stlouisfed.org/docs/api/api_key.html",
            instructions=[
                "Sign in to FRED if you already use it.",
                "Request an API key from the FRED API page.",
                "Paste it into FinPilot only if you want the extra limit headroom.",
            ],
        ),
        ServiceGuide(
            id="reddit",
            label="Reddit app",
            env_keys=["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT"],
            category="optional",
            description="Lets the sentiment agent read Reddit mention trends.",
            helper_text="Requires creating a Reddit app plus a descriptive user agent.",
            setup_url="https://www.reddit.com/prefs/apps",
            instructions=[
                "Sign in to Reddit and scroll to the app preferences page.",
                "Create a script app and copy the client ID and secret.",
                "Keep the default user agent or replace it with one that identifies your account.",
            ],
        ),
        ServiceGuide(
            id="polygon",
            label="Polygon",
            env_keys=["POLYGON_API_KEY"],
            category="market_data",
            description="Optional premium market data provider.",
            helper_text="Only needed if you already pay for Polygon and want to use it here.",
            setup_url="https://polygon.io/",
            instructions=[
                "Sign in to Polygon.",
                "Copy your API key from the dashboard.",
                "Paste it into FinPilot if you want Polygon-backed data.",
            ],
        ),
    ]


def current_key_statuses() -> list[SecretKeyStatus]:
    reload_settings()
    return [
        SecretKeyStatus(
            name="OpenAI",
            configured=bool(settings.openai_api_key),
            masked_value=mask_secret(settings.openai_api_key),
            message="Missing",
        ),
        SecretKeyStatus(
            name="Anthropic",
            configured=bool(settings.anthropic_api_key),
            masked_value=mask_secret(settings.anthropic_api_key),
            message="Missing",
        ),
        SecretKeyStatus(
            name="Google",
            configured=bool(settings.google_api_key),
            masked_value=mask_secret(settings.google_api_key),
            message="Missing",
        ),
        SecretKeyStatus(
            name="Alpaca",
            configured=settings.has_alpaca(),
            masked_value=mask_secret(settings.alpaca_api_key),
            message="Needs API + secret key",
        ),
        SecretKeyStatus(
            name="Finnhub",
            configured=bool(settings.finnhub_api_key),
            masked_value=mask_secret(settings.finnhub_api_key),
            message="Optional news key",
        ),
        SecretKeyStatus(
            name="Marketaux",
            configured=bool(settings.marketaux_api_key),
            masked_value=mask_secret(settings.marketaux_api_key),
            message="Optional news key",
        ),
        SecretKeyStatus(
            name="FMP",
            configured=bool(settings.fmp_api_key),
            masked_value=mask_secret(settings.fmp_api_key),
            message="Optional market data key",
        ),
        SecretKeyStatus(
            name="FRED",
            configured=bool(settings.fred_api_key),
            masked_value=mask_secret(settings.fred_api_key),
            message="Optional macro data key",
        ),
        SecretKeyStatus(
            name="Polygon",
            configured=bool(settings.polygon_api_key),
            masked_value=mask_secret(settings.polygon_api_key),
            message="Optional premium data key",
        ),
        SecretKeyStatus(
            name="Reddit",
            configured=bool(settings.reddit_client_id and settings.reddit_client_secret),
            masked_value=mask_secret(settings.reddit_client_id),
            message="Needs client ID + secret",
        ),
    ]


async def current_setup_status() -> dict:
    reload_settings()
    saved_settings = await load_state("user_settings", None)
    current = UserSettings.from_dict(saved_settings) if saved_settings else default_user_settings()
    return {
        "first_run": saved_settings is None,
        "configured_sources": settings.available_data_sources(),
        "user_settings": current.to_dict(),
        "has_alpaca": settings.has_alpaca(),
        "has_ai_provider": settings.has_ai_provider(),
        "ai_provider": settings.ai_provider,
        "alpaca_mode": settings.alpaca_mode,
        "env_file_present": ensure_env_file().exists(),
    }


async def sync_runtime_settings() -> None:
    raw = await load_state("user_settings", None)
    current = UserSettings.from_dict(raw) if raw else default_user_settings()
    current.llm.provider = settings.ai_provider
    current.data_sources.use_finnhub = bool(settings.finnhub_api_key)
    current.data_sources.use_marketaux = bool(settings.marketaux_api_key)
    current.data_sources.use_fmp = bool(settings.fmp_api_key)
    current.data_sources.use_reddit = bool(settings.reddit_client_id and settings.reddit_client_secret)
    current.data_sources.use_alpaca_data = settings.has_alpaca()
    current.data_sources.use_polygon = bool(settings.polygon_api_key)
    await save_state("user_settings", current.to_dict())


@router.get("/status")
async def setup_status():
    return await current_setup_status()


@router.get("/validate-keys")
async def validate_keys():
    return {"keys": [item.model_dump() for item in current_key_statuses()]}


@router.get("/guides")
async def setup_guides():
    return SetupGuideResponse(
        security_note=(
            "Your keys stay on this machine. The browser sends them only to your local FinPilot backend, "
            "which writes them into the local .env file. FinPilot never stores them in browser storage "
            "and only returns masked status values back to the UI."
        ),
        quickstart_steps=[
            "Choose one AI provider to unlock strategy chat and agent analysis.",
            "Add Alpaca if you want paper trading from inside FinPilot.",
            "Add optional data providers only when you want deeper signals.",
        ],
        providers=provider_guides(),
        services=service_guides(),
    ).model_dump()


@router.post("/save-secrets")
async def save_secrets(payload: SaveSetupSecretsRequest):
    updates = {"AI_PROVIDER": payload.ai_provider, "ALPACA_MODE": payload.alpaca_mode}
    for key, value in payload.values.items():
        if value:
            updates[key] = value

    if payload.ai_provider != "ollama":
        provider_key_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
        }
        required_key = provider_key_map[payload.ai_provider]
        current_status = current_key_statuses()
        configured_now = any(
            status.name.lower() == payload.ai_provider and status.configured for status in current_status
        )
        if required_key not in updates and not configured_now:
            raise HTTPException(status_code=400, detail=f"{required_key} is required for {payload.ai_provider}.")

    try:
        saved_keys = write_onboarding_env_values(updates)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    reload_settings()
    await sync_runtime_settings()
    AuditLogger.log(
        "setup",
        "secrets.saved",
        {
            "saved_keys": saved_keys,
            "ai_provider": settings.ai_provider,
            "alpaca_mode": settings.alpaca_mode,
        },
    )
    return {
        "ok": True,
        "saved_keys": saved_keys,
        "status": await current_setup_status(),
        "keys": [item.model_dump() for item in current_key_statuses()],
        "message": "Saved locally to .env. Masked status has been refreshed.",
    }


@router.get("/plan")
async def plan_status(override: str = "auto"):
    reload_settings()
    plan = await detect_alpaca_plan(override)
    return plan.__dict__ | {"plan": plan.plan.value}
