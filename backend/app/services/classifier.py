"""Second stage of the safety gate, after the PII filter.

Does two things: labels a chunk by category (for routing and for showing why it was
retrieved), and denies obvious prompt-injection outright. Rule-based, so it needs no
model and no network. Swapping in an LLM classifier later wouldn't change the
signature.
"""

# Highest-scoring bucket wins.
CATEGORY_KEYWORDS = {
    "billing": ["invoice", "bill", "payment", "euro", "charge", "refund",
                "subscription", "plan", "fee"],
    "technical_support": ["router", "reset", "password", "wifi", "error",
                          "install", "connect", "network", "support"],
    "safety": ["hard hat", "lockout", "tagout", "safety", "ppe", "boots",
               "maintenance", "hazard"],
    "hr": ["leave", "vacation", "remote work", "reimbursement", "salary",
           "employee", "annual leave", "expense"],
}

# Text trying to hijack the model's instructions. One hit and the chunk is dropped
# before it can reach the LLM.
INJECTION_MARKERS = [
    "ignore previous", "ignore all previous", "disregard the above",
    "disregard previous", "system prompt", "you are now", "jailbreak",
    "ignore your instructions", "override the rules",
]


def classify(text: str) -> dict:
    """-> {category, allowed, reasons}. reasons is empty when allowed."""
    low = (text or "").lower()

    scores = {
        category: sum(low.count(kw) for kw in keywords)
        for category, keywords in CATEGORY_KEYWORDS.items()
    }
    best = max(scores, key=scores.get)
    category = best if scores[best] > 0 else "general"

    reasons = [f"injection_marker:{m}" for m in INJECTION_MARKERS if m in low]

    return {"category": category, "allowed": not reasons, "reasons": reasons}
