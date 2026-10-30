"""
security rules ,the company id is ALWYAS taken from an authenticated user never from the request body
every customer and user of a company must be linked to a company only super admin doesnt have one
"""
from functools import wraps

from flask import g, jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from .extensions import db
from .models import Company, User


def _load_current_user():
    """
    we load the user data from the jwt token , every query we check the the user row in case they get demoted/fired mid convoersation
    """
    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id)) if user_id is not None else None
    g.current_user = user
    return user


def require_auth(fn):

    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user = _load_current_user()
        if user is None:
            return jsonify(error="user_not_found"), 401
        return fn(*args, **kwargs)

    return wrapper


def require_role(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user = _load_current_user()
            if user is None:
                return jsonify(error="user_not_found"), 401
            if user.role not in roles:
                return jsonify(error="forbidden", required_roles=list(roles)), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def current_company_id():
    """determine the company  for this request. returns (company_id, error_response).
    """
    user = getattr(g, "current_user", None)
    if user is None:
        return None, (jsonify(error="not_authenticated"), 401)


    if user.is_company_bound:
        if user.company_id is None:
            return None, (jsonify(error="user_without_company"), 400)
        return user.company_id, None

    # super_admin case
    raw = request.headers.get("X-Company-Id")
    if not raw:
        return None, (
            jsonify(error="admin_must_select_company",
                    hint="send X-Company-Id header"),
            400,
        )
    try:
        company_id = int(raw)
    except (TypeError, ValueError):
        return None, (jsonify(error="invalid_company_id"), 400)

    if db.session.get(Company, company_id) is None:
        return None, (jsonify(error="company_not_found"), 404)
    return company_id, None
