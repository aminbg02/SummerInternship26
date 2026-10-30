"""Shared validation for per-user daily token caps .

"""
from ..extensions import db
from ..models import Company, User


def company_ceiling(company_id):
    """The tenant pool a member's cap may not exceed. None = company is uncapped."""
    if company_id is None:
        return None
    company = db.session.get(Company, company_id)
    return company.daily_token_limit if company is not None else None


def company_allocated(company_id, exclude_user_id=None):
    """Sum of explicit daily_token_limit caps already handed to this company's

    """
    q = User.query.filter_by(company_id=company_id, role="customer").filter(
        User.daily_token_limit.isnot(None)
    )
    if exclude_user_id is not None:
        q = q.filter(User.id != exclude_user_id)
    return sum(u.daily_token_limit for u in q.all())


def validate_token_limit(raw, company_id, *, role="customer", exclude_user_id=None):

    from flask import jsonify

    if raw is None:
        return None, None

    if isinstance(raw, bool):
        return None, (jsonify(error="invalid_token_limit"), 400)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None, (jsonify(error="invalid_token_limit"), 400)
    if value < 0:
        return None, (jsonify(error="invalid_token_limit"), 400)

    ceiling = company_ceiling(company_id)
    if ceiling and (value == 0 or value > ceiling):
        return None, (
            jsonify(
                error="cap_exceeds_company_limit",
                company_limit=ceiling,
                requested="unlimited" if value == 0 else value,
            ),
            400,
        )

    if ceiling and value and role == "customer":
        already = company_allocated(company_id, exclude_user_id=exclude_user_id)
        if already + value > ceiling:
            return None, (
                jsonify(
                    error="allocation_exceeds_company_limit",
                    company_limit=ceiling,
                    already_allocated=already,
                    remaining=max(ceiling - already, 0),
                    requested=value,
                ),
                400,
            )
    return value, None
