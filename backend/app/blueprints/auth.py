"""Authentication: login, JWT issuance, and a /me probe.

JWT carries the user id as identity plus role + company_id .
"""
from flask import Blueprint, g, jsonify, request
from flask_jwt_extended import create_access_token

from ..models import User
from ..security import require_auth

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()

    if user is None or not user.check_password(password):
        return jsonify(error="invalid_credentials"), 401

    token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role, "company_id": user.company_id},
    )
    return jsonify(
        access_token=token,
        user={
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "company_id": user.company_id,
        },
    )


@auth_bp.get("/me")
@require_auth
def me():

    u = g.current_user
    return jsonify(
        id=u.id,
        email=u.email,
        role=u.role,
        company_id=u.company_id,
    )
