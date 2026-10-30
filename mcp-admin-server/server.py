"""MCP server exposing the Orange platform's admin API as tools an AnythingLLM
agent can call. Standalone from backend/ on purpose — this talks to the
running Flask app over HTTP, the same way any admin client would, rather than
importing its code directly.

Three tiers of tools:
  1. Reads          — plain GETs, one endpoint each (list_companies, ...).
  2. Diagnostics    — read-only, but the tool does the multi-step work itself
                      (probe every provider, cross-reference usage + feedback +
                      ingestions for one company, rank the providers users hate).
  3. Writes         — real state changes (enable a provider, add a PII rule,
                      move a token cap, decide a token request). Every one of
                      these is DRY-RUN BY DEFAULT: it returns a preview and does
                      nothing until re-called with confirm=true. That guard is
                      here, not in the backend — a human hitting the admin API
                      still gets no confirmation step.

Run:
    ORANGE_ADMIN_EMAIL=you@company.com ORANGE_ADMIN_PASSWORD=... python server.py

Then point AnythingLLM's anythingllm_mcp_servers.json at this script (see
README.md in this folder).
"""
import os
import re
import time

import httpx
from mcp.server import MCPServer
from mcp.types import ToolAnnotations

API_BASE = os.environ.get("ORANGE_API_BASE", "http://localhost:5000/api")
ADMIN_EMAIL = os.environ["ORANGE_ADMIN_EMAIL"]
ADMIN_PASSWORD = os.environ["ORANGE_ADMIN_PASSWORD"]

mcp = MCPServer("orange-admin")

# Annotation presets — hints the agent uses to decide how freely it may call a
# tool. read_only: safe to call anytime. probe: read-only for our DB but it
# reaches out to a third-party LLM, so not free. mutating: changes state, but
# our confirm=false default means a bare call is still only a preview.
READ_ONLY = ToolAnnotations(read_only_hint=True, idempotent_hint=True, open_world_hint=False)
PROBE = ToolAnnotations(read_only_hint=True, idempotent_hint=True, open_world_hint=True)
MUTATING = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True)

_token: str | None = None


def _login() -> str:
    global _token
    if _token is None:
        resp = httpx.post(
            f"{API_BASE}/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=10,
        )
        resp.raise_for_status()
        _token = resp.json()["access_token"]
    return _token


def _request(method: str, path: str, *, params: dict | None = None,
             json: dict | None = None, timeout: float = 15.0) -> dict:
    """Call an admin endpoint, retrying once with a fresh login on a 401 (an
    expired token, not a first-time auth failure — _login() would already have
    raised if the credentials themselves were wrong). On any other 4xx/5xx the
    body is surfaced as {"error": ...} rather than raising, so the agent gets a
    message it can act on instead of a stack trace."""
    global _token
    for attempt in (1, 2):
        resp = httpx.request(
            method,
            f"{API_BASE}{path}",
            headers={"Authorization": f"Bearer {_login()}"},
            params=params or {},
            json=json,
            timeout=timeout,
        )
        if resp.status_code == 401 and attempt == 1:
            _token = None
            continue
        break

    if resp.is_success:
        return resp.json()
    try:
        body = resp.json()
    except ValueError:
        body = {"detail": resp.text[:300]}
    return {"error": body.get("error", "request_failed"), "status": resp.status_code, **body}


def _get(path: str, params: dict | None = None) -> dict:
    return _request("GET", path, params=params)


# --------------------------------------------------------------------------- #
# Lookup helpers — the agent works in names, the API works in ids.
# --------------------------------------------------------------------------- #

def _find_company(name: str | None) -> dict | None:
    if not name:
        return None
    for c in _get("/admin/companies").get("companies", []):
        if c["name"].lower() == name.lower():
            return c
    return None


def _find_provider(name: str | None) -> dict | None:
    if not name:
        return None
    for p in _get("/admin/llm-providers").get("providers", []):
        if p["display_name"].lower() == name.lower():
            return p
    return None


def _find_user(email: str) -> dict | None:
    email = (email or "").lower()
    for u in _get("/users").get("users", []):
        if (u["email"] or "").lower() == email:
            return u
    return None


def _company_id(name: str | None) -> int | None:
    c = _find_company(name)
    return c["id"] if c else None


def _provider_id(name: str | None) -> int | None:
    p = _find_provider(name)
    return p["id"] if p else None


def _preview(confirm: bool, action: str, changes: dict) -> dict | None:
    """Returns a dry-run payload when confirm is not exactly True, else None
    (meaning: go ahead and apply). Keeping the check `is not True` means a
    stray "true" string or 1 won't be mistaken for consent."""
    if confirm is True:
        return None
    return {
        "dry_run": True,
        "action": action,
        "would_change": changes,
        "to_apply": "call this tool again with confirm=true",
    }


# --------------------------------------------------------------------------- #
# Tier 1 — reads
# --------------------------------------------------------------------------- #

@mcp.tool(annotations=READ_ONLY)
def list_companies() -> dict:
    """List every company (tenant) on the platform: id, name, email domain,
    daily token/request caps, and where its vectors live (shared vs dedicated
    Qdrant)."""
    return _get("/admin/companies")


@mcp.tool(annotations=READ_ONLY)
def list_providers() -> dict:
    """List every LLM provider: whether it's enabled, its priority in the
    fallback chain, rate limits, and whether an API key is set. Disabled or
    rate-limited providers still show up here — use test_provider to find out
    if one is actually answering right now."""
    return _get("/admin/llm-providers")


@mcp.tool(annotations=READ_ONLY)
def get_usage_summary(
    company_name: str | None = None,
    provider_name: str | None = None,
    since: str | None = None,
) -> dict:
    """Token/request usage totals plus per-company, per-provider, per-user and
    per-day breakdowns. Filter by company_name and/or provider_name (exact
    display names, case-insensitive — see list_companies / list_providers).
    `since` is an ISO date (YYYY-MM-DD) or a bare number of days ago as a
    string (e.g. "7"); omit for all-time."""
    params: dict = {}
    if (cid := _company_id(company_name)) is not None:
        params["company_id"] = cid
    if (pid := _provider_id(provider_name)) is not None:
        params["provider_id"] = pid
    if since:
        params["since"] = since
    return _get("/admin/usage", params=params)


@mcp.tool(annotations=READ_ONLY)
def get_feedback_summary(
    company_name: str | None = None,
    provider_name: str | None = None,
    since: str | None = None,
) -> dict:
    """Thumbs up/down totals and satisfaction score (percent of rated answers
    that were positive), broken down by company and provider, plus the most
    recent thumbs-down answers with the sources they were grounded on. Same
    filters as get_usage_summary."""
    params: dict = {}
    if (cid := _company_id(company_name)) is not None:
        params["company_id"] = cid
    if (pid := _provider_id(provider_name)) is not None:
        params["provider_id"] = pid
    if since:
        params["since"] = since
    return _get("/admin/feedback", params=params)


@mcp.tool(annotations=READ_ONLY)
def list_pii_rules(company_name: str | None = None) -> dict:
    """List custom PII redaction rules (regex patterns applied to retrieved
    chunks and final answers). Pass company_name to see that company's rules
    plus the global ones; omit for every rule."""
    params: dict = {}
    if (cid := _company_id(company_name)) is not None:
        params["company_id"] = cid
    return _get("/admin/pii-rules", params=params)


@mcp.tool(annotations=READ_ONLY)
def list_ingestions(company_name: str | None = None) -> dict:
    """Audit trail of documents added to a knowledge base — filename, who did
    it, chunks indexed vs. blocked by the safety gate, when. Newest first,
    capped at 200. Pass company_name to filter to one tenant."""
    params: dict = {}
    if (cid := _company_id(company_name)) is not None:
        params["company_id"] = cid
    return _get("/admin/ingestions", params=params)


@mcp.tool(annotations=READ_ONLY)
def list_deletions(company_name: str | None = None) -> dict:
    """Audit trail of documents removed from a knowledge base — the mirror of
    list_ingestions. Same company_name filter."""
    params: dict = {}
    if (cid := _company_id(company_name)) is not None:
        params["company_id"] = cid
    return _get("/admin/deletions", params=params)


@mcp.tool(annotations=READ_ONLY)
def qdrant_pool_status() -> dict:
    """How many dedicated Qdrant instances exist, which tenant claims each, and
    how many slots are still free to assign to a company that wants isolated
    (not shared) vector storage."""
    return _get("/admin/qdrant-pool")


@mcp.tool(annotations=READ_ONLY)
def list_token_requests(status: str | None = None) -> dict:
    """List "please raise my limit" requests from customers and company admins.
    Optional status filter: "pending", "approved", or "rejected". Feed a
    request's id to decide_token_request to approve or reject it."""
    rows = _get("/token-requests").get("requests", [])
    if status:
        rows = [r for r in rows if r.get("status") == status.lower()]
    return {"requests": rows, "count": len(rows)}


# --------------------------------------------------------------------------- #
# Tier 2 — diagnostics (read-only, multi-step)
# --------------------------------------------------------------------------- #

@mcp.tool(annotations=PROBE)
def health_check_all_providers(include_disabled: bool = False) -> dict:
    """Actively probe every provider in turn — sends each a trivial prompt and
    times the round trip — then return a live/degraded/down verdict for each.
    This is the real "is the platform healthy" check: list_providers only shows
    the configured state, this shows what's actually answering. Skips disabled
    providers unless include_disabled=true. Takes a few seconds per provider."""
    reg = _get("/admin/llm-providers")
    if "error" in reg:
        return reg  # surfaced error dict
    providers = reg.get("providers", [])

    results = []
    live = degraded = down = 0
    for p in providers:
        if not p["enabled"] and not include_disabled:
            continue
        started = time.perf_counter()
        res = _request("POST", f"/admin/llm-providers/{p['id']}/test", json={}, timeout=45.0)
        elapsed = round(time.perf_counter() - started, 1)

        if res.get("ok"):
            verdict = "live"
            live += 1
        elif res.get("error") == "rate_limited" or res.get("status") == 429:
            verdict = "degraded (rate limited)"
            degraded += 1
        else:
            verdict = "down"
            down += 1
        results.append({
            "provider": p["display_name"],
            "enabled": p["enabled"],
            "verdict": verdict,
            "seconds": elapsed,
            "detail": res.get("detail") or res.get("error"),
        })

    return {
        "checked": len(results),
        "live": live,
        "degraded": degraded,
        "down": down,
        "summary": f"{live} live, {degraded} degraded, {down} down of {len(results)} checked",
        "providers": results,
    }


@mcp.tool(annotations=READ_ONLY)
def diagnose_company(company_name: str) -> dict:
    """One-call health report for a single tenant: pulls its caps, last-24h and
    all-time usage, feedback score, and recent ingestions, then flags the
    problems (near or over its token cap, low answer satisfaction, documents
    with lots of blocked chunks, no knowledge base yet). Use this when someone
    asks "what's wrong with company X" instead of calling four tools yourself."""
    company = _find_company(company_name)
    if company is None:
        return {"error": f"no company named {company_name!r} — call list_companies() for valid names"}
    cid = company["id"]

    day_usage = _get("/admin/usage", params={"company_id": cid, "since": "1"}).get("total", {})
    all_usage = _get("/admin/usage", params={"company_id": cid}).get("total", {})
    fb = _get("/admin/feedback", params={"company_id": cid}).get("total", {})
    ingestions = _get("/admin/ingestions", params={"company_id": cid}).get("ingestions", [])

    cap = company.get("daily_token_limit")
    used_today = day_usage.get("total_tokens", 0)
    flags = []

    if cap:
        pct = round(used_today * 100 / cap) if cap else 0
        if used_today >= cap:
            flags.append(f"OVER token cap: {used_today}/{cap} used in the last 24h")
        elif pct >= 80:
            flags.append(f"near token cap: {used_today}/{cap} ({pct}%) used in the last 24h")
    else:
        flags.append("no daily token cap set (uncapped spend)")

    score = fb.get("score")
    if score is not None and fb.get("rated", 0) >= 5 and score < 60:
        flags.append(f"low answer satisfaction: {score}% positive over {fb['rated']} rated answers")

    blocked = [i for i in ingestions if i.get("chunks_blocked", 0) > 0]
    if blocked:
        worst = max(blocked, key=lambda i: i["chunks_blocked"])
        flags.append(
            f"{len(blocked)} ingested file(s) had chunks blocked by the safety gate "
            f"(worst: {worst['filename']}, {worst['chunks_blocked']} blocked)"
        )
    if not ingestions:
        flags.append("no documents ingested yet — this tenant has an empty knowledge base")

    return {
        "company": company,
        "usage_last_24h": day_usage,
        "usage_all_time": all_usage,
        "feedback": fb,
        "ingestion_count": len(ingestions),
        "flags": flags or ["no problems detected"],
        "verdict": "needs attention" if flags else "healthy",
    }


@mcp.tool(annotations=READ_ONLY)
def find_problem_providers(since: str | None = None) -> dict:
    """Rank providers by how badly they're serving users: combines the feedback
    score (percent positive) with disabled state to surface the ones worth
    looking at. `since` filters the feedback window (ISO date or days-ago
    string). Returns worst first. Follow up with test_provider or
    health_check_all_providers to see if it's a live outage or just unpopular
    answers."""
    params = {"since": since} if since else {}
    by_provider = _get("/admin/feedback", params=params).get("by_provider", [])
    providers = {p["display_name"]: p for p in _get("/admin/llm-providers").get("providers", [])}

    problems = []
    for row in by_provider:
        name = row.get("name")
        score = row.get("score")
        rated = row.get("rated", 0)
        cfg = providers.get(name, {})
        reasons = []
        if not cfg.get("enabled", True):
            reasons.append("currently disabled")
        if score is not None and rated >= 5 and score < 60:
            reasons.append(f"{score}% positive over {rated} rated answers")
        elif score is not None and rated >= 5 and score < 75:
            reasons.append(f"mediocre: {score}% positive over {rated} rated answers")
        if reasons:
            problems.append({
                "provider": name,
                "score": score,
                "rated": rated,
                "downvotes": row.get("down", 0),
                "reasons": reasons,
            })

    problems.sort(key=lambda p: (p["score"] if p["score"] is not None else 101, -p["rated"]))
    return {
        "problem_count": len(problems),
        "problems": problems or "no providers currently look problematic",
    }


# --------------------------------------------------------------------------- #
# Tier 3 — writes (dry-run unless confirm=true)
# --------------------------------------------------------------------------- #

@mcp.tool(annotations=PROBE)
def test_provider(provider_name: str) -> dict:
    """Actively probe ONE provider right now: sends it a trivial prompt and
    reports whether it answered. Use this to check a provider is live before
    relying on it — "enabled" in list_providers doesn't mean it isn't
    rate-limited or down."""
    pid = _provider_id(provider_name)
    if pid is None:
        return {"error": f"no provider named {provider_name!r} — call list_providers() for valid names"}
    return _request("POST", f"/admin/llm-providers/{pid}/test", json={}, timeout=45.0)


@mcp.tool(annotations=MUTATING)
def set_provider_enabled(provider_name: str, enabled: bool, confirm: bool = False) -> dict:
    """Enable or disable a provider in the fallback chain. Disabling takes it
    out of rotation for every company immediately. DRY-RUN by default: shows
    what would change; pass confirm=true to apply."""
    p = _find_provider(provider_name)
    if p is None:
        return {"error": f"no provider named {provider_name!r} — call list_providers() for valid names"}
    if p["enabled"] == enabled:
        return {"noop": True, "detail": f"{p['display_name']} is already {'enabled' if enabled else 'disabled'}"}

    dry = _preview(
        confirm,
        f"{'enable' if enabled else 'disable'} provider {p['display_name']!r}",
        {"enabled": {"from": p["enabled"], "to": enabled}},
    )
    if dry:
        return dry
    return _request("PUT", f"/admin/llm-providers/{p['id']}", json={"enabled": enabled})


@mcp.tool(annotations=MUTATING)
def create_pii_rule(
    entity_name: str,
    pattern: str,
    company_name: str | None = None,
    score: float = 0.85,
    confirm: bool = False,
) -> dict:
    """Add a custom PII redaction rule — a regex whose matches get masked out
    of retrieved chunks and final answers. entity_name is a label (e.g.
    "EMPLOYEE_ID"), pattern is a Python regex. Scope it to one tenant with
    company_name, or leave it off for a platform-wide rule. The regex is
    validated here before anything is sent. DRY-RUN by default; confirm=true
    to apply."""
    try:
        re.compile(pattern)
    except re.error as e:
        return {"error": "invalid_pattern", "detail": str(e)}

    body: dict = {"entity_name": entity_name.strip().upper(), "pattern": pattern, "score": score}
    scope = "platform-wide"
    if company_name:
        c = _find_company(company_name)
        if c is None:
            return {"error": f"no company named {company_name!r} — call list_companies() for valid names"}
        body["company_id"] = c["id"]
        scope = c["name"]

    dry = _preview(confirm, f"create PII rule {body['entity_name']!r} ({scope})",
                   {"entity_name": body["entity_name"], "pattern": pattern, "score": score, "scope": scope})
    if dry:
        return dry
    return _request("POST", "/admin/pii-rules", json=body)


@mcp.tool(annotations=MUTATING)
def set_company_token_limit(
    company_name: str,
    daily_token_limit: int | None,
    confirm: bool = False,
) -> dict:
    """Set a company's shared daily token cap. Pass an integer for the cap,
    or null to remove the cap entirely (uncapped). This is the pool every user
    at the company draws from. DRY-RUN by default; confirm=true to apply."""
    c = _find_company(company_name)
    if c is None:
        return {"error": f"no company named {company_name!r} — call list_companies() for valid names"}

    dry = _preview(
        confirm,
        f"set {c['name']} daily token cap to {daily_token_limit if daily_token_limit is not None else 'uncapped'}",
        {"daily_token_limit": {"from": c.get("daily_token_limit"), "to": daily_token_limit}},
    )
    if dry:
        return dry
    return _request("PUT", f"/admin/companies/{c['id']}", json={"daily_token_limit": daily_token_limit})


@mcp.tool(annotations=MUTATING)
def set_user_token_limit(
    email: str,
    daily_token_limit: int | None,
    confirm: bool = False,
) -> dict:
    """Set one user's personal daily token cap. Integer for the cap, 0 to block
    the user entirely, or null to fall back to the platform default. A user is
    also still bound by their company's shared pool. DRY-RUN by default;
    confirm=true to apply."""
    u = _find_user(email)
    if u is None:
        return {"error": f"no user with email {email!r} — call list_users via get_usage_summary breakdowns or check the address"}

    dry = _preview(
        confirm,
        f"set {u['email']} daily token cap to "
        f"{daily_token_limit if daily_token_limit is not None else 'platform default'}",
        {"daily_token_limit": {"from": u.get("daily_token_limit"), "to": daily_token_limit}},
    )
    if dry:
        return dry
    return _request("PATCH", f"/users/{u['id']}/token-limit",
                    json={"daily_token_limit": daily_token_limit})


@mcp.tool(annotations=MUTATING)
def decide_token_request(
    request_id: int,
    decision: str,
    reason: str | None = None,
    confirm: bool = False,
) -> dict:
    """Approve or reject a pending token-limit request (see list_token_requests).
    decision is "approved" or "rejected"; a reason is required to reject.
    Approving a company-scope request ADDS the requested amount to the company
    pool; approving a user-scope request SETS that user's cap to the requested
    value. DRY-RUN by default; confirm=true to apply."""
    decision = decision.strip().lower()
    if decision not in ("approved", "rejected"):
        return {"error": "decision must be 'approved' or 'rejected'"}
    if decision == "rejected" and not reason:
        return {"error": "a reason is required to reject a request"}

    match = next((r for r in _get("/token-requests").get("requests", []) if r.get("id") == request_id), None)
    if match is None:
        return {"error": f"no token request with id {request_id}"}
    if match.get("status") != "pending":
        return {"error": f"request {request_id} is already {match.get('status')}"}

    dry = _preview(
        confirm,
        f"{decision} token request #{request_id} "
        f"({match.get('scope')}-scope, {match.get('requested_limit')} tokens, "
        f"from {match.get('requester_email')})",
        {"status": {"from": "pending", "to": decision}, "reason": reason},
    )
    if dry:
        return dry
    body = {"status": decision}
    if reason:
        body["decision_reason"] = reason
    return _request("PATCH", f"/token-requests/{request_id}", json=body)


# --------------------------------------------------------------------------- #
# Prompt + resources — give the agent a starting brief and a couple of
# always-available context reads it doesn't have to "call a tool" for.
# --------------------------------------------------------------------------- #

@mcp.prompt(description="Brief for acting as the Orange platform admin assistant.")
def platform_admin_briefing() -> str:
    return (
        "You are the operations assistant for the Orange multi-tenant RAG platform. "
        "You have admin tools grouped in three tiers:\n"
        "  - Reads (list_*, get_*_summary, qdrant_pool_status): call freely.\n"
        "  - Diagnostics (health_check_all_providers, diagnose_company, "
        "find_problem_providers): read-only but they do real multi-step work — "
        "prefer these to running several reads yourself.\n"
        "  - Writes (set_provider_enabled, create_pii_rule, set_company_token_limit, "
        "set_user_token_limit, decide_token_request): every one is dry-run by "
        "default. Call once to preview the change, show the user the preview, and "
        "only re-call with confirm=true after they say yes.\n\n"
        "Work in names (company names, provider display names, user emails); the "
        "tools resolve them to ids. When asked an open question like 'is anything "
        "wrong', start with health_check_all_providers and find_problem_providers."
    )


@mcp.resource("orange://providers", mime_type="application/json",
              description="Live provider registry (same data as list_providers).")
def providers_resource() -> dict:
    return _get("/admin/llm-providers")


@mcp.resource("orange://companies", mime_type="application/json",
              description="Live company/tenant list (same data as list_companies).")
def companies_resource() -> dict:
    return _get("/admin/companies")


if __name__ == "__main__":
    mcp.run(transport="stdio")
