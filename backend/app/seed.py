"""Idempotent dev seed: one super_admin plus nine demo companies, each with a
company_admin and one or more customers.

This mirrors the exported production-ish database (transfer_data/postgres.sql)
rather than inventing a tidier world of its own. setup.ps1 falls back to this
seed when there is no dump to restore, and a fallback that produces a DIFFERENT
tenant list is a fallback nobody can trust: a bug reproduced on seeded data has
to be reproducible on restored data too. So the company names, email domains,
token budgets and Qdrant assignments below are the ones in the dump.

What deliberately is NOT reproduced: conversations, messages and token usage.
seed_conversations.py regenerates those by really querying the platform (see
its docstring), so the counts differ from the dump's even though the shape
matches — fabricated usage numbers fall apart the moment anyone clicks in.

Every tenant gets a daily token budget, and most users a cap under it — see
TENANT_BUDGETS for the ladder and the sizing behind it.

Run with:  python -m app.seed   (from the backend/ dir)
"""
from . import create_app
from .extensions import db
from .models import Company, User
from .services import qdrant_pool


SEED_PASSWORD = "password123"  # dev only

# Each company: display name + email domain (users are bound to a tenant by the
# domain of their email — see services/tenancy.py).
COMPANIES = [
    ("Telecom", "telecom.com"),
    ("Ooredoo", "ooredoo.tn"),
    ("BIAT", "biat.com.tn"),
    ("Topnet", "topnet.com"),
    ("FIAT", "fiat.com"),
    # A university, not a telco/bank — a leak from its corpus reads as obviously
    # foreign rather than plausible.
    ("utm", "utm.com"),
    # The four below were created through the admin UI on the live instance
    # rather than by an earlier version of this seeder. They are here because
    # the dump has them: globalnet already has a full corpus waiting in
    # seed_docs.py (which silently skipped it while this list was missing the
    # company), and TEST/Oxford are the two tenants that exercise the dedicated
    # Qdrant path — without them a seeded database can only ever demonstrate the
    # shared-instance half of tenant isolation.
    ("globalnet", "globalnet.com"),
    ("TEST", "test.com"),
    ("Oxford", "oxford.us"),
]

# Domains that get their own Qdrant instance instead of the shared one, in the
# order they should claim slots — claim_url() hands out QDRANT_DEDICATED_URLS in
# configured order, so this ordering is what reproduces the dump's assignment
# (test.com -> :6343, oxford.us -> :6353). Everything else is shared.
DEDICATED_DOMAINS = ["test.com", "oxford.us"]

# domain -> list of (email, role). One company_admin + some customers each. Every
# company also gets a user@<domain> customer, so a demo can log in to any tenant
# without remembering which name belongs to which company.
USERS_BY_DOMAIN = {
    "telecom.com": [
        ("admin@telecom.com", "company_admin"),
        ("user@telecom.com", "customer"),
        ("alice@telecom.com", "customer"),
        ("sami@telecom.com", "customer"),
    ],
    "ooredoo.tn": [
        ("admin@ooredoo.tn", "company_admin"),
        ("user@ooredoo.tn", "customer"),
        ("leila@ooredoo.tn", "customer"),
        ("karim@ooredoo.tn", "customer"),
    ],
    "biat.com.tn": [
        ("admin@biat.com.tn", "company_admin"),
        ("user@biat.com.tn", "customer"),
        ("nadia@biat.com.tn", "customer"),
        ("mehdi@biat.com.tn", "customer"),
        # Deliberately capped far below its siblings (10,000): the one user on
        # the platform whose PERSONAL cap bites long before their company pool
        # does, which is the only way to demo the two limits independently.
        ("sami@biat.com.tn", "customer", 500),
    ],
    "topnet.com": [
        ("admin@topnet.com", "company_admin"),
        ("user@topnet.com", "customer"),
        ("bob@topnet.com", "customer"),
    ],
    "fiat.com": [
        ("admin@fiat.com", "company_admin"),
        ("user@fiat.com", "customer"),
    ],
    "utm.com": [
        ("admin@utm.com", "company_admin"),
        ("user@utm.com", "customer"),
        # Third element = an explicit daily cap, overriding the tenant default
        # from TENANT_BUDGETS. None means "no personal cap", which is what the
        # dump has for every user added through the UI after the original seed:
        # they fall back to config DEFAULT_USER_DAILY_TOKEN_LIMIT and are held
        # by their company pool. Worth keeping rather than tidying away — a
        # tenant where every user is capped never exercises that fallback.
        ("user12@utm.com", "customer", None),
    ],
    "globalnet.com": [
        ("admin@globalnet.com", "company_admin", None),
        ("sami@globalnet.com", "customer", None),
    ],
    "test.com": [
        ("admin@test.com", "company_admin", None),
    ],
    "oxford.us": [
        ("admin@oxford.us", "company_admin", None),
    ],
}


# domain -> (company daily pool, company_admin cap, customer cap), in tokens/day.
#
# Sized against real traffic: one RAG turn costs ~400-700 tokens (a retrieved
# prompt plus a short grounded answer), so ~600 is a fair "one question". That
# makes a 5,000 pool about 8 questions a day for the whole tenant, and 60,000
# about a hundred.
#
# The ladder is deliberate — a flat number on every tenant would show nothing.
# It runs from a flagship account down to a trial one, so the admin dashboard has
# tenants at genuinely different scales to compare, and the smallest tier is
# small enough that a demo can actually WATCH a cap bite instead of talking about
# it hypothetically.
#
# Two rules hold across every row, and blueprints/users.py enforces the first:
#   * no user cap exceeds its company's pool (a cap above the pool is a number
#     that can never be reached — check_company_quota refuses the call first), and
#   * an admin's cap is above their customers', since they carry the ingestion
#     and testing work on top of ordinary chat.
#
# A None cap means "no personal limit" — the user falls back to the platform
# default (config DEFAULT_USER_DAILY_TOKEN_LIMIT) and is bounded by the company
# pool. That is what the tenants created later through the UI look like.
TENANT_BUDGETS = {
    #                    pool     admin   customer
    "telecom.com":   (200_000,  40_000,  20_000),   # flagship tenant
    "ooredoo.tn":    (120_000,  30_000,  15_000),
    "biat.com.tn":   ( 60_000,  20_000,  10_000),
    "topnet.com":    ( 25_000,  10_000,   5_000),
    "fiat.com":      ( 10_000,   4_000,   2_000),
    "utm.com":       (  5_000,   2_000,   1_000),   # trial tier — caps bite here
    # Added through the admin UI on the live instance; no per-user caps were set,
    # so these run on the platform default under a company pool.
    "globalnet.com": (  4_000,    None,    None),
    "oxford.us":     (  4_000,    None,    None),
    # 400/day is ~half a dozen questions for the WHOLE tenant. Deliberately
    # tiny: it is the pool that runs out during a demo instead of after one.
    "test.com":      (    400,    None,    None),
}


def _budget_for(domain, role):
    """The seeded daily cap for a user, by their tenant and role."""
    pool, admin_cap, customer_cap = TENANT_BUDGETS[domain]
    return admin_cap if role == "company_admin" else customer_cap


def _assign_dedicated_instance(company, domain):
    """Give a tenant its own Qdrant instance, if it is meant to have one.

    Claims from the same pool the admin endpoint uses (services/qdrant_pool.py)
    rather than hardcoding a URL, so a deployment that configured a different
    QDRANT_DEDICATED_URLS still gets a valid assignment. Never re-claims: a
    company that already holds a slot keeps it, because its vectors live there.
    """
    if domain not in DEDICATED_DOMAINS or company.qdrant_url:
        return
    url = qdrant_pool.claim_url()
    if url is None:
        # Pool exhausted or unconfigured. Not fatal — the tenant just stays on
        # the shared instance, which is a working company, only a less
        # interesting one. Silence here would be worse than a line of output.
        print(f"  ! no free dedicated Qdrant slot for {domain} — leaving it shared")
        return
    qdrant_pool.assert_url_unclaimed(url, exclude_company_id=company.id)
    company.qdrant_url = url


def _get_or_create_company(name, domain):
    pool = TENANT_BUDGETS[domain][0]
    company = Company.query.filter_by(name=name).first()
    if company is None:
        company = Company(name=name, domain=domain, daily_token_limit=pool)
        db.session.add(company)
        db.session.flush()
    else:
        company.domain = domain  # keep domain in sync on re-seed
        # Re-applied on re-seed like role/company below: this is a dev seed, and
        # its whole value is that the demo data is the same every time. A cap
        # changed by hand in the UI is reset by the next `python -m app.seed`.
        company.daily_token_limit = pool
    company.assign_collection_name()  # no-op once set — a re-seed must not move it
    _assign_dedicated_instance(company, domain)
    return company


def _get_or_create_user(email, role, company_id=None, daily_token_limit=None):
    user = User.query.filter_by(email=email).first()
    if user is None:
        user = User(email=email, role=role, company_id=company_id,
                    daily_token_limit=daily_token_limit)
        user.set_password(SEED_PASSWORD)
        db.session.add(user)
    else:
        # keep role/company/cap in sync on re-seed
        user.role = role
        user.company_id = company_id
        user.daily_token_limit = daily_token_limit
    return user


def _cap_for(domain, entry):
    """A user's daily cap: the explicit third element if the row carries one,
    otherwise the tenant/role default. Length matters, not truthiness — an
    explicit None ("no personal cap") is a real value and must not fall through
    to the tenant default."""
    return entry[2] if len(entry) > 2 else _budget_for(domain, entry[1])


def _fmt_cap(cap):
    """ASCII, and safe on None."""
    return "no personal cap" if cap is None else f"cap {cap:,}/day"


def seed():
    companies = {domain: _get_or_create_company(name, domain)
                 for name, domain in COMPANIES}

    # Orange staff: not bound to any company, and never capped (super_admin,
    # company_id NULL, daily_token_limit NULL — see usage.effective_user_limit).
    _get_or_create_user("admin@orange.com", role="super_admin", company_id=None)

    for domain, users in USERS_BY_DOMAIN.items():
        company = companies[domain]
        for entry in users:
            email, role = entry[0], entry[1]
            _get_or_create_user(email, role=role, company_id=company.id,
                                daily_token_limit=_cap_for(domain, entry))

    db.session.commit()

    print("Seeded:")
    print(f"  admin@orange.com   / {SEED_PASSWORD}  (super_admin, no company, uncapped)")
    for domain, users in USERS_BY_DOMAIN.items():
        company = companies[domain]
        pool = TENANT_BUDGETS[domain][0]
        # ASCII only: this prints to a Windows console under cp1252, where an
        # em-dash comes out as a replacement character.
        store = f"dedicated {company.qdrant_url}" if company.qdrant_url else "shared Qdrant"
        print(f"  {company.name} ({domain}) - pool {pool:,} tokens/day, {store}")
        for entry in users:
            email, role = entry[0], entry[1]
            print(f"    {email:<22} / {SEED_PASSWORD}  ({role}, {_fmt_cap(_cap_for(domain, entry))})")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        seed()
