"""Register the free-tier providers from env vars.

Run with:  python -m app.seed_providers   (after python -m app.seed)

Reads GEMINI_API_KEY / GROQ_API_KEY / ... from the environment (.env). Skips any
provider whose key isn't set, so it's safe to run with only one configured. A
local provider (Ollama) has no key to skip on and is always registered.

Idempotent: matches on (provider_key, model_name) and updates in place instead
of duplicating. NOT on provider_key alone — five of the rows below are
"openrouter", and keying on the provider alone would collapse them into one row
whose model_name is whichever spec happened to be last.

The list mirrors the exported database (transfer_data/postgres.sql), including
priorities, so a seeded platform offers the same model menu in the same order as
a restored one.

The stored key is Fernet-encrypted here, exactly as the admin API would do it.
"""
import os

from . import create_app
from .extensions import db
from .models import LlmProvider
from .services import crypto, free_guard

# A local server authenticates nothing, but api_key_encrypted is what the router
# reads to build the client, and LiteLLM wants *something* in the Authorization
# header. This is the placeholder, not a secret.
LOCAL_PLACEHOLDER_KEY = "ollama"

# Rate limits below are the documented free-tier ceilings (BUILD_PLAN.md table).
SEED_PROVIDERS = [
    {
        "env": "GEMINI_API_KEY",
        "display_name": "Gemini 2.0 Flash",
        "provider_key": "gemini",
        "base_url": None,  # native branch, no OpenAI-compatible base_url
        "model_name": "gemini-2.0-flash",
        "is_free": True,
        "rate_limit_rpm": 15,
        "rate_limit_rpd": 1500,
        "priority": 90,
        # Generation controls: low temperature for grounded support answers, and a
        # per-provider output-token cap that protects the shared free key.
        "default_temperature": 0.2,
        "max_output_tokens": 1024,
    },
    {
        "env": "GROQ_API_KEY",
        "display_name": "Llama 3.3 70B (Groq)",
        "provider_key": "groq",
        "base_url": "https://api.groq.com/openai/v1",
        "model_name": "llama-3.3-70b-versatile",
        "is_free": True,
        "rate_limit_rpm": 30,
        "rate_limit_rpd": 1000,
        "priority": 20,
        "default_temperature": 0.2,
        "max_output_tokens": 1024,
    },
    {
        "env": "MISTRAL_API_KEY",
        "display_name": "Mistral Small",
        "provider_key": "mistral",
        "base_url": "https://api.mistral.ai/v1",
        "model_name": "mistral-small-latest",
        "is_free": True,
        "rate_limit_rpm": 60,
        "rate_limit_rpd": 1000,
        "priority": 30,
        "default_temperature": 0.2,
        "max_output_tokens": 1024,
    },
    {
        "env": "OPENROUTER_API_KEY",
        "display_name": "Llama 3.3 70B",
        "provider_key": "openrouter",
        "base_url": "https://openrouter.ai/api/v1",
        # OpenRouter serves paid models too; the free-guard requires a ':free' id.
        "model_name": "meta-llama/llama-3.3-70b-instruct:free",
        "is_free": True,
        "rate_limit_rpm": 20,
        "rate_limit_rpd": 50,
        "priority": 91,
        "default_temperature": 0.2,
        "max_output_tokens": 1024,
    },
    {
        "env": "CEREBRAS_API_KEY",
        "display_name": "GPT-OSS 120B",
        "provider_key": "cerebras",
        "base_url": "https://api.cerebras.ai/v1",
        "model_name": "gpt-oss-120b",
        "is_free": True,
        "rate_limit_rpm": 30,
        "rate_limit_rpd": 1000,
        "priority": 10,
        "default_temperature": 0.3,
        "max_output_tokens": 1024,
    },
    {
        "env": "NVIDIA_API_KEY",
        "display_name": "Llama 3.3 70B (NVIDIA)",
        "provider_key": "nvidia_nim",
        "base_url": "https://integrate.api.nvidia.com/v1",
        # NOT z-ai/glm-5.2. That model works, but it took 91 SECONDS to answer —
        # unusable in a demo, and the customer just watches a spinner. Llama 3.3
        # answers on the same endpoint in ~3.6s.
        "model_name": "meta/llama-3.3-70b-instruct",
        "is_free": True,
        "rate_limit_rpm": 40,
        "rate_limit_rpd": 1000,
        "priority": 40,
        "default_temperature": 0.2,
        "max_output_tokens": 1024,
    },
    # --- The rest of the OpenRouter menu -------------------------------------
    # Same key and same endpoint as the row above, different models. They exist
    # so the model picker has real breadth to choose from rather than one entry
    # per vendor, and because a 50/day ceiling on any single free OpenRouter
    # model runs out fast — having several means the demo keeps working.
    {
        "env": "OPENROUTER_API_KEY",
        "display_name": "Qwen3 Next 80B",
        "provider_key": "openrouter",
        "base_url": "https://openrouter.ai/api/v1",
        "model_name": "qwen/qwen3-next-80b-a3b-instruct:free",
        "is_free": True,
        "rate_limit_rpm": 20,
        "rate_limit_rpd": 50,
        "priority": 45,
        "default_temperature": 0.2,
        "max_output_tokens": 1024,
    },
    {
        "env": "OPENROUTER_API_KEY",
        "display_name": "Nemotron 3 Super 120B",
        "provider_key": "openrouter",
        "base_url": "https://openrouter.ai/api/v1",
        "model_name": "nvidia/nemotron-3-super-120b-a12b:free",
        "is_free": True,
        "rate_limit_rpm": 20,
        "rate_limit_rpd": 50,
        "priority": 46,
        "default_temperature": 0.2,
        "max_output_tokens": 1024,
    },
    {
        "env": "OPENROUTER_API_KEY",
        "display_name": "Hy3",
        "provider_key": "openrouter",
        "base_url": "https://openrouter.ai/api/v1",
        "model_name": "tencent/hy3:free",
        "is_free": True,
        "rate_limit_rpm": 20,
        "rate_limit_rpd": 1000,
        "priority": 92,
        "default_temperature": 0.2,
        "max_output_tokens": 1024,
    },
    {
        "env": "OPENROUTER_API_KEY",
        "display_name": "Laguna XS 2.1",
        "provider_key": "openrouter",
        "base_url": "https://openrouter.ai/api/v1",
        "model_name": "poolside/laguna-xs-2.1:free",
        "is_free": True,
        "rate_limit_rpm": 50,
        "rate_limit_rpd": 5000,
        "priority": 100,
        "default_temperature": 0.2,
        "max_output_tokens": 1024,
    },
    # --- Local ---------------------------------------------------------------
    # env=None: there is no key to look up, so this one is never skipped. It is
    # also the only row that still answers when every hosted free tier is spent
    # — worth keeping seeded even on a machine with no Ollama running, since a
    # provider that fails to connect greys itself out (see LLM_TIMEOUT_SECONDS)
    # rather than breaking anything.
    {
        "env": None,
        "display_name": "Local Ollama",
        "provider_key": "ollama",
        "base_url": "http://localhost:11434/v1",
        "model_name": "qwen2.5:3b-instruct",
        "is_free": True,
        "rate_limit_rpm": 50,
        "rate_limit_rpd": 5000,
        "priority": 100,
        "default_temperature": 0.2,
        "max_output_tokens": 1024,
    },
]


def seed_providers():
    for spec in SEED_PROVIDERS:
        env = spec.get("env")
        if env is None:
            api_key = LOCAL_PLACEHOLDER_KEY
        else:
            api_key = os.environ.get(env)
            if not api_key:
                print(f"  ! {env} not set — skipping {spec['display_name']}")
                continue

        # Free-only guardrail: never seed a provider that could cost money.
        ok, reason = free_guard.check_provider(
            spec["provider_key"], spec["base_url"], spec["model_name"]
        )
        if not ok:
            print(f"  ! not free — skipping {spec['display_name']}: {reason}")
            continue

        # (provider_key, model_name), not provider_key — see the module docstring.
        provider = LlmProvider.query.filter_by(
            provider_key=spec["provider_key"], model_name=spec["model_name"]
        ).first()
        if provider is None:
            provider = LlmProvider()
            db.session.add(provider)

        provider.display_name = spec["display_name"]
        provider.provider_key = spec["provider_key"]
        provider.base_url = spec["base_url"]
        provider.model_name = spec["model_name"]
        provider.is_free = spec["is_free"]
        provider.enabled = True
        provider.rate_limit_rpm = spec["rate_limit_rpm"]
        provider.rate_limit_rpd = spec["rate_limit_rpd"]
        provider.priority = spec["priority"]
        provider.default_temperature = spec["default_temperature"]
        provider.max_output_tokens = spec["max_output_tokens"]
        provider.api_key_encrypted = crypto.encrypt(api_key)

        print(f"  registered {spec['display_name']} ({spec['provider_key']}: {spec['model_name']})")

    db.session.commit()


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        seed_providers()
