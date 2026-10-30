"""The provider list the customer's model dropdown is built from.

Enabled rows only, and only the safe fields

"""
from flask import Blueprint, g, jsonify

from ..extensions import db
from ..models import LlmProvider
from ..security import require_auth
from ..services import usage

providers_bp = Blueprint("providers", __name__, url_prefix="/api")


def resolve_enabled_provider(provider_id, company_id):

    provider = db.session.get(LlmProvider, provider_id)
    if provider is None or not provider.enabled:
        return None
    if provider.company_id is not None and provider.company_id != company_id:
        return None
    return provider


def enabled_providers_for(company_id):
    """Usable providers in fallback order (lowest priority number first)"""
    return (
        LlmProvider.query.filter(LlmProvider.enabled.is_(True))
        .filter(
            db.or_(
                LlmProvider.company_id.is_(None),
                LlmProvider.company_id == company_id,
            )
        )
        .order_by(LlmProvider.priority, LlmProvider.id)
        .all()
    )


@providers_bp.get("/llm-providers")
@require_auth
def list_providers():
    company_id = getattr(g.current_user, "company_id", None)

    query = LlmProvider.query.filter(LlmProvider.enabled.is_(True))
    query = query.filter(
        db.or_(
            LlmProvider.company_id.is_(None),
            LlmProvider.company_id == company_id,
        )
    )
    providers = query.order_by(LlmProvider.priority, LlmProvider.id).all()


    out = []
    for p in providers:
        row = p.public_dict()
        row.update(usage.provider_availability(p))
        out.append(row)
    return jsonify(providers=out)
