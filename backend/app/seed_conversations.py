"""Seed realistic chat history by asking the platform real questions.

Deliberately NOT a set of hand-written rows inserted into `messages`. Every thread
here is produced by POSTing to /api/query exactly as the Angular app does, so what
lands in the database is the real thing: the retrieved chunks are really retrieved,
the answers are really generated, and the token counts are what the providers
actually reported. A demo backed by fabricated usage numbers is a demo that falls
apart the moment someone clicks into it.

Consequences worth knowing:
  - it costs real (free-tier) quota and takes a few minutes;
  - it only asks questions the seeded corpus can actually answer, so the answers are
    grounded rather than "I don't have that information";
  - each user's threads are their own — history is per (company, user), so this also
    populates the sidebar for whoever you log in as.

Providers are rotated and the script paces itself, because the shared free keys have
RPM ceilings and usage.py will (correctly) refuse a call that would breach them.

Idempotent-ish: skips a user who already has >= MIN_THREADS threads, so re-running
tops up rather than duplicating.

Run with:  python -m app.seed_conversations   (from backend/, with Docker up)
"""
import time

from . import create_app
from .extensions import db
from .models import Company, Conversation, LlmProvider, User

# A user who already has this many threads is left alone, so re-running tops up
# rather than piling on duplicates.
TARGET_THREADS_PER_USER = 8
# Pause between calls. The tightest shared-key ceiling in play is 30 RPM, so ~2.5s
# keeps us comfortably under it even with every provider in rotation.
PACE_SECONDS = 2.5

# Customers whose own daily cap is below this are left out of the seeding run.
# A grounded turn costs ~400-700 tokens, so a user capped at 500/day cannot fund
# one — and seed.py creates exactly such a user on purpose (sami@biat.com.tn) so
# that a cap can be watched biting in a demo. Spending it here would both empty
# the thing the user exists to demonstrate and fill this log with 429s. None
# means no personal cap, which always passes.
MIN_USER_TOKEN_BUDGET = 1500

# Multi-turn threads: each is a list of questions asked in sequence in ONE
# conversation, so the history sidebar has threads with real depth rather than a
# single question each. Keyed by company domain.
THREADS = {
    "telecom.com": [
        [
            "How much does the Fiber Pro plan cost and what speed does it include?",
            "Is the installation fee waived if I sign a 12-month contract?",
            "Does it come with a router?",
        ],
        [
            "What is the refund policy?",
            "What happens if I downgrade my plan halfway through the month?",
        ],
        [
            "How much notice do I need to give to cancel a monthly plan?",
            "Can I cancel without penalty if I move somewhere with no coverage?",
        ],
        [
            "What compensation do I get if there is an outage?",
            "How long does the outage have to last before I get a credit?",
        ],
        [
            "How do loyalty points work?",
            "How many points do I need for a device discount?",
            "Do the points expire?",
        ],
        [
            "How long is prepaid credit valid for?",
            "What prepaid data packs are available?",
        ],
        [
            "I am hard of hearing. What accessibility services do you offer?",
            "Can I get my invoice in large print?",
        ],
        [
            "How do I raise a complaint and how fast will you respond?",
            "What happens if you miss the deadline?",
        ],
        ["When does a plan change made in the app take effect?"],
        ["How much data does the Unlimited mobile plan include and what does it cost?"],
    ],
    "ooredoo.tn": [
        [
            "What is the wallet limit for mobile money?",
            "What does it cost to transfer money to a bank account?",
            "Do I need to verify my identity?",
        ],
        [
            "How does the family plan discount work?",
            "How many lines can I have on one family plan?",
        ],
        [
            "What does Device Care cover and how much is it?",
            "What is the excess for a screen repair?",
        ],
        [
            "I am a student. What offers do you have?",
            "What happens if I don't renew my proof of enrolment?",
        ],
        [
            "How many times can I transfer my eSIM to a new device?",
            "What if my old phone is broken?",
        ],
        ["What are your call centre hours and what number do I call?"],
        ["Can I get a free signal booster if my indoor signal is weak?"],
    ],
    "biat.com.tn": [
        [
            "How much can I borrow for a mortgage and over how long?",
            "What is the fixed interest rate?",
            "Is there a penalty for repaying early?",
        ],
        [
            "What are the fees for an international transfer?",
            "And what does a card replacement cost?",
        ],
        [
            "What documents do I need to open a business account?",
            "How long does it take and what is the monthly fee?",
        ],
        [
            "What interest does the savings account pay?",
            "What about a 24-month fixed-term deposit?",
        ],
        [
            "My card was blocked while I was abroad. What do I do?",
            "What fee do you charge for foreign purchases?",
        ],
        [
            "How long do I have to dispute a card transaction?",
            "Will you re-credit the money while you investigate?",
        ],
        ["What ID do I need to open a personal account?"],
    ],
    "topnet.com": [
        [
            "Is there a data cap on the unlimited plan?",
            "What happens if I go over 2 TB in a month?",
        ],
        [
            "How much is a static IP address?",
            "What uptime do you guarantee on a business plan?",
        ],
        [
            "What TV bundles do you offer?",
            "How many devices can stream at the same time?",
            "How long are recordings kept?",
        ],
        [
            "I am moving house. How much notice do I need to give?",
            "What if my new address has no coverage?",
        ],
        [
            "What does .tn domain registration cost?",
            "What hosting plans are available?",
        ],
        [
            "My speed is much lower than advertised. What can I do?",
            "What speed do you actually guarantee on fibre?",
        ],
        ["How do I secure my account, and will you ever ask for my password?"],
    ],
    # The two small tenants. Deliberately one question per thread, unlike the
    # four above: FIAT's only customer is capped at 2,000 tokens/day and utm's
    # at 1,000, so a three-question thread here would hit its own cap partway
    # through and fill the log with quota errors instead of history. The seeder
    # survives that, but "the demo data ran out of quota while being created" is
    # a confusing first impression. Depth lives in the big tenants; these two
    # exist to show what a small account looks like, and a small account looks
    # like a couple of short threads.
    "fiat.com": [
        ["How long is the warranty on a new FIAT, and what does it not cover?"],
        ["How often does a diesel engine need servicing, and what does it cost?"],
    ],
    "utm.com": [
        ["How many books can a Master student borrow, and for how long?"],
        ["What are the annual registration fees, and what scholarships can I apply for?"],
    ],
}


def _healthy_providers():
    """Enabled providers that aren't currently greyed out, cheapest-first by priority."""
    from .services import usage

    rows = (
        LlmProvider.query.filter(LlmProvider.enabled.is_(True))
        .order_by(LlmProvider.priority, LlmProvider.id)
        .all()
    )
    return [p for p in rows if usage.provider_availability(p)["available"]]


def seed_conversations():
    app = create_app()
    with app.app_context():
        providers = _healthy_providers()
        if not providers:
            print("! No healthy providers — nothing to ask with. Fix a provider first.")
            return
        print(f"Using providers: {', '.join(p.display_name for p in providers)}\n")

        client = app.test_client()
        asked = 0
        rotation = 0

        for domain, threads in THREADS.items():
            company = Company.query.filter_by(domain=domain).first()
            if company is None:
                print(f"! No company for domain {domain} — skipping")
                continue

            # Spread the threads across that company's real customers.
            users = (
                User.query.filter_by(company_id=company.id, role="customer")
                .order_by(User.id)
                .all()
            )
            too_small = [
                u for u in users
                if u.daily_token_limit is not None
                and u.daily_token_limit < MIN_USER_TOKEN_BUDGET
            ]
            for u in too_small:
                print(f"  . {u.email} capped at {u.daily_token_limit}/day — leaving their quota intact")
            users = [u for u in users if u not in too_small]
            if not users:
                print(f"! {company.name}: no customers — skipping")
                continue

            print(f"--- {company.name} ({len(users)} customer(s))")
            for i, questions in enumerate(threads):
                user = users[i % len(users)]

                existing = Conversation.query.filter_by(
                    company_id=company.id, user_id=user.id
                ).count()
                if existing >= TARGET_THREADS_PER_USER:
                    continue

                token = client.post(
                    "/api/auth/login",
                    json={"email": user.email, "password": "password123"},
                ).get_json()["access_token"]
                headers = {"Authorization": f"Bearer {token}"}

                convo_id = None
                for question in questions:
                    provider = providers[rotation % len(providers)]
                    rotation += 1

                    body = {"question": question, "provider_id": provider.id}
                    if convo_id is not None:
                        body["conversation_id"] = convo_id

                    resp = client.post("/api/query", headers=headers, json=body)
                    data = resp.get_json() or {}
                    asked += 1

                    if resp.status_code != 200:
                        print(f"  ! {user.email}: {data.get('error')} ({provider.display_name})")
                        # A provider just went dark — drop it and carry on.
                        providers = _healthy_providers()
                        if not providers:
                            print("  ! every provider is now unavailable — stopping")
                            db.session.commit()
                            return
                        continue

                    convo_id = data.get("conversation_id")
                    tokens = (data.get("usage") or {}).get("total_tokens", 0)
                    print(
                        f"  + {user.email:22s} {provider.display_name[:18]:18s} "
                        f"{tokens:>5} tok  {question[:46]}"
                    )
                    time.sleep(PACE_SECONDS)

        db.session.commit()
        print(f"\nDone. {asked} question(s) asked.")
        print(f"Conversations now: {Conversation.query.count()}")


if __name__ == "__main__":
    seed_conversations()
