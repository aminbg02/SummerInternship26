"""Backfill demo chat + token-usage history for the admin usage dashboard.

Unlike seed_conversations.py (which asks the platform real questions and logs
real token counts), the rows written here are SYNTHETIC: you cannot backdate a
real LLM call, and the point of this script is to populate PAST days so the
dashboard's daily-activity timeline has a story to tell in a demo.

What it writes, per backfilled turn:
  - a Conversation (backdated, titled after its first question) and its user /
    assistant Message rows — so the history sidebar shows real-looking threads,
  - a TokenUsage row linked to that conversation, with RAG-shaped counts sized
    from the actual answer text.

Attribution is real (actual companies, customers and providers from the DB);
only the calls themselves never happened.

Budgets are in TOKENS per day (~2-4k: a handful of support chats, not a flood).
Idempotent-ish: a day is topped UP to its budget counting whatever rows already
exist on it, so re-running doesn't stack — and a day that already has real
traffic past the budget is left alone.

Run with:  python -m app.seed_usage_history   (from backend/, with Docker up)
"""
import random
from datetime import date, datetime, timedelta

from sqlalchemy import func

from . import create_app
from .extensions import db
from .models import Company, Conversation, LlmProvider, Message, TokenUsage, User

# day -> total tokens that day should end up with (existing rows count toward it).
# Shaped like a real week: the 12th is a Sunday, so it's the quiet one; the 25th
# is a Saturday, same story.
DAY_TOKEN_BUDGETS = {
    date(2026, 7, 12): 2100,
    date(2026, 7, 13): 3600,
    date(2026, 7, 14): 3400,
    date(2026, 7, 15): 3900,
    date(2026, 7, 24): 3800,
    date(2026, 7, 25): 2000,
}

# Deterministic so two runs agree on what "random" meant.
_rng = random.Random(20260712)

# Question/answer material per company domain, matching each tenant's seeded
# corpus themes. Threads are 1-3 turns; answers are the kind of short grounded
# reply the real pipeline produces.
THREADS = {
    "telecom.com": [
        [
            ("How much does the Fiber Pro plan cost?",
             "The Fiber Pro plan is 89 TND per month and includes 500 Mbps download speed. "
             "Installation is free if you sign a 12-month contract."),
            ("Does it come with a router?",
             "Yes — a WiFi 6 router is included at no extra cost and remains yours after "
             "the contract period ends."),
        ],
        [
            ("What is your refund policy?",
             "You can request a full refund within 14 days of activation. After that, "
             "refunds are prorated for the unused portion of the current billing month."),
        ],
        [
            ("How do loyalty points work?",
             "You earn 1 point per dinar spent on your monthly bill. Points can be redeemed "
             "for device discounts starting at 500 points, and they expire after 24 months."),
            ("Do the points expire?",
             "Yes, loyalty points expire 24 months after they are earned. You'll get a "
             "reminder SMS 30 days before any points lapse."),
        ],
        [
            ("What compensation do I get if there is an outage?",
             "If an outage lasts more than 4 consecutive hours, you receive a credit equal "
             "to one day of your subscription for each day affected, applied automatically."),
        ],
    ],
    "ooredoo.tn": [
        [
            ("What is the wallet limit for mobile money?",
             "The standard mobile money wallet is capped at 500 TND. With identity "
             "verification, the limit rises to 5,000 TND."),
            ("Do I need to verify my identity?",
             "Verification is optional for the basic wallet, but required for the 5,000 TND "
             "limit and for transfers to bank accounts. You can verify in any branch with your CIN."),
        ],
        [
            ("How does the family plan discount work?",
             "Each additional line on a family plan gets 20% off its monthly fee, up to 5 "
             "lines. All lines share the plan's data allowance."),
        ],
        [
            ("What does Device Care cover?",
             "Device Care covers accidental damage, liquid damage and theft, for 12 TND per "
             "month. Screen repairs carry a 50 TND excess."),
        ],
    ],
    "biat.com.tn": [
        [
            ("What are the fees for an international transfer?",
             "International transfers cost 0.5% of the amount with a 20 TND minimum. "
             "Transfers within the SEPA zone settle in 1-2 business days."),
            ("And what does a card replacement cost?",
             "A replacement card is 15 TND for standard delivery, or 30 TND for express "
             "delivery within 48 hours."),
        ],
        [
            ("What interest does the savings account pay?",
             "The savings account pays 5.2% annual interest, calculated daily and credited "
             "quarterly. There is no minimum balance requirement."),
        ],
        [
            ("What documents do I need to open a business account?",
             "You'll need the company's registration certificate, tax identification, the "
             "manager's CIN, and proof of address. Opening takes 3-5 business days."),
        ],
    ],
    "topnet.com": [
        [
            ("Is there a data cap on the unlimited plan?",
             "The unlimited plan has no hard cap, but a 2 TB monthly fair-use threshold. "
             "Beyond it, speeds may be reduced during peak hours."),
            ("What happens if I go over 2 TB in a month?",
             "Nothing is charged extra — your speed may simply be prioritised lower during "
             "peak hours (19:00-23:00) until the next billing cycle."),
        ],
        [
            ("How much is a static IP address?",
             "A static IPv4 address is 10 TND per month on residential plans, and included "
             "free on all business plans."),
        ],
        [
            ("What TV bundles do you offer?",
             "Two bundles: Essential (60 channels, 15 TND/month) and Premium (120 channels "
             "plus sports, 35 TND/month). Both allow streaming on up to 3 devices."),
        ],
    ],
}


# Roughly what a real deployment sees: most answers are never rated, and the ones
# that are skew positive. A flat 50/50 split would make the dashboard useless for
# spotting a genuinely bad model.
_RATED_SHARE = 0.35
_UP_SHARE = 0.82


def _feedback_vote():
    """'up', 'down', or None — the thumbs a customer left on an answer."""
    if _rng.random() >= _RATED_SHARE:
        return None
    return "up" if _rng.random() < _UP_SHARE else "down"


def _turn_tokens(question: str, answer: str) -> dict:
    """RAG-shaped counts sized from the real text: the prompt carries retrieved
    context on top of the question; the completion tracks the answer length."""
    prompt = _rng.randint(260, 520) + len(question) // 4
    completion = len(answer) // 4 + _rng.randint(-10, 25)
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "reasoning_tokens": 0,
        "total_tokens": prompt + completion,
    }


def _work_hours_start(day: date) -> datetime:
    """A moment in the 08:00-18:00 window, biased toward late morning/afternoon."""
    hour = _rng.choice([8, 9, 9, 10, 10, 11, 11, 12, 13, 14, 14, 15, 15, 16, 16, 17])
    return datetime(day.year, day.month, day.day, hour, _rng.randint(0, 59), _rng.randint(0, 59))


def seed_usage_history():
    providers = (
        LlmProvider.query.filter(LlmProvider.enabled.is_(True))
        .order_by(LlmProvider.priority)
        .all()
    )
    if not providers:
        print("! Need seeded providers first (python -m app.seed_providers).")
        return
    # Weight the rotation so the dashboard shows a preferred provider rather than
    # a perfectly flat split nobody would believe.
    provider_pool = [p for p, w in zip(providers, (5, 4, 3, 2, 2, 1, 1, 1, 1)) for _ in range(w)]

    # (company, customer, thread) combinations to draw from, in random order.
    material = []
    for domain, threads in THREADS.items():
        company = Company.query.filter_by(domain=domain).first()
        if company is None:
            continue
        customers = User.query.filter_by(company_id=company.id, role="customer").all()
        if not customers:
            continue
        for thread in threads:
            material.append((company, _rng.choice(customers), thread))
    _rng.shuffle(material)
    if not material:
        print("! No seeded companies/customers matching the demo threads.")
        return

    draw = 0
    added_tokens = added_convos = 0
    for day, budget in sorted(DAY_TOKEN_BUDGETS.items()):
        existing = (
            db.session.query(func.coalesce(func.sum(TokenUsage.total_tokens), 0))
            .filter(func.date(TokenUsage.created_at) == day)
            .scalar()
        )
        if existing >= budget:
            print(f"  {day}: already at {existing:,} tokens (budget {budget:,}) — skipping")
            continue

        day_tokens = existing
        while day_tokens < budget:
            company, user, thread = material[draw % len(material)]
            draw += 1

            at = _work_hours_start(day)
            convo = Conversation(
                company_id=company.id,
                user_id=user.id,
                title=thread[0][0][:300],
                created_at=at,
            )
            db.session.add(convo)
            db.session.flush()  # id for the messages / usage rows

            provider = _rng.choice(provider_pool)
            for question, answer in thread:
                db.session.add(Message(conversation_id=convo.id, role="user",
                                       content=question, created_at=at))
                at += timedelta(seconds=_rng.randint(4, 12))  # model "thinking"
                db.session.add(Message(conversation_id=convo.id, role="assistant",
                                       content=answer, created_at=at,
                                       # Same provider the TokenUsage row below is
                                       # charged to. Without it the feedback
                                       # dashboard groups every seeded answer under
                                       # "(no provider)" — it joins on this column.
                                       provider_id=provider.id,
                                       feedback=_feedback_vote()))
                tokens = _turn_tokens(question, answer)
                db.session.add(
                    TokenUsage(
                        company_id=company.id,
                        user_id=user.id,
                        provider_id=provider.id,
                        conversation_id=convo.id,
                        created_at=at,
                        **tokens,
                    )
                )
                day_tokens += tokens["total_tokens"]
                added_tokens += tokens["total_tokens"]
                at += timedelta(seconds=_rng.randint(20, 150))  # reading + typing
            added_convos += 1

        print(f"  {day}: {existing:,} existing -> {day_tokens:,} tokens")

    db.session.commit()
    print(f"\nDone. {added_convos} conversation(s), {added_tokens:,} tokens added.")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        seed_usage_history()
