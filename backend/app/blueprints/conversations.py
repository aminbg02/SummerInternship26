"""Chat history: list, open, and delete the caller's own conversations.

"""
from flask import Blueprint, g, jsonify, request

from ..extensions import db
from ..models import Conversation, Message, StagedChunk, TokenUsage
from ..security import current_company_id, require_auth

conversations_bp = Blueprint("conversations", __name__, url_prefix="/api/conversations")

# how many charachters we use as title for convo
TITLE_MAX = 80

TITLE_LIMIT = 300


def _owned(conversation_id, company_id):
    """Fetch a conversation the caller actually owns, else None.
    """
    convo = db.session.get(Conversation, conversation_id)
    if convo is None:
        return None
    if convo.company_id != company_id or convo.user_id != g.current_user.id:
        return None
    return convo


def _summary(convo, last_at=None, count=None):
    return {
        "id": convo.id,
        "title": convo.title or "New chat",
        "created_at": convo.created_at.isoformat(),
        "last_at": (last_at or convo.created_at).isoformat(),
        "message_count": count if count is not None else 0,
    }


@conversations_bp.get("")
@require_auth
def list_conversations():

    company_id, err = current_company_id()
    if err:
        return err

    stats = dict(
        (row.conversation_id, row)
        for row in db.session.query(
            Message.conversation_id,
            db.func.count(Message.id).label("count"),
            db.func.max(Message.created_at).label("last_at"),
        )
        .join(Conversation, Conversation.id == Message.conversation_id)
        .filter(
            Conversation.company_id == company_id,
            Conversation.user_id == g.current_user.id,
        )
        .group_by(Message.conversation_id)
        .all()
    )

    convos = (
        Conversation.query.filter_by(
            company_id=company_id, user_id=g.current_user.id
        )
        .filter(Conversation.id.in_(stats.keys()) if stats else db.false())
        .all()
    )

    out = [
        _summary(c, last_at=stats[c.id].last_at, count=stats[c.id].count)
        for c in convos
    ]
    out.sort(key=lambda c: c["last_at"], reverse=True)
    return jsonify(conversations=out)


@conversations_bp.get("/<int:conversation_id>")
@require_auth
def get_conversation(conversation_id):
    company_id, err = current_company_id()
    if err:
        return err

    convo = _owned(conversation_id, company_id)
    if convo is None:
        return jsonify(error="conversation_not_found"), 404

    messages = (
        Message.query.filter_by(conversation_id=convo.id)
        .order_by(Message.created_at, Message.id)
        .all()
    )
    return jsonify(
        conversation=_summary(convo, count=len(messages)),
        messages=[
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "sources": m.sources or [],
                "feedback": m.feedback,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    )


# Accepted thumbs values: a vote, or None to clear one (toggle off).
_FEEDBACK_VALUES = ("up", "down", None)


@conversations_bp.post("/<int:conversation_id>/messages/<int:message_id>/feedback")
@require_auth
def set_message_feedback(conversation_id, message_id):
    """Record the caller's thumbs on one assistant answer
    """
    company_id, err = current_company_id()
    if err:
        return err

    convo = _owned(conversation_id, company_id)
    if convo is None:
        return jsonify(error="conversation_not_found"), 404

    message = db.session.get(Message, message_id)
    if message is None or message.conversation_id != convo.id:
        return jsonify(error="message_not_found"), 404
    if message.role != "assistant":
        return jsonify(error="feedback_assistant_only"), 400

    data = request.get_json(silent=True) or {}
    value = data.get("value")
    if value not in _FEEDBACK_VALUES:
        return jsonify(error="invalid_feedback"), 400

    message.feedback = value
    db.session.commit()
    return jsonify(message_id=message.id, feedback=message.feedback)


@conversations_bp.patch("/<int:conversation_id>")
@require_auth
def rename_conversation(conversation_id):
    """Rename an owned thread.
    """
    company_id, err = current_company_id()
    if err:
        return err

    convo = _owned(conversation_id, company_id)
    if convo is None:
        return jsonify(error="conversation_not_found"), 404

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        # An empty title would render as a blank row; keep the old one instead.
        return jsonify(error="title_required"), 400

    convo.title = title[:TITLE_LIMIT]
    db.session.commit()
    return jsonify(conversation=_summary(convo))


@conversations_bp.delete("/<int:conversation_id>")
@require_auth
def delete_conversation(conversation_id):
    """delete an owned thread and everything hanging off it.
    """
    company_id, err = current_company_id()
    if err:
        return err

    convo = _owned(conversation_id, company_id)
    if convo is None:
        return jsonify(error="conversation_not_found"), 404

    TokenUsage.query.filter_by(conversation_id=convo.id).update(
        {"conversation_id": None}
    )
    Message.query.filter_by(conversation_id=convo.id).delete()
    StagedChunk.query.filter_by(conversation_id=convo.id).delete()
    db.session.delete(convo)
    db.session.commit()
    return jsonify(deleted=conversation_id)
