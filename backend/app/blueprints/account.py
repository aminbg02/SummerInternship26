
from flask import Blueprint, g, jsonify

from ..security import require_auth
from ..services import usage
account_bp = Blueprint("account", __name__, url_prefix="/api/account")

@account_bp.get("/usage")
@require_auth
def my_usage():
    """
    shows this user's token usage in the current 24hours compared to the daily cap
    returns {used, limit, remaining, percent}. limit=null means the user is
    uncapped (percent stays 0). pushes  the chat "tokens used today" progress bar

    """
    user = g.current_user
    snapshot = usage.user_daily_usage(user)
    return jsonify(
        user_id=user.id,
        role=user.role,
        company_id=user.company_id,
        **snapshot,
    )
