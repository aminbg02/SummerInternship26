
import re

from presidio_analyzer import AnalyzerEngine, PatternRecognizer, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_analyzer.pattern import Pattern
from presidio_analyzer.predefined_recognizers import (
    EsNieRecognizer,
    EsNifRecognizer,
    EsPassportRecognizer,
    PlPeselRecognizer,
)

# Order matters: the specific patterns run before the loose phone one, otherwise
# the phone regex eats half a card number. Used by redact() ONLY now — apply_filter()
# below uses Presidio instead (see module docstring), and redact() is its fallback.
PATTERNS = {
    "email": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b"),
    "iban": re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b"),
    # Conservative on length so it doesn't redact "79 euros" or "10 seconds".
    "phone": re.compile(r"\b\+?\d[\d ().-]{7,}\d\b"),
}


def scan(text: str) -> dict:
    """{pii_type: match_count} for everything found in `text`."""
    found = {}
    for name, pattern in PATTERNS.items():
        matches = pattern.findall(text or "")
        if matches:
            found[name] = len(matches)
    return found


def redact(text: str):
    """Replace each match with [REDACTED_<TYPE>]. Returns (clean_text, types_found)."""
    types = []
    clean = text or ""
    for name, pattern in PATTERNS.items():
        if pattern.search(clean):
            clean = pattern.sub(f"[REDACTED_{name.upper()}]", clean)
            types.append(name)
    return clean, types


_PII_ENTITIES = [
    "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD", "US_SSN", "IBAN_CODE",
    "US_BANK_NUMBER", "US_PASSPORT", "US_ITIN", "US_DRIVER_LICENSE",
    "CRYPTO", "MEDICAL_LICENSE",
    "ES_NIF", "ES_NIE", "ES_PASSPORT", "PL_PESEL", "FR_NIR",
]


class FrNirRecognizer(PatternRecognizer):
    """The French INSEE/NIR number ("numéro de sécurité sociale") — 13 digits
    (sex, year, month, department [2A/2B for Corsica], commune, order) plus a
    2-digit checksum. Presidio has no built-in recognizer for France, so this
    follows the same pattern Presidio's own country recognizers use: a weak
    structural match, promoted to full confidence only if validate_result's
    checksum passes."""

    PATTERNS = [
        Pattern(
            name="fr_nir (weak)",
            regex=r"\b[12]\d{2}(?:0[1-9]|1[0-2])(?:\d{2}|2[AB])\d{3}\d{3}\d{2}\b",
            score=0.3,
        ),
    ]
    CONTEXT = ["nir", "insee", "sécurité sociale", "securite sociale", "numéro de sécurité"]

    def __init__(self, supported_language="en"):
        super().__init__(
            supported_entity="FR_NIR",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language=supported_language,
        )

    def validate_result(self, pattern_text: str):
        """Real modulo-97 checksum, same algorithm INSEE itself uses. Corsica
        codes 2A/2B count as 19/18 respectively for this calculation."""
        digits = re.sub(r"\s", "", pattern_text)
        if len(digits) != 15:
            return None
        body, key = digits[:13].upper().replace("2A", "19").replace("2B", "18"), digits[13:]
        if not body.isdigit() or not key.isdigit():
            return None
        return (97 - (int(body) % 97)) == int(key)


def _eu_recognizers():
    """Spain + Poland + France national ID recognizers, always active — same
    tier as Presidio's own US/UK built-ins, not admin-editable like PiiRule.
    Spain/Poland reuse Presidio's real recognizer classes (regex + checksum),
    just constructed with supported_language="en" instead of their default
    'es'/'pl': analyze() only runs a recognizer whose language matches the
    `language=` argument, and _get_nlp_engine is English-only, so the default
    tag would silently never fire. The tag doesn't affect the regex/checksum
    logic itself, so retagging is safe."""
    return [
        EsNifRecognizer(supported_language="en"),
        EsNieRecognizer(supported_language="en"),
        EsPassportRecognizer(supported_language="en"),
        PlPeselRecognizer(supported_language="en"),
        FrNirRecognizer(supported_language="en"),
    ]


_nlp_engine = None


def _get_nlp_engine():
    global _nlp_engine
    if _nlp_engine is None:
        _nlp_engine = NlpEngineProvider(nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
        }).create_engine()
    return _nlp_engine


def _custom_recognizers(company_id):
    """Admin-added rules from the PiiRule table (CRUD in app/blueprints/
    admin.py), scoped to `company_id` — NULL applies to everyone, a specific
    id only when it matches. Same OR-NULL convention as LlmProvider.company_id.
    company_id=None sees only the global rules.

    Swallows any error — an admin-rule lookup failing must not break detection
    of Presidio's built-in types. Returns (recognizers, entity_names); the
    names are needed too, since they must join the entities allowlist or a
    custom rule would silently never fire."""
    try:
        from ..models import PiiRule

        query = PiiRule.query.filter_by(enabled=True)
        if company_id is not None:
            query = query.filter(
                (PiiRule.company_id == company_id) | (PiiRule.company_id.is_(None))
            )
        else:
            query = query.filter(PiiRule.company_id.is_(None))
        rows = query.all()
    except Exception:  # noqa: BLE001 — no app/request context, or DB unavailable
        return [], []
    recognizers, names = [], []
    for row in rows:
        try:
            recognizers.append(PatternRecognizer(
                supported_entity=row.entity_name,
                patterns=[Pattern(name=f"rule-{row.id}", regex=row.pattern, score=row.score)],
            ))
            names.append(row.entity_name)
        except Exception:  # noqa: BLE001 — a bad regex in one admin rule shouldn't drop the rest
            continue
    return recognizers, names


def _get_analyzer(company_id):
    """A fresh AnalyzerEngine per call, reusing the already-loaded NLP engine.
    Cheap: this is what makes admin-added rules take effect immediately, with
    no cache to invalidate and no redeploy. Returns (analyzer, entities) — the
    entities allowlist to pass to analyze(), see _PII_ENTITIES above."""
    custom_recognizers, custom_names = _custom_recognizers(company_id)
    registry = RecognizerRegistry()
    registry.load_predefined_recognizers(nlp_engine=_get_nlp_engine())
    for r in _eu_recognizers():
        registry.add_recognizer(r)
    for r in custom_recognizers:
        registry.add_recognizer(r)
    analyzer = AnalyzerEngine(nlp_engine=_get_nlp_engine(), registry=registry)
    return analyzer, _PII_ENTITIES + custom_names


def _resolve_overlaps(results):
    """Presidio's recognizers can agree on overlapping spans (e.g. an email
    partly matching the URL recognizer too). Keep the highest-confidence span
    in any overlapping cluster, greedily."""
    kept = []
    for r in sorted(results, key=lambda r: r.score, reverse=True):
        if not any(r.start < k.end and k.start < r.end for k in kept):
            kept.append(r)
    return sorted(kept, key=lambda r: r.start)


def apply_filter(text: str, company_id: int | None = None) -> dict:
    """Filter one chunk -> {action: pass|redacted, clean_text, pii: [types]}.

    Presidio-backed (built-ins + NER + admin-added PiiRule patterns, scoped to
    `company_id` — see _custom_recognizers). Falls back to the plain-regex
    redact() above if Presidio itself errors — a filter failure must degrade
    to weaker detection, never to none at all. company_id=None (a call site
    with no tenant context, e.g. this module's own tests) sees only
    platform-wide (company_id=NULL) custom rules, never a specific tenant's.
    """
    try:
        analyzer, entities = _get_analyzer(company_id)
        results = _resolve_overlaps(analyzer.analyze(text=text or "", language="en", entities=entities))
    except Exception:  # noqa: BLE001 — Presidio/spaCy hiccup: fall back, don't 500 the request
        clean, types = redact(text)
        return {"action": "redacted" if types else "pass", "clean_text": clean, "pii": types}

    types = sorted({r.entity_type for r in results})
    clean = text or ""
    for r in sorted(results, key=lambda r: r.start, reverse=True):
        clean = clean[: r.start] + f"[REDACTED_{r.entity_type}]" + clean[r.end :]

    return {
        "action": "redacted" if types else "pass",
        "clean_text": clean,
        "pii": types,
    }


def judge_with_llm(text: str, provider) -> dict:  # pragma: no cover
    """Seam for an LLM-as-judge pass. Not wired up — keeps the regex path dependency-free."""
    raise NotImplementedError("LLM-as-judge filtering is a later enhancement")

