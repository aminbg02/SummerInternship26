"""Seed admin-added PII detection rules (PiiRule) per company, plus one
platform-wide rule, so services/filter.py has non-Presidio-builtin entity
types to catch — each tenant's own internal ID formats, not just the generic
email/card patterns Presidio ships out of the box.

Run with:  python -m app.seed_pii_rules   (after python -m app.seed)

Idempotent: matches on (entity_name, company_id) and updates in place.
"""
from . import create_app
from .extensions import db
from .models import Company, PiiRule

# company_id=None rows apply to every tenant (see PiiRule.company_id
# docstring) — kept separate since they aren't scoped to a domain.
GLOBAL_RULES = [
    # Orange-group-wide employee badge format, shared across every subsidiary.
    {"entity_name": "ORG_EMPLOYEE_ID", "pattern": r"\bORG-EMP-\d{6}\b", "score": 0.8},
]

# domain -> list of rule specs. Deliberately varied by the kind of business
# each tenant runs (telco, bank, ISP, automaker, university) rather than one
# template repeated six times — a bank's sensitive identifiers are account/RIB
# numbers, a telco's are subscriber/SIM ids, a university's are student ids.
RULES_BY_DOMAIN = {
    "telecom.com": [
        {"entity_name": "TELECOM_SUBSCRIBER_ID", "pattern": r"\bTC-\d{8}\b", "score": 0.9},
        # Tunisian mobile numbers: 8 digits starting 2/5/9.
        {"entity_name": "TELECOM_MSISDN", "pattern": r"\b(?:2|5|9)\d{7}\b", "score": 0.7},
    ],
    "ooredoo.tn": [
        {"entity_name": "OOREDOO_SIM_SERIAL", "pattern": r"\b89216\d{15}\b", "score": 0.9},
        {"entity_name": "OOREDOO_CUSTOMER_REF", "pattern": r"\bOOR-\d{6}\b", "score": 0.85},
    ],
    "biat.com.tn": [
        # Tunisian bank RIB: 20 digits, no separators — the most sensitive
        # format here, so it carries the highest confidence score.
        {"entity_name": "BIAT_RIB", "pattern": r"\b\d{20}\b", "score": 0.95},
        {"entity_name": "BIAT_ACCOUNT_NUMBER", "pattern": r"\bBIAT\d{10}\b", "score": 0.9},
    ],
    "topnet.com": [
        {"entity_name": "TOPNET_CONTRACT_ID", "pattern": r"\bTOP-\d{7}\b", "score": 0.8},
    ],
    "fiat.com": [
        # Standard 17-char VIN alphabet excludes I, O, Q.
        {"entity_name": "FIAT_VIN", "pattern": r"\b[A-HJ-NPR-Z0-9]{17}\b", "score": 0.85},
        {"entity_name": "FIAT_DEALER_CODE", "pattern": r"\bFIAT-\d{4}\b", "score": 0.7},
    ],
    "utm.com": [
        {"entity_name": "UTM_STUDENT_ID", "pattern": r"\b\d{2}[A-Z]{2}\d{4}\b", "score": 0.8},
    ],
}


def _get_or_create(entity_name, pattern, score, company_id):
    rule = PiiRule.query.filter_by(entity_name=entity_name, company_id=company_id).first()
    if rule is None:
        rule = PiiRule(entity_name=entity_name, company_id=company_id)
        db.session.add(rule)
    rule.pattern = pattern
    rule.score = score
    rule.enabled = True
    return rule


def seed_pii_rules():
    for spec in GLOBAL_RULES:
        _get_or_create(spec["entity_name"], spec["pattern"], spec["score"], company_id=None)

    for domain, specs in RULES_BY_DOMAIN.items():
        company = Company.query.filter_by(domain=domain).first()
        if company is None:
            print(f"  ! no company for domain {domain} — run python -m app.seed first, skipping")
            continue
        for spec in specs:
            _get_or_create(spec["entity_name"], spec["pattern"], spec["score"], company_id=company.id)

    db.session.commit()

    print("Seeded PII rules:")
    for spec in GLOBAL_RULES:
        print(f"  [global]        {spec['entity_name']:<24} score={spec['score']}")
    for domain, specs in RULES_BY_DOMAIN.items():
        for spec in specs:
            print(f"  {domain:<15} {spec['entity_name']:<24} score={spec['score']}")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        seed_pii_rules()
