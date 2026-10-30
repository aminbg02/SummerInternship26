"""Usage tracking + rate limiting
"""
import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy import func

from ..extensions import db
from ..models import Company, LlmProvider, ProviderCallLog, TokenUsage, User
from . import crypto


_MINUTE = timedelta(minutes=1)
_DAY = timedelta(days=1)

_FAILURE_COOLDOWN = timedelta(seconds=60)
_recent_failures: dict = {}


class RateLimitExceeded(Exception):
    """Raised when a provider is at its shared RPM/RPD ceiling"""

    def __init__(self, provider_id, limit_type, limit, window_seconds):
        self.provider_id = provider_id
        self.limit_type = limit_type
        self.limit = limit
        self.window_seconds = window_seconds
        super().__init__(
            f"provider {provider_id} hit its {limit_type} ceiling "
            f"({limit} requests / {window_seconds}s)"
        )


class QuotaExceeded(Exception):
    """Raised when a daily governance cap is hit .
    """

    def __init__(self, subject_id, quota_type, limit, scope="company"):
        self.subject_id = subject_id
        self.company_id = subject_id if scope == "company" else None
        self.quota_type = quota_type  # 'tokens' or 'requests'
        self.limit = limit
        self.scope = scope  # 'company' or 'user'
        super().__init__(
            f"{scope} {subject_id} reached its daily {quota_type} limit ({limit})"
        )


def _now():
    return datetime.now(timezone.utc)



REASON_AT_CAPACITY = "at capacity"
REASON_KEY_REJECTED = "key rejected"
REASON_TIMED_OUT = "timed out"
REASON_UNAVAILABLE = "unavailable"


def _credential_fingerprint(provider) -> str:
    """roduces an anonymous ID for which API key a provider row uses,
     so rows sharing a key can share a rate-limit budget.
    """
    if not provider.api_key_encrypted:
        return ""
    try:
        plaintext = crypto.decrypt(provider.api_key_encrypted)
    except Exception:
        return ""
    if not plaintext:
        return ""
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def rate_limit_peers(provider) -> list:
    """Every provider row that shares this row's RPM/RPD budget.
    """
    group = (provider.rate_limit_group or "").strip()
    if group:
        peers = [
            row_id
            for (row_id,) in db.session.query(LlmProvider.id).filter(
                LlmProvider.rate_limit_group == group
            )
        ]
    else:
        fingerprint = _credential_fingerprint(provider)
        if not fingerprint:
            return [provider.id]

        peers = [
            row.id
            for row in db.session.query(LlmProvider).filter(
                LlmProvider.rate_limit_group.is_(None),
                LlmProvider.api_key_encrypted.isnot(None),
            )
            if _credential_fingerprint(row) == fingerprint
        ]


    if provider.id not in peers:
        peers.append(provider.id)
    return peers


def _provider_calls_since(provider, since: datetime) -> int:
    """Count calls charged to a provider's KEY since `since`.
    """
    return (
        db.session.query(func.count(ProviderCallLog.id))
        .filter(
            ProviderCallLog.provider_id.in_(rate_limit_peers(provider)),
            ProviderCallLog.created_at >= since,
        )
        .scalar()
    ) or 0


def check_provider_rate_limit(provider) -> None:
    """Raise RateLimitExceeded if one more call would breach the RPM/RPD ceiling.
    """
    now = _now()

    if provider.rate_limit_rpm:
        used = _provider_calls_since(provider, now - _MINUTE)
        if used >= provider.rate_limit_rpm:
            raise RateLimitExceeded(provider.id, "rpm", provider.rate_limit_rpm, 60)

    if provider.rate_limit_rpd:
        used = _provider_calls_since(provider, now - _DAY)
        if used >= provider.rate_limit_rpd:
            raise RateLimitExceeded(provider.id, "rpd", provider.rate_limit_rpd, 86400)


def record_provider_call(provider_id: int) -> None:
    """Log one call against a provider (feeds the rate-limit counter above)."""
    db.session.add(ProviderCallLog(provider_id=provider_id))
    db.session.commit()


_COOLDOWN_QUOTA = timedelta(hours=1)  # 429 / quota exhausted / billing
_COOLDOWN_AUTH = timedelta(hours=6)  # 401 / 403 — bad or revoked key
_COOLDOWN_TRANSIENT = _FAILURE_COOLDOWN  # 60s — timeouts, blips


def classify_failure(error_text: str):
    """Turn a provider's raw error into (cooldown, short human reason).
    """
    text = (error_text or "").lower()
    if "429" in text or "quota" in text or "rate limit" in text or "ratelimit" in text:
        return _COOLDOWN_QUOTA, REASON_AT_CAPACITY
    if "401" in text or "403" in text or "unauthor" in text or "invalid api key" in text:
        return _COOLDOWN_AUTH, REASON_KEY_REJECTED
    if "timeout" in text or "timed out" in text:
        return _COOLDOWN_TRANSIENT, REASON_TIMED_OUT
    return _COOLDOWN_TRANSIENT, REASON_UNAVAILABLE


def mark_provider_failed(provider_id: int, error_text: str = "") -> None:

    cooldown, reason = classify_failure(error_text)
    until = _now() + cooldown
    _recent_failures[provider_id] = until

    provider = db.session.get(LlmProvider, provider_id)
    if provider is not None:
        provider.unavailable_until = until
        provider.last_error = reason
        db.session.commit()


def clear_provider_failure(provider_id: int) -> None:
    """Clear the cooldown after a successful call the provider is healthy again."""
    _recent_failures.pop(provider_id, None)

    provider = db.session.get(LlmProvider, provider_id)
    if provider is not None and (provider.unavailable_until or provider.last_error):
        provider.unavailable_until = None
        provider.last_error = None
        db.session.commit()


def provider_availability(provider) -> dict:
    """
    Returns {available: bool, reason: str|None, retry_after: int|None}

    """
    now = _now()


    until = _recent_failures.get(provider.id)
    persisted = provider.unavailable_until
    if persisted is not None:

        if persisted.tzinfo is None:
            persisted = persisted.replace(tzinfo=timezone.utc)
        if until is None or persisted > until:
            until = persisted

    if until is not None:
        if until > now:
            return {
                "available": False,

                "reason": provider.last_error or REASON_UNAVAILABLE,
                "retry_after": max(1, int((until - now).total_seconds())),
            }
        _recent_failures.pop(provider.id, None)  # expired — prune


    if provider.rate_limit_rpm:
        used = _provider_calls_since(provider, now - _MINUTE)
        if used >= provider.rate_limit_rpm:
            return {"available": False, "reason": REASON_AT_CAPACITY, "retry_after": 60}
    if provider.rate_limit_rpd:
        used = _provider_calls_since(provider, now - _DAY)
        if used >= provider.rate_limit_rpd:
            return {"available": False, "reason": REASON_AT_CAPACITY, "retry_after": 3600}

    return {"available": True, "reason": None, "retry_after": None}



def _company_usage_since(company_id: int, since: datetime):
    """Return (total_tokens, request_count) for a company since `since`."""
    tokens, requests = (
        db.session.query(
            func.coalesce(func.sum(TokenUsage.total_tokens), 0),
            func.count(TokenUsage.id),
        )
        .filter(
            TokenUsage.company_id == company_id,
            TokenUsage.created_at >= since,
        )
        .one()
    )
    return int(tokens or 0), int(requests or 0)


def check_company_quota(company_id: int) -> None:
    """Raise QuotaExceeded if the company is over a daily cap it has set.

    """
    company = db.session.get(Company, company_id)
    if company is None:
        return
    if not company.daily_token_limit and not company.daily_request_limit:
        return  # no caps configured — nothing to check

    tokens, requests = _company_usage_since(company_id, _now() - _DAY)

    if company.daily_token_limit and tokens >= company.daily_token_limit:
        raise QuotaExceeded(company_id, "tokens", company.daily_token_limit)
    if company.daily_request_limit and requests >= company.daily_request_limit:
        raise QuotaExceeded(company_id, "requests", company.daily_request_limit)



def _user_tokens_since(user_id: int, since: datetime) -> int:
    """Total tokens this ONE user has spent since `since` (their own calls only)."""
    total = (
        db.session.query(func.coalesce(func.sum(TokenUsage.total_tokens), 0))
        .filter(TokenUsage.user_id == user_id, TokenUsage.created_at >= since)
        .scalar()
    )
    return int(total or 0)


def effective_user_limit(user) -> int:


    if user is None:
        return 0
    if user.is_super_admin:
        return 0
    if user.daily_token_limit is not None:
        return user.daily_token_limit
    from flask import current_app
    return int(current_app.config.get("DEFAULT_USER_DAILY_TOKEN_LIMIT", 0) or 0)


def check_user_quota(user) -> None:
    """Raise QuotaExceeded (scope='user') if this user is at/over their daily cap.
    """
    limit = effective_user_limit(user)
    if not limit:
        return
    used = _user_tokens_since(user.id, _now() - _DAY)
    if used >= limit:
        raise QuotaExceeded(user.id, "tokens", limit, scope="user")


def _quota_snapshot(used: int, limit: int | None) -> dict:
    """used / limit / remaining / percent for one counter. limit falsy = uncapped."""
    if not limit:
        return {"used": used, "limit": None, "remaining": None, "percent": 0}
    return {
        "used": used,
        "limit": limit,
        "remaining": max(0, limit - used),
        "percent": min(100, round(used * 100 / limit)),
    }


def user_daily_usage(user) -> dict:
    """What actually limits this user right now — powers the chat bar.
    """
    user_used = _user_tokens_since(user.id, _now() - _DAY)
    user_snap = _quota_snapshot(user_used, effective_user_limit(user))

    company = db.session.get(Company, user.company_id) if user.company_id else None
    if company is None:
        # A super_admin belongs to no company, so only their own cap can bite.
        return {**user_snap, "blocked_by": _blocker(user_snap), "user": user_snap, "company": None}

    company_used, _ = _company_usage_since(company.id, _now() - _DAY)
    company_snap = _quota_snapshot(company_used, company.daily_token_limit)
    company_snap["name"] = company.name


    candidates = [s for s in (user_snap, company_snap) if s["remaining"] is not None]
    binding = min(candidates, key=lambda s: s["remaining"]) if candidates else user_snap

    return {
        "used": binding["used"],
        "limit": binding["limit"],
        "remaining": binding["remaining"],
        "percent": binding["percent"],
        "blocked_by": _blocker(binding),
        "scope": "company" if binding is company_snap else "user",
        "user": user_snap,
        "company": company_snap,
    }


def _blocker(snap: dict) -> bool:
    """True when this counter has no headroom left — the next call is refused."""
    return snap["remaining"] is not None and snap["remaining"] <= 0


def estimate_tokens(text: str) -> int:
    """Rough token estimate when a provider omits its usage field (~4 chars/token)"""
    if not text:
        return 0
    return max(1, len(text) // 4)


def log_token_usage(company_id, user_id, provider_id, conversation_id, result, messages):
    """Write one token_usage row for a completed call.
    """
    prompt_tokens = result.get("prompt_tokens")
    completion_tokens = result.get("completion_tokens")
    reasoning_tokens = result.get("reasoning_tokens") or 0

    if prompt_tokens is None:
        prompt_text = " ".join(m.get("content", "") for m in messages)
        prompt_tokens = estimate_tokens(prompt_text)
    if completion_tokens is None:
        completion_tokens = estimate_tokens(result.get("content", ""))

    total = result.get("total_tokens")
    if total is None:
        total = prompt_tokens + completion_tokens + reasoning_tokens

    db.session.add(
        TokenUsage(
            company_id=company_id,
            user_id=user_id,
            provider_id=provider_id,
            conversation_id=conversation_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            reasoning_tokens=reasoning_tokens,
            total_tokens=total,
        )
    )
    db.session.commit()


def _totals_query(company_id=None, provider_id=None, since=None):
    q = db.session.query(
        func.coalesce(func.sum(TokenUsage.prompt_tokens), 0),
        func.coalesce(func.sum(TokenUsage.completion_tokens), 0),
        # coalesce covers rows written before the column existed (they read NULL).
        func.coalesce(func.sum(TokenUsage.reasoning_tokens), 0),
        func.coalesce(func.sum(TokenUsage.total_tokens), 0),
        func.count(TokenUsage.id),
    )
    if company_id is not None:
        q = q.filter(TokenUsage.company_id == company_id)
    if provider_id is not None:
        q = q.filter(TokenUsage.provider_id == provider_id)
    if since is not None:
        q = q.filter(TokenUsage.created_at >= since)
    return q


def usage_summary(company_id=None, provider_id=None, since=None) -> dict:
    """Aggregate token_usage for the admin dashboard.


    """
    p, c, r, t, n = _totals_query(company_id, provider_id, since).one()
    total = {
        "prompt_tokens": int(p),
        "completion_tokens": int(c),
        "reasoning_tokens": int(r),
        "total_tokens": int(t),
        "requests": int(n),
    }

    company_names = {c_.id: c_.name for c_ in Company.query.all()}
    provider_names = {p_.id: p_.display_name for p_ in LlmProvider.query.all()}
    user_names = {u_.id: u_.email for u_ in User.query.all()}

    def _grouped(column, names, noun):
        rows = (
            _totals_query(company_id, provider_id, since)
            .add_columns(column)
            .group_by(column)
            .all()
        )
        out = []
        for pt, ct, rt, tt, cnt, key in rows:
            out.append(
                {
                    "id": key,

                    "name": names.get(key) or f"{noun} #{key} (deleted)",
                    "prompt_tokens": int(pt),
                    "completion_tokens": int(ct),
                    "reasoning_tokens": int(rt),
                    "total_tokens": int(tt),
                    "requests": int(cnt),
                }
            )
        # Biggest consumer first — that's the one the admin is looking for.
        out.sort(key=lambda row: row["total_tokens"], reverse=True)
        return out

    day = func.date(TokenUsage.created_at)
    daily_rows = (
        _totals_query(company_id, provider_id, since)
        .add_columns(day)
        .group_by(day)
        .order_by(day.desc())
        .limit(30)
        .all()
    )
    by_day = [
        {
            "day": str(d),
            "prompt_tokens": int(pt),
            "completion_tokens": int(ct),
            "reasoning_tokens": int(rt),
            "total_tokens": int(tt),
            "requests": int(cnt),
        }
        for pt, ct, rt, tt, cnt, d in daily_rows
    ]
    by_day.reverse()

    return {
        "total": total,
        "by_company": _grouped(TokenUsage.company_id, company_names, "Company"),
        "by_provider": _grouped(TokenUsage.provider_id, provider_names, "Provider"),
        "by_user": _grouped(TokenUsage.user_id, user_names, "User"),
        "by_day": by_day,
    }
