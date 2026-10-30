"""Allocation of dedicated Qdrant instances to tenants.

"""
from flask import current_app

from ..models import Company


def configured_urls() -> list[str]:
    """Every dedicated slot this deployment has, in configured order."""
    return list(current_app.config.get("QDRANT_DEDICATED_URLS") or [])


def claimed_urls() -> set[str]:
    """Slots already belonging to a company.

    """
    rows = (
        Company.query.with_entities(Company.qdrant_url)
        .filter(Company.qdrant_url.isnot(None))
        .all()
    )
    return {url for (url,) in rows}


def free_urls() -> list[str]:
    """Slots that exist and nobody holds, in configured order."""
    taken = claimed_urls()
    return [u for u in configured_urls() if u not in taken]


def claim_url() -> str | None:
    """Take the first free slot, or None if the pool is exhausted.


    """
    free = free_urls()
    return free[0] if free else None


def assert_url_unclaimed(url: str, *, exclude_company_id: int | None = None) -> None:
    """Raise ValueError if `url` already belongs to a company.
    """
    query = Company.query.filter(Company.qdrant_url == url)
    if exclude_company_id is not None:
        query = query.filter(Company.id != exclude_company_id)
    holder = query.first()
    if holder is not None:
        raise ValueError(
            f"Qdrant instance {url} is already dedicated to company "
            f"{holder.id} ({holder.name!r})"
        )


def pool_status() -> dict:
    """Reports the state of the dedicated-Qdrant pool,
    so the admin UI knows whether it can even offer "dedicated" when creating a company


    """
    holders = {
        c.qdrant_url: {"company_id": c.id, "company_name": c.name}
        for c in Company.query.filter(Company.qdrant_url.isnot(None)).all()
    }
    urls = configured_urls()
    return {
        "configured": len(urls),
        "free": len([u for u in urls if u not in holders]),
        "available": any(u not in holders for u in urls),
        "slots": [
            {"url": u, "claimed_by": holders.get(u)}
            for u in urls
        ],
    }
