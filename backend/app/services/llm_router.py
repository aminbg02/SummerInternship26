"""

Loads a provider row, decrypts its  and calls LiteLLM.

"""
from flask import current_app

from ..extensions import db
from ..models import User
from . import crypto, free_guard, usage


class LlmRouterError(Exception):
    pass


def _call_litellm(**kwargs):
    import litellm
    return litellm.completion(**kwargs)


def _clamp(value, low, high):
    return max(low, min(value, high))


def resolve_generation_params(provider, temperature=None, max_tokens=None) -> dict:
    """Settle the final temperature/max_tokens: request -> provider -> global default.
    """
    cfg = current_app.config

    temp_max = cfg.get("GEN_TEMPERATURE_MAX", 2.0)
    if temperature is None:
        temperature = provider.default_temperature
    if temperature is None:
        temperature = cfg.get("GEN_DEFAULT_TEMPERATURE", 0.2)
    temperature = _clamp(float(temperature), 0.0, temp_max)

    global_ceiling = cfg.get("GEN_MAX_TOKENS_CEILING", 4096)
    provider_cap = provider.max_output_tokens or global_ceiling
    hard_cap = min(provider_cap, global_ceiling)  # the tighter of the two wins

    if max_tokens is None:
        max_tokens = provider.max_output_tokens or cfg.get("GEN_DEFAULT_MAX_TOKENS", 1024)
    max_tokens = int(_clamp(int(max_tokens), 1, hard_cap))

    return {"temperature": temperature, "max_tokens": max_tokens}


def _kwargs_for(provider, messages, gen_params, overrides):
    api_key = (
        crypto.decrypt(provider.api_key_encrypted)
        if provider.api_key_encrypted
        else None
    )

    if provider.provider_key == "gemini":
        kwargs = {
            "model": f"gemini/{provider.model_name}",
            "messages": messages,
            "api_key": api_key,
        }
    else:

        if api_key is None and free_guard.is_local_key(provider.provider_key):

            api_key = "local"
        kwargs = {
            "model": f"openai/{provider.model_name}",
            "messages": messages,
            "api_key": api_key,
            "api_base": provider.base_url,
        }

    kwargs["temperature"] = gen_params["temperature"]
    kwargs["max_tokens"] = gen_params["max_tokens"]


    cfg = current_app.config

    kwargs["timeout"] = (
        cfg.get("LLM_LOCAL_TIMEOUT_SECONDS", 120)
        if free_guard.is_local_key(provider.provider_key)
        else cfg.get("LLM_TIMEOUT_SECONDS", 15)
    )
    kwargs["num_retries"] = cfg.get("LLM_NUM_RETRIES", 0)

    kwargs.update(overrides)
    return kwargs


def _extract(obj, key, default=None):
    """LiteLLM hands back objects; tests and some providers hand back dicts."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _reasoning_tokens(usage_field) -> int:
    """Tokens spent thinking before answering
    """
    details = _extract(usage_field, "completion_tokens_details")
    value = _extract(details, "reasoning_tokens")
    if value is None:
        value = _extract(usage_field, "reasoning_tokens")
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def complete(provider, messages, *, company_id=None, user_id=None,
             conversation_id=None, temperature=None, max_tokens=None,
             **overrides) -> dict:

    if current_app.config.get("FREE_ONLY", True) and not free_guard.is_known_free_key(
        provider.provider_key
    ):
        raise LlmRouterError(
            f"free-only mode: provider_key '{provider.provider_key}' is not a "
            "known free service; refusing to call it."
        )

    usage.check_provider_rate_limit(provider)
    if company_id is not None:
        usage.check_company_quota(company_id)
    if user_id is not None:
        user = db.session.get(User, user_id)
        if user is not None:
            usage.check_user_quota(user)

    gen_params = resolve_generation_params(provider, temperature, max_tokens)
    kwargs = _kwargs_for(provider, messages, gen_params, overrides)


    usage.record_provider_call(provider.id)

    try:
        resp = _call_litellm(**kwargs)
    except Exception as e:

        usage.mark_provider_failed(provider.id, str(e))
        raise LlmRouterError(str(e)) from e

    usage.clear_provider_failure(provider.id)

    choices = _extract(resp, "choices") or []
    if not choices:
        raise LlmRouterError("provider returned no choices")
    message = _extract(choices[0], "message")
    content = _extract(message, "content", "") or ""


    usage_field = _extract(resp, "usage")
    result = {
        "content": content,
        "prompt_tokens": _extract(usage_field, "prompt_tokens"),
        "completion_tokens": _extract(usage_field, "completion_tokens"),
        "reasoning_tokens": _reasoning_tokens(usage_field),
        "total_tokens": _extract(usage_field, "total_tokens"),
        "model": kwargs["model"],
        "params": gen_params,
    }


    if company_id is not None:
        usage.log_token_usage(
            company_id, user_id, provider.id, conversation_id, result, messages
        )
    return result
