"""delete staged upload chunks past their TTL.

"""
from datetime import datetime, timezone

from ..extensions import db
from ..models import StagedChunk


def purge_expired_staged_chunks(now=None) -> int:
    """Delete staged chunks whose TTL has passed; return the row count.


    """
    now = now or datetime.now(timezone.utc)

    deleted = (
        StagedChunk.query.filter(
            StagedChunk.expires_at.isnot(None),
            StagedChunk.expires_at <= now,
        ).delete(synchronize_session=False)
    )
    db.session.commit()
    return deleted
