"""Screening pipeline — Filter → Classifier, in that order.

This is the one place the safety gate is composed, so both the retrieval path
(query.py) and the upload path (documents.py) enforce it identically. Hard
constraint #4: no retrieved or uploaded content reaches the LLM without passing
through here first.

Order matters: redact PII first (filter), then classify the redacted text
(classifier) so policy decisions aren't thrown off by raw PII.
"""
from . import classifier
from . import filter as content_filter


def screen_chunk(text: str, company_id: int | None = None) -> dict:
    """Run one chunk through the full gate.

    company_id scopes which admin-added PiiRule rows apply (see
    filter.apply_filter) — pass the tenant this text belongs to/was retrieved
    for, or None to only apply platform-wide (company_id=NULL) rules.

    Returns:
        {
          "action": "pass" | "redacted" | "blocked",
          "text": str,          # cleaned text ("" when blocked)
          "category": str,      # classifier label
          "pii": [types...],    # PII types redacted (if any)
          "reasons": [str...],  # policy reasons when blocked
        }
    """
    f = content_filter.apply_filter(text, company_id=company_id)
    c = classifier.classify(f["clean_text"])

    if not c["allowed"]:
        # Policy denial wins — drop the chunk entirely.
        return {
            "action": "blocked",
            "text": "",
            "category": c["category"],
            "pii": f["pii"],
            "reasons": c["reasons"],
        }

    return {
        "action": "redacted" if f["pii"] else "pass",
        "text": f["clean_text"],
        "category": c["category"],
        "pii": f["pii"],
        "reasons": [],
    }


def screen_many(texts, company_id: int | None = None):
    """Screen a list of chunk texts; return the list of per-chunk verdicts."""
    return [screen_chunk(t, company_id=company_id) for t in texts]
