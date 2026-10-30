"""

Token-cap request flow
the user can ask their company admin to raise their personal daily token limit
a company can ask the super admin to raise the company's daily token

"""
from datetime import datetime, timezone

from flask import Blueprint, g, jsonify, request

from ..extensions import db
from ..models import Company, TokenRequest, User
from ..security import require_auth
from ..services import token_caps

token_requests_bp = Blueprint(
    "token_requests", __name__, url_prefix="/api/token-requests"
)

_STATUSES = ("approved", "rejected")


def _utcnow():
    return datetime.now(timezone.utc)


def _validate_requested_limit(raw):
    """A request just needs a sane non-negative integer """
    if raw is None:
        return None, (jsonify(error="missing_field", field="requested_limit"), 400)
    if isinstance(raw, bool):
        return None, (jsonify(error="invalid_requested_limit"), 400)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None, (jsonify(error="invalid_requested_limit"), 400)
    if value < 0:
        return None, (jsonify(error="invalid_requested_limit"), 400)
    return value, None


def _request_dict(r: TokenRequest, emails: dict, company_names: dict) -> dict:
    return {
        "id": r.id,
        "requester_id": r.requester_id,
        "requester_email": emails.get(r.requester_id),
        "company_id": r.company_id,
        "company_name": company_names.get(r.company_id),
        "scope": r.scope,
        "requested_limit": r.requested_limit,
        "reason": r.reason,
        "status": r.status,
        "decision_reason": r.decision_reason,
        "reviewed_by": r.reviewed_by,
        "reviewed_by_email": emails.get(r.reviewed_by),
        "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def _serialize(rows: list) -> list:
    """get a list to match every requester and reviewr,one batch to avoid querying multiple times """
    user_ids = {r.requester_id for r in rows} | {r.reviewed_by for r in rows if r.reviewed_by}
    company_ids = {r.company_id for r in rows}
    emails = {
        u.id: u.email for u in User.query.filter(User.id.in_(user_ids)).all()
    } if user_ids else {}
    company_names = {
        c.id: c.name for c in Company.query.filter(Company.id.in_(company_ids)).all()
    } if company_ids else {}
    return [_request_dict(r, emails, company_names) for r in rows]


@token_requests_bp.get("")
@require_auth
def list_requests():
    """list the requests the caller is allowed to see.

    customer can only see their own
    company_admin can see the  pending user requests from their OWN company

                       their own  requests to the super_admin.
     super_admin everyone's  requests

    """
    caller = g.current_user
    if caller.is_super_admin:
        rows = TokenRequest.query.order_by(TokenRequest.created_at.desc()).all()
    elif caller.is_company_admin:
        rows = (
            TokenRequest.query.filter(
                db.or_(
                    db.and_(
                        TokenRequest.scope == "user",
                        TokenRequest.company_id == caller.company_id,
                    ),
                    TokenRequest.requester_id == caller.id,
                )
            )
            .order_by(TokenRequest.created_at.desc())
            .all()
        )
    else:
        rows = (
            TokenRequest.query.filter_by(requester_id=caller.id)
            .order_by(TokenRequest.created_at.desc())
            .all()
        )
    return jsonify(requests=_serialize(rows))


@token_requests_bp.post("")
@require_auth
def create_request():


    caller = g.current_user
    if caller.is_super_admin:
        return jsonify(error="forbidden",
                       detail="nobody is above a super_admin to ask"), 403
    if caller.company_id is None:
        return jsonify(error="user_without_company"), 400

    data = request.get_json(silent=True) or {}
    reason = (data.get("reason") or "").strip()
    if not reason:
        return jsonify(error="missing_field", field="reason"), 400

    requested_limit, limit_error = _validate_requested_limit(data.get("requested_limit"))
    if limit_error:
        return limit_error

    scope = "company" if caller.is_company_admin else "user"


    existing = TokenRequest.query.filter_by(
        requester_id=caller.id, scope=scope, status="pending"
    ).first()
    if existing:
        return jsonify(error="request_already_pending", request_id=existing.id), 409

    req = TokenRequest(
        requester_id=caller.id,
        company_id=caller.company_id,
        scope=scope,
        requested_limit=requested_limit,
        reason=reason,
    )
    db.session.add(req)
    db.session.commit()
    return jsonify(request=_serialize([req])[0]), 201


@token_requests_bp.patch("/<int:request_id>")
@require_auth
def decide_request(request_id):

    caller = g.current_user
    req = db.session.get(TokenRequest, request_id)
    if req is None:
        return jsonify(error="request_not_found"), 404
    if req.status != "pending":
        return jsonify(error="request_already_decided"), 409

    if req.scope == "company":
        if not caller.is_super_admin:
            return jsonify(error="forbidden"), 403
    else:  # scope == "user"
        allowed = caller.is_super_admin or (
            caller.is_company_admin and caller.company_id == req.company_id
        )
        if not allowed:
            return jsonify(error="forbidden"), 403

    data = request.get_json(silent=True) or {}
    decision = (data.get("status") or "").strip().lower()
    if decision not in _STATUSES:
        return jsonify(error="invalid_status", allowed=list(_STATUSES)), 400

    decision_reason = (data.get("decision_reason") or "").strip()
    if decision == "rejected" and not decision_reason:
        return jsonify(error="missing_field", field="decision_reason"), 400

    if decision == "approved":
        if req.scope == "user":
            target = db.session.get(User, req.requester_id)
            if target is None:
                return jsonify(error="user_not_found"), 404
            limit, limit_error = token_caps.validate_token_limit(
                req.requested_limit, target.company_id,
                role=target.role, exclude_user_id=target.id,
            )
            if limit_error:
                return limit_error
            target.daily_token_limit = limit
        else:  # scope == "company"
            company = db.session.get(Company, req.company_id)
            if company is None:
                return jsonify(error="company_not_found"), 404

            company.daily_token_limit = (company.daily_token_limit or 0) + req.requested_limit

    req.status = decision
    req.decision_reason = decision_reason or None
    req.reviewed_by = caller.id
    req.reviewed_at = _utcnow()
    db.session.commit()
    return jsonify(request=_serialize([req])[0])
