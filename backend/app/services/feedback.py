"""Answer-quality feedback aggregation for the admin dashboard.

"""
from sqlalchemy import case, func

from ..extensions import db
from ..models import Company, Conversation, LlmProvider, Message


_UP = func.coalesce(func.sum(case((Message.feedback == "up", 1), else_=0)), 0)
_DOWN = func.coalesce(func.sum(case((Message.feedback == "down", 1), else_=0)), 0)
_ANSWERS = func.count(Message.id)

_REVIEW_LIMIT = 50
_CONTENT_PREVIEW = 400


def _apply(q, company_id=None, provider_id=None, since=None):

    q = q.join(Conversation, Message.conversation_id == Conversation.id).filter(
        Message.role == "assistant"
    )
    if company_id is not None:
        q = q.filter(Conversation.company_id == company_id)
    if provider_id is not None:
        q = q.filter(Message.provider_id == provider_id)
    if since is not None:
        q = q.filter(Message.created_at >= since)
    return q


def _score(up: int, down: int):
    """Satisfaction as a percent of rated answers, or None when nothing is rated."""
    rated = up + down
    if rated == 0:
        return None
    return round(up * 100 / rated)


def _tally(up, down, answers) -> dict:
    up, down, answers = int(up or 0), int(down or 0), int(answers or 0)
    return {
        "up": up,
        "down": down,
        "rated": up + down,
        "answers": answers,
        "score": _score(up, down),
    }


def _grouped(column, names, noun, company_id, provider_id, since):
    """up/down/answers per value of `column` (provider_id or company_id).


    """
    rows = (
        _apply(
            db.session.query(column, _UP, _DOWN, _ANSWERS),
            company_id, provider_id, since,
        )
        .group_by(column)
        .all()
    )
    out = []
    for key, up, down, answers in rows:
        row = _tally(up, down, answers)
        row["id"] = key
        # A feedback row outlives what it points at (deleting a provider/company does not
        # delete its answers), so fall back rather than show a blank.
        if key is None:
            row["name"] = f"(no {noun.lower()})"
        else:
            row["name"] = names.get(key) or f"{noun} #{key} (deleted)"
        out.append(row)
    out.sort(key=lambda r: (r["rated"], r["down"]), reverse=True)
    return out


def _review_queue(company_names, provider_names, company_id, provider_id, since):
    """The most recent thumbs-DOWN answers, with the sources they were grounded on."""
    rows = (
        _apply(
            db.session.query(Message, Conversation.company_id),
            company_id, provider_id, since,
        )
        .filter(Message.feedback == "down")
        .order_by(Message.created_at.desc())
        .limit(_REVIEW_LIMIT)
        .all()
    )
    review = []
    for msg, comp_id in rows:
        pid = msg.provider_id
        review.append(
            {
                "message_id": msg.id,
                "conversation_id": msg.conversation_id,
                "company_id": comp_id,
                "company_name": company_names.get(comp_id) or f"Company #{comp_id} (deleted)",
                "provider_id": pid,
                "provider_name": (
                    "(no model)" if pid is None
                    else provider_names.get(pid) or f"Provider #{pid} (deleted)"
                ),
                "content": (msg.content or "")[:_CONTENT_PREVIEW],
                "sources": msg.sources or [],
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            }
        )
    return review


def feedback_summary(company_id=None, provider_id=None, since=None) -> dict:
    """Aggregate answer feedback for the admin dashboard.

    """
    up, down, answers = _apply(
        db.session.query(_UP, _DOWN, _ANSWERS), company_id, provider_id, since
    ).one()


    company_names = {c.id: c.name for c in Company.query.all()}
    provider_names = {p.id: p.display_name for p in LlmProvider.query.all()}

    return {
        "total": _tally(up, down, answers),
        "by_provider": _grouped(
            Message.provider_id, provider_names, "Provider",
            company_id, provider_id, since,
        ),
        "by_company": _grouped(
            Conversation.company_id, company_names, "Company",
            company_id, provider_id, since,
        ),
        "review": _review_queue(
            company_names, provider_names, company_id, provider_id, since
        ),
    }
