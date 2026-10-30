"""Translate an incoming question into English, so retrieval can still work.

"""
from flask import current_app

from . import languages, llm_router


_SYSTEM = (
    "You are a translation engine. Translate the user's message into English. "
    "Reply with ONLY the translation — no quotes, no explanation, no preamble. "
    "Preserve product names, numbers, and technical terms exactly as written. "
    "If the message is already English, repeat it back unchanged."
)


_MAX_TOKENS = 200


def _pick_provider(company_id, preferred=None):
    """The model to translate with: the one the user chose, else any enabled one.
    """
    if preferred is not None:
        return preferred
    from ..blueprints.providers import enabled_providers_for

    candidates = enabled_providers_for(company_id)
    return candidates[0] if candidates else None


def to_english(question, locale, *, company_id=None, user_id=None, provider=None):
    """Return `question` in English, or unchanged if it already is / can't be.


    """
    if languages.is_english(locale):
        return question, False
    if not current_app.config.get("QUERY_TRANSLATION_ENABLED", True):
        return question, False
    if not (question or "").strip():
        return question, False

    provider = _pick_provider(company_id, provider)
    if provider is None:
        return question, False  # no model available

    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": question},
    ]
    try:
        result = llm_router.complete(
            provider, messages,
            company_id=company_id, user_id=user_id,
            temperature=0.0, max_tokens=_MAX_TOKENS,
        )
    except Exception as exc:
        current_app.logger.warning("query translation failed (%s): %s", locale, exc)
        return question, False

    translated = (result.get("content") or "").strip()
    if not translated:
        return question, False
    return translated, True
