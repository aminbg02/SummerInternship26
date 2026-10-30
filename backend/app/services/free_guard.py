"""Rejects any provider that could cost money.

There's no billing on this platform, so a paid provider doesn't fail gracefully —
it either 401s or quietly bills someone. Checked both when a provider is saved
(admin.py, seed_providers.py) and again before dispatch (llm_router.complete).

Turn off with FREE_ONLY=false only if you actually have billing.
"""
import ipaddress
from urllib.parse import urlparse

# Models running on your OWN hardware (Ollama, LM Studio, llama.cpp, vLLM…).
# Free by definition — no third party bills you for your own GPU — but only as
# long as the endpoint really is local, which is what _is_local_host enforces.
# All of them speak the OpenAI-compatible protocol, so llm_router needs no new
# branch: they go down the same path as Groq and friends, with api_base pointing
# at localhost.
LOCAL_PROVIDER_KEYS = {
    "ollama",
    "lm_studio",
    "lmstudio",      # alias
    "llama_cpp",
    "llamacpp",      # alias
    "vllm",
    "local",         # generic escape hatch for any other local server
}

FREE_PROVIDER_KEYS = {
    "gemini",
    "groq",
    "openrouter",    # :free model ids only — see check_provider
    "nvidia_nim",
    "nvidia",        # alias
    "mistral",
    "cerebras",
    "github",
    "github_models", # alias
} | LOCAL_PROVIDER_KEYS

# Matched as suffixes, so subdomains pass.
FREE_HOST_SUFFIXES = (
    "api.groq.com",
    "openrouter.ai",
    "integrate.api.nvidia.com",
    "api.mistral.ai",
    "api.cerebras.ai",
    "models.inference.ai.azure.com",
    "models.github.ai",
    "generativelanguage.googleapis.com",
)


def _host_of(base_url: str) -> str:
    raw = (base_url or "").strip()
    if not raw:
        return ""
    if "//" not in raw:
        raw = "//" + raw  # or urlparse reads it as a path, not a netloc
    return (urlparse(raw).hostname or "").lower()


def is_local_key(provider_key) -> bool:
    """True for a provider that runs on your own machine (or your LAN)."""
    return (provider_key or "").strip().lower() in LOCAL_PROVIDER_KEYS


def _is_local_host(host: str) -> bool:
    """True only for a host that cannot reach a billable third-party API.

    Matched EXACTLY, not by suffix like FREE_HOST_SUFFIXES: this is the check
    that stops "ollama" from being typed in front of a paid public endpoint, and
    a suffix rule would let a registered domain ending in "localhost" through.

    Accepts loopback, private LAN and link-local addresses, so the model may sit
    on another box on your network — and host.docker.internal, which is how a
    container reaches a server running on the host.
    """
    if not host:
        return False
    h = host.strip().lower()
    # RFC 6761 reserves .localhost for exactly this, so *.localhost is safe.
    if h == "localhost" or h.endswith(".localhost"):
        return True
    if h == "host.docker.internal":
        return True
    try:
        ip = ipaddress.ip_address(h)
    except ValueError:
        return False  # a resolvable public name — not local
    return ip.is_loopback or ip.is_private or ip.is_link_local


def check_provider(provider_key: str, base_url, model_name: str):
    """Return (ok, reason). The reason is shown to the admin, so keep it readable."""
    pk = (provider_key or "").strip().lower()

    if pk not in FREE_PROVIDER_KEYS:
        allowed = ", ".join(sorted(FREE_PROVIDER_KEYS))
        return False, (
            f"provider_key '{pk or '(blank)'}' is not a known free service. "
            f"Free-only mode allows: {allowed}."
        )

    # A local model is free because it's YOUR hardware, not because of anything
    # about the endpoint — so the allowlist below doesn't apply and would reject
    # it. Instead the endpoint must prove it's actually local.
    if pk in LOCAL_PROVIDER_KEYS:
        if not (base_url or "").strip():
            return False, (
                f"base_url is required for '{pk}' — point it at your local server, "
                "e.g. http://localhost:11434/v1 (Ollama) or "
                "http://localhost:1234/v1 (LM Studio)."
            )
        host = _host_of(base_url)
        if not _is_local_host(host):
            return False, (
                f"'{pk}' means a model on your own machine, but host '{host}' is "
                "not local. Use localhost, 127.0.0.1, a private LAN address, or "
                "host.docker.internal."
            )
        return True, ""

    # Gemini is the only one that legitimately has no base_url (llm_router calls it
    # on LiteLLM's native branch). Everyone else goes through the OpenAI-compatible
    # branch, where a null api_base defaults to api.openai.com — so an empty base_url
    # doesn't fail closed, it ships our key to OpenAI and comes back 401.
    if pk != "gemini" and not (base_url or "").strip():
        return False, (
            f"base_url is required for '{pk}'. Only Gemini may omit it; every other "
            "provider is called through the OpenAI-compatible branch, where an empty "
            "base_url defaults to api.openai.com (not free, and it will reject the key)."
        )

    host = _host_of(base_url)
    if host and not any(host == s or host.endswith("." + s) or host.endswith(s)
                        for s in FREE_HOST_SUFFIXES):
        allowed = ", ".join(FREE_HOST_SUFFIXES)
        return False, (
            f"base_url host '{host}' is not an allowlisted free endpoint. "
            f"Allowed hosts: {allowed}."
        )

    # OpenRouter serves paid and free models off one endpoint and one key.
    if pk == "openrouter" and not (model_name or "").strip().endswith(":free"):
        return False, (
            "OpenRouter serves paid models from the same endpoint; only ':free' "
            f"model ids are allowed (got '{model_name or '(blank)'}'). "
            "Pick a model whose id ends in ':free'."
        )

    return True, ""


def is_known_free_key(provider_key: str) -> bool:
    return (provider_key or "").strip().lower() in FREE_PROVIDER_KEYS
