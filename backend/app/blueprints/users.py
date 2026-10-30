"""
defines the users hierarchy the superadmin can create anyone
the company admin can only create new customers for their OWN company
the customer can create nobody
"""
from flask import Blueprint, g, jsonify, request

from ..extensions import db
from ..models import (
    Company,
    Conversation,
    Document,
    KbDeletion,
    KbIngestion,
    LlmProvider,
    Message,
    StagedChunk,
    TokenUsage,
    User,
)
from ..security import require_auth
from ..services import tenancy, token_caps, usage

users_bp = Blueprint("users", __name__, url_prefix="/api/users")

_ROLES = ("super_admin", "company_admin", "customer")
_MIN_PASSWORD = 6


def _authorize_cap_change(caller: User, target: User):
    """error response if `caller` may not set `target`'s cap, else None."""
    if target.is_super_admin:
        return jsonify(error="super_admin_not_capped"), 400
    if caller.is_super_admin:
        return None
    """a company admin can not cap another company admin limit and we treat the case if the company admin wants to cap another company """
    if caller.is_company_admin:
        if target.role != "customer" or target.company_id != caller.company_id:
            return jsonify(error="forbidden",
                           detail="company_admin can only cap their own customers"), 403
        return None
    return jsonify(error="forbidden"), 403


def _user_dict(u: User) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "role": u.role,
        "company_id": u.company_id,
        "daily_token_limit": u.daily_token_limit,
        "effective_token_limit": usage.effective_user_limit(u),
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


@users_bp.get("")
@require_auth
def list_users():
    """List users the caller is allowed to see.

    super_admin -> everyone; company_admin -> only their own company; anyone else
    is forbidden
    """
    caller = g.current_user
    if caller.is_super_admin:
        rows = User.query.order_by(User.id).all()
    elif caller.is_company_admin:
        rows = (
            User.query.filter_by(company_id=caller.company_id)
            .order_by(User.id)
            .all()
        )
    else:
        return jsonify(error="forbidden"), 403

    company_ids = {u.company_id for u in rows if u.company_id is not None}
    company_limits = {
        c.id: c.daily_token_limit
        for c in Company.query.filter(Company.id.in_(company_ids)).all()
    } if company_ids else {}

    company_allocated = {cid: token_caps.company_allocated(cid) for cid in company_ids}

    return jsonify(
        users=[_user_dict(u) for u in rows],
        company_limits=company_limits,
        company_allocated=company_allocated,
    )


@users_bp.post("")
@require_auth
def create_user():

    caller = g.current_user
    if not (caller.is_super_admin or caller.is_company_admin):
        return jsonify(error="forbidden"), 403

    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    requested_role = (data.get("role") or "customer").strip()


    if not email or email.count("@") != 1:
        return jsonify(error="invalid_email"), 400
    if len(password) < _MIN_PASSWORD:
        return jsonify(error="weak_password", min_length=_MIN_PASSWORD), 400
    if requested_role not in _ROLES:
        return jsonify(error="invalid_role", allowed=list(_ROLES)), 400
    if User.query.filter_by(email=email).first():
        return jsonify(error="email_taken"), 409

    domain = tenancy.domain_of_email(email)
    if domain is None:
        return jsonify(error="invalid_email"), 400


    if caller.is_company_admin:

        if requested_role != "customer":
            return jsonify(error="forbidden_role",
                           detail="company_admin can only create customers"), 403
        company = db.session.get(Company, caller.company_id)
        if company is None:
            return jsonify(error="user_without_company"), 400

        if company.domain and domain != company.domain:
            return jsonify(error="email_domain_mismatch",
                           expected=company.domain, got=domain), 400
        role = "customer"
        company_id = company.id
    else:

        role = requested_role
        if role == "super_admin":
            company_id = None
        else:
            company = tenancy.get_or_create_company_by_domain(domain)
            company_id = company.id


    requested_limit = data.get("daily_token_limit")
    if role == "super_admin" and requested_limit is not None:
        return jsonify(error="super_admin_not_capped"), 400
    daily_token_limit, limit_error = token_caps.validate_token_limit(
        requested_limit, company_id, role=role
    )
    if limit_error:
        return limit_error

    user = User(email=email, role=role, company_id=company_id,
                daily_token_limit=daily_token_limit)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify(user=_user_dict(user)), 201


@users_bp.patch("/<int:user_id>/token-limit")
@require_auth
def set_token_limit(user_id):

    caller = g.current_user
    target = db.session.get(User, user_id)
    if target is None:
        return jsonify(error="user_not_found"), 404

    denied = _authorize_cap_change(caller, target)
    if denied:
        return denied

    data = request.get_json(silent=True) or {}
    if "daily_token_limit" not in data:
        return jsonify(error="missing_field", field="daily_token_limit"), 400


    limit, limit_error = token_caps.validate_token_limit(
        data.get("daily_token_limit"), target.company_id,
        role=target.role, exclude_user_id=target.id,
    )
    if limit_error:
        return limit_error

    target.daily_token_limit = limit
    db.session.commit()
    return jsonify(user=_user_dict(target))


@users_bp.delete("/<int:user_id>")
@require_auth
def delete_user(user_id):
    """delete a user, mirroring the creation hierarchy above.
    super admin can delete anyone but themselves
    company admin can only delete customers of their own company
    customer can delete nobody

    What happens to the user's data:
      token_usage / kb_ingestions / kb_deletions: history and audit outlive the
        actor — user_id is NULLed, the rows (and the usage dashboard's totals) stay.
       documents.created_by / llm_providers.created_by: NULLed, the rows stay.
       conversations + messages: personal chat history, deleted .
    """
    caller = g.current_user
    if not (caller.is_super_admin or caller.is_company_admin):
        return jsonify(error="forbidden"), 403

    target = db.session.get(User, user_id)
    if target is None:
        return jsonify(error="user_not_found"), 404
    if target.id == caller.id:
        return jsonify(error="cannot_delete_self"), 400
    if caller.is_company_admin and (
        target.role != "customer" or target.company_id != caller.company_id
    ):
        return jsonify(error="forbidden"), 403

    TokenUsage.query.filter_by(user_id=user_id).update(
        {"user_id": None}, synchronize_session=False
    )
    KbIngestion.query.filter_by(user_id=user_id).update(
        {"user_id": None}, synchronize_session=False
    )
    KbDeletion.query.filter_by(user_id=user_id).update(
        {"user_id": None}, synchronize_session=False
    )
    Document.query.filter_by(created_by=user_id).update(
        {"created_by": None}, synchronize_session=False
    )
    LlmProvider.query.filter_by(created_by=user_id).update(
        {"created_by": None}, synchronize_session=False
    )


    convo_ids = [
        row[0]
        for row in Conversation.query.filter_by(user_id=user_id)
        .with_entities(Conversation.id)
        .all()
    ]
    if convo_ids:
        TokenUsage.query.filter(TokenUsage.conversation_id.in_(convo_ids)).update(
            {"conversation_id": None}, synchronize_session=False
        )

        StagedChunk.query.filter(StagedChunk.conversation_id.in_(convo_ids)).delete(
            synchronize_session=False
        )
        Message.query.filter(Message.conversation_id.in_(convo_ids)).delete(
            synchronize_session=False
        )
        Conversation.query.filter(Conversation.id.in_(convo_ids)).delete(
            synchronize_session=False
        )

    db.session.delete(target)
    db.session.commit()
    return jsonify(deleted=user_id)
