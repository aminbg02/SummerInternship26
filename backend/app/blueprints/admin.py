"""Admin registry management.

CRUD on the llm_providers table, plus a "test this provider"
is super-admin-only

the API key arrives here in plaintext exactly once (admin submits the form),
is immediately fernet-encrypted  and is never returned by any
endpoint
"""
import re
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, g, jsonify, request

from ..extensions import db
from ..models import (
    Company,
    KbDeletion,
    KbIngestion,
    LlmProvider,
    Message,
    PiiRule,
    ProviderCallLog,
    TokenUsage,
    User,
)
from ..security import require_role
from ..services import (
    crypto,
    feedback,
    free_guard,
    llm_router,
    qdrant_pool,
    rag,
    tenancy,
    usage,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


_EDITABLE_FIELDS = (
    "display_name",
    "provider_key",
    "base_url",
    "model_name",
    "enabled",
    "is_free",
    "rate_limit_rpm",
    "rate_limit_rpd",
    "rate_limit_group",
    "priority",
    "default_temperature",
    "max_output_tokens",
    "company_id",
)



_TRIMMED_FIELDS = (
    "display_name", "provider_key", "base_url", "model_name",

    "rate_limit_group",
)


_ENDPOINT_SUFFIX = "/chat/completions"


def _normalise_base_url(value: str) -> str:
    url = value.strip().rstrip("/")
    while url.lower().endswith(_ENDPOINT_SUFFIX):
        url = url[: -len(_ENDPOINT_SUFFIX)].rstrip("/")
    return url


def _apply_fields(provider: LlmProvider, data: dict):

    for field in _EDITABLE_FIELDS:
        if field in data:
            value = data[field]
            if field in _TRIMMED_FIELDS and isinstance(value, str):
                value = value.strip()
            if field == "base_url" and isinstance(value, str):
                value = _normalise_base_url(value)
            setattr(provider, field, value)


def _validate_company(data: dict):

    company_id = data.get("company_id")
    if company_id is not None and db.session.get(Company, company_id) is None:
        return jsonify(error="company_not_found"), 404
    return None


def _enforce_free(provider: LlmProvider):
    """Refuse to save a provider that could cost money (free_guard).
    """
    if not current_app.config.get("FREE_ONLY", True):
        return None
    ok, reason = free_guard.check_provider(
        provider.provider_key, provider.base_url, provider.model_name
    )
    if not ok:
        return jsonify(error="not_free_provider", detail=reason), 400
    provider.is_free = True
    return None


@admin_bp.get("/llm-providers")
@require_role("super_admin")
def list_all_providers():
    """List every provider (enabled or not) with the full admin view."""
    providers = LlmProvider.query.order_by(
        LlmProvider.priority, LlmProvider.id
    ).all()
    return jsonify(providers=[p.admin_dict() for p in providers])


@admin_bp.get("/llm-providers/<int:provider_id>")
@require_role("super_admin")
def get_provider(provider_id):
    provider = db.session.get(LlmProvider, provider_id)
    if provider is None:
        return jsonify(error="provider_not_found"), 404
    return jsonify(provider=provider.admin_dict())


@admin_bp.post("/llm-providers")
@require_role("super_admin")
def create_provider():
    data = request.get_json(silent=True) or {}

    for required in ("display_name", "provider_key", "model_name"):
        if not (data.get(required) or "").strip():
            return jsonify(error="missing_field", field=required), 400

    err = _validate_company(data)
    if err:
        return err

    provider = LlmProvider()
    _apply_fields(provider, data)
    provider.created_by = g.current_user.id

    err = _enforce_free(provider)
    if err:
        return err


    api_key = (data.get("api_key") or "").strip()
    if api_key:
        provider.api_key_encrypted = crypto.encrypt(api_key)

    db.session.add(provider)
    db.session.commit()
    return jsonify(provider=provider.admin_dict()), 201


@admin_bp.put("/llm-providers/<int:provider_id>")
@require_role("super_admin")
def update_provider(provider_id):
    provider = db.session.get(LlmProvider, provider_id)
    if provider is None:
        return jsonify(error="provider_not_found"), 404

    data = request.get_json(silent=True) or {}
    err = _validate_company(data)
    if err:
        return err

    _apply_fields(provider, data)


    err = _enforce_free(provider)
    if err:
        return err


    if "api_key" in data:
        api_key = (data.get("api_key") or "").strip()
        provider.api_key_encrypted = crypto.encrypt(api_key) if api_key else None

    db.session.commit()
    return jsonify(provider=provider.admin_dict())


@admin_bp.delete("/llm-providers/<int:provider_id>")
@require_role("super_admin")
def delete_provider(provider_id):
    """Delete a provider, clearing the two tables that hold an FK to it first.


    """
    provider = db.session.get(LlmProvider, provider_id)
    if provider is None:
        return jsonify(error="provider_not_found"), 404

    ProviderCallLog.query.filter_by(provider_id=provider_id).delete(
        synchronize_session=False
    )
    TokenUsage.query.filter_by(provider_id=provider_id).update(
        {"provider_id": None}, synchronize_session=False
    )

    Message.query.filter_by(provider_id=provider_id).update(
        {"provider_id": None}, synchronize_session=False
    )

    db.session.delete(provider)
    db.session.commit()
    return jsonify(deleted=provider_id)


@admin_bp.post("/llm-providers/<int:provider_id>/test")
@require_role("super_admin")
def test_provider(provider_id):
    """Send a trivial prompt through the router to verify the provider works.
    """
    provider = db.session.get(LlmProvider, provider_id)
    if provider is None:
        return jsonify(error="provider_not_found"), 404

    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "Reply with the single word: pong.").strip()
    messages = [{"role": "user", "content": prompt}]

    try:
        result = llm_router.complete(
            provider, messages,
            temperature=data.get("temperature"), max_tokens=data.get("max_tokens"),
        )
    except usage.RateLimitExceeded as e:
        # The shared-key ceiling was hit — tell the caller clearly (429), don't hang.
        return jsonify(ok=False, error="rate_limited", detail=str(e),
                       limit_type=e.limit_type), 429
    except llm_router.LlmRouterError as e:
        return jsonify(ok=False, error="provider_call_failed", detail=str(e)), 502

    return jsonify(ok=True, result=result)


@admin_bp.get("/pii-rules")
@require_role("super_admin")
def list_pii_rules():

    company_id = request.args.get("company_id", type=int)
    query = PiiRule.query
    if company_id is not None:
        query = query.filter(
            (PiiRule.company_id == company_id) | (PiiRule.company_id.is_(None))
        )
    rules = query.order_by(PiiRule.id).all()
    return jsonify(rules=[r.admin_dict() for r in rules])


@admin_bp.post("/pii-rules")
@require_role("super_admin")
def create_pii_rule():

    data = request.get_json(silent=True) or {}

    entity_name = (data.get("entity_name") or "").strip().upper()
    pattern = (data.get("pattern") or "").strip()
    if not entity_name or not pattern:
        return jsonify(error="missing_field", field="entity_name" if not entity_name else "pattern"), 400


    try:
        re.compile(pattern)
    except re.error as e:
        return jsonify(error="invalid_pattern", detail=str(e)), 400

    company_ids = data.get("company_ids")
    if company_ids:
        if not isinstance(company_ids, list):
            return jsonify(error="invalid_company_ids"), 400
        for cid in company_ids:
            err = _validate_company({"company_id": cid})
            if err:
                return err
        target_ids = company_ids
    elif "company_id" in data:
        err = _validate_company(data)
        if err:
            return err
        target_ids = [data.get("company_id")]
    else:
        target_ids = [None]  # Global

    created = []
    for cid in target_ids:
        rule = PiiRule(
            entity_name=entity_name,
            pattern=pattern,
            score=data.get("score", 0.85),
            enabled=data.get("enabled", True),
            company_id=cid,
            created_by=g.current_user.id,
        )
        db.session.add(rule)
        created.append(rule)
    db.session.commit()
    return jsonify(rules=[r.admin_dict() for r in created]), 201


@admin_bp.put("/pii-rules/<int:rule_id>")
@require_role("super_admin")
def update_pii_rule(rule_id):
    rule = db.session.get(PiiRule, rule_id)
    if rule is None:
        return jsonify(error="pii_rule_not_found"), 404

    data = request.get_json(silent=True) or {}

    err = _validate_company(data)
    if err:
        return err

    if "pattern" in data:
        pattern = (data["pattern"] or "").strip()
        try:
            re.compile(pattern)
        except re.error as e:
            return jsonify(error="invalid_pattern", detail=str(e)), 400
        rule.pattern = pattern
    if "entity_name" in data:
        entity_name = (data["entity_name"] or "").strip().upper()
        if not entity_name:
            return jsonify(error="missing_field", field="entity_name"), 400
        rule.entity_name = entity_name
    if "score" in data:
        rule.score = data["score"]
    if "enabled" in data:
        rule.enabled = data["enabled"]
    if "company_id" in data:
        rule.company_id = data["company_id"]

    db.session.commit()
    return jsonify(rule=rule.admin_dict())


@admin_bp.delete("/pii-rules/<int:rule_id>")
@require_role("super_admin")
def delete_pii_rule(rule_id):
    rule = db.session.get(PiiRule, rule_id)
    if rule is None:
        return jsonify(error="pii_rule_not_found"), 404
    db.session.delete(rule)
    db.session.commit()
    return jsonify(deleted=rule_id)


def _parse_since(raw):

    if not raw:
        return None
    if raw.isdigit():
        return datetime.now(timezone.utc) - timedelta(days=int(raw))
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


@admin_bp.get("/usage")
@require_role("super_admin")
def usage_report():
    """Aggregate token usage for the dashboard .

    returns overall totals plus per-company and per-provider breakdowns.
    """
    company_id = request.args.get("company_id", type=int)
    provider_id = request.args.get("provider_id", type=int)
    since = _parse_since(request.args.get("since"))

    summary = usage.usage_summary(
        company_id=company_id, provider_id=provider_id, since=since
    )
    return jsonify(summary)


@admin_bp.get("/feedback")
@require_role("super_admin")
def feedback_report():
    """answer quality feedback  for the dashboard.


    """
    company_id = request.args.get("company_id", type=int)
    provider_id = request.args.get("provider_id", type=int)
    since = _parse_since(request.args.get("since"))

    summary = feedback.feedback_summary(
        company_id=company_id, provider_id=provider_id, since=since
    )
    return jsonify(summary)


_DEFAULT_ADMIN_PASSWORD = "password123"  # dev only


def _ensure_company_admin(company: Company) -> User | None:
    """Create admin@domain  for a company that has none.


    """
    if not company.domain:
        return None
    if User.query.filter_by(company_id=company.id, role="company_admin").first():
        return None
    email = f"admin@{company.domain}"
    if User.query.filter_by(email=email).first():
        return None
    admin = User(email=email, role="company_admin", company_id=company.id)
    admin.set_password(_DEFAULT_ADMIN_PASSWORD)
    db.session.add(admin)
    return admin


def _company_dict(c: Company) -> dict:
    """Admin view of a company: identity, email domain, caps and KB isolation."""
    return {
        "id": c.id,
        "name": c.name,
        "domain": c.domain,
        "daily_token_limit": c.daily_token_limit,
        "daily_request_limit": c.daily_request_limit,
        # Where this tenant's vectors live. The URL is included because "dedicated"
        # alone doesn't tell an operator which container to back up or restart.
        "isolation": c.isolation,
        "qdrant_url": c.qdrant_url,
    }


@admin_bp.get("/qdrant-pool")
@require_role("super_admin")
def qdrant_pool_status():
    """How many dedicated Qdrant instances exist and which are free.


    """
    return jsonify(qdrant_pool.pool_status())


@admin_bp.get("/companies")
@require_role("super_admin")
def list_companies():

    companies = Company.query.order_by(Company.name).all()
    return jsonify(companies=[_company_dict(c) for c in companies])


@admin_bp.post("/companies")
@require_role("super_admin")
def create_company():

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    domain = (data.get("domain") or "").strip().lower() or None
    isolation = (data.get("isolation") or "shared").strip().lower()
    if not name:
        return jsonify(error="missing_field", field="name"), 400
    if isolation not in ("shared", "dedicated"):
        return jsonify(error="invalid_isolation", isolation=isolation,
                       allowed=["shared", "dedicated"]), 400
    if domain and Company.query.filter_by(domain=domain).first():
        return jsonify(error="domain_taken", domain=domain), 409
    if Company.query.filter_by(name=name).first():
        return jsonify(error="name_taken", name=name), 409


    dedicated_url = None
    if isolation == "dedicated":
        dedicated_url = qdrant_pool.claim_url()
        if dedicated_url is None:
            configured = len(qdrant_pool.configured_urls())
            return jsonify(
                error="no_dedicated_instance_available",
                detail=(
                    "Every dedicated Qdrant instance is already assigned."
                    if configured
                    else "No dedicated Qdrant instances are configured "
                         "(QDRANT_DEDICATED_URLS is empty)."
                ),
                configured=configured,
            ), 409

    company = Company(
        name=name,
        domain=domain,
        daily_token_limit=data.get("daily_token_limit"),
        daily_request_limit=data.get("daily_request_limit"),
        qdrant_url=dedicated_url,
    )
    db.session.add(company)
    db.session.flush()
    company.assign_collection_name()

    if dedicated_url is not None:

        try:
            qdrant_pool.assert_url_unclaimed(dedicated_url, exclude_company_id=company.id)
        except ValueError:
            db.session.rollback()
            return jsonify(error="no_dedicated_instance_available",
                           detail="That instance was claimed by another request."), 409


    _ensure_company_admin(company)

    db.session.commit()


    warning = None
    try:
        rag.get_or_create_company_collection(company.id)
    except Exception as exc:  # noqa: BLE001
        current_app.logger.warning(
            "company %s created but its Qdrant collection was not (%s): %s",
            company.id, company.qdrant_url or "shared instance", exc
        )
        warning = "company_created_without_collection"

    body = {"company": _company_dict(company)}
    if warning:
        body["warning"] = warning
    return jsonify(body), 201


@admin_bp.put("/companies/<int:company_id>")
@require_role("super_admin")
def update_company(company_id):
    """Update a company's name, domain, or daily governance caps """
    company = db.session.get(Company, company_id)
    if company is None:
        return jsonify(error="company_not_found"), 404

    data = request.get_json(silent=True) or {}
    moved_users = {"moved": [], "skipped": []}

    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify(error="missing_field", field="name"), 400
        clash = Company.query.filter_by(name=name).first()
        if clash and clash.id != company.id:
            return jsonify(error="name_taken", name=name), 409
        company.name = name
    if "domain" in data:
        domain = (data.get("domain") or "").strip().lower() or None
        if domain:
            clash = Company.query.filter_by(domain=domain).first()
            if clash and clash.id != company.id:
                return jsonify(error="domain_taken", domain=domain), 409

        moved_users = tenancy.move_users_to_domain(company, company.domain, domain)
        company.domain = domain
    if "daily_token_limit" in data:
        company.daily_token_limit = data.get("daily_token_limit")
    if "daily_request_limit" in data:
        company.daily_request_limit = data.get("daily_request_limit")

    db.session.commit()
    return jsonify(company=_company_dict(company), users=moved_users)


@admin_bp.get("/ingestions")
@require_role("super_admin")
def list_ingestions():

    company_id = request.args.get("company_id", type=int)
    q = KbIngestion.query
    if company_id is not None:
        q = q.filter(KbIngestion.company_id == company_id)
    rows = q.order_by(KbIngestion.created_at.desc()).limit(200).all()
    return jsonify(
        ingestions=[
            {
                "id": r.id,
                "company_id": r.company_id,
                "document_id": r.document_id,
                "user_id": r.user_id,
                "filename": r.filename,
                "chunks_indexed": r.chunks_indexed,
                "chunks_blocked": r.chunks_blocked,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    )


@admin_bp.get("/deletions")
@require_role("super_admin")
def list_deletions():

    company_id = request.args.get("company_id", type=int)
    q = KbDeletion.query
    if company_id is not None:
        q = q.filter(KbDeletion.company_id == company_id)
    rows = q.order_by(KbDeletion.created_at.desc()).limit(200).all()
    return jsonify(
        deletions=[
            {
                "id": r.id,
                "company_id": r.company_id,
                "document_id": r.document_id,
                "user_id": r.user_id,
                "filename": r.filename,
                "chunks_deleted": r.chunks_deleted,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    )
