"""The languages the platform speaks, and how a request declares one.

One list, shared by the answer-language instruction (blueprints/query.py) and the
query-translation step (services/translation.py), so the two can never disagree
about what "pl" means or which locales are allowed.

The knowledge base itself is NOT multilingual and is not meant to be: documents
are ingested, embedded and stored in English, and the embedding model
(BAAI/bge-small-en-v1.5) is English-only. Language enters the system at exactly
two points, both on *text*, never on vectors:

    1. the incoming question is translated to English before it is embedded
    2. the model is told to write its answer in the user's language

See services/translation.py for why translation has to happen before embedding.
"""

# locale code -> the name to use when instructing a model. Names are given in
# English because that is the language the system prompt itself is written in,
# and mixing languages inside one instruction makes models less reliable.
LANGUAGES = {
    "en": "English",
    "fr": "French",
    "es": "Spanish",
    "pl": "Polish",
}

DEFAULT_LOCALE = "en"


def normalise(locale) -> str:
    """Coerce whatever the client sent into a supported locale code.

    Accepts "FR", "fr-FR", "fr_FR" and similar, because a browser's
    `navigator.language` is a BCP-47 tag and the UI may pass it through
    untouched. Anything unrecognised — including None, a number, or a language we
    don't support — falls back to English rather than raising: a bad locale should
    degrade the wording of an answer, never fail the question.
    """
    if not isinstance(locale, str):
        return DEFAULT_LOCALE
    code = locale.strip().lower().replace("_", "-").split("-")[0]
    return code if code in LANGUAGES else DEFAULT_LOCALE


def name_of(locale) -> str:
    """English name of a locale, e.g. "fr" -> "French". Unknown -> "English"."""
    return LANGUAGES[normalise(locale)]


def is_english(locale) -> bool:
    """True when no translation or answer-language instruction is needed.

    The English path must stay byte-for-byte what it was before multilingual
    support existed — no extra model call, no extra prompt text. This predicate is
    what guarantees that.
    """
    return normalise(locale) == DEFAULT_LOCALE
