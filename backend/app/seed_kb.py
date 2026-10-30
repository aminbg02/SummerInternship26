"""Seed each company's knowledge base with distinct documents.

Run with:  python -m app.seed_kb   (after python -m app.seed)

Telecom and BIAT get deliberately different docs (a telco vs. a bank) so the
isolation behaviour is visible: ask both the same question, get company-scoped
answers.

Note: seed_docs.py loads the fuller, realistic corpus for every company. This
tiny seeder is kept only as the minimal two-company isolation demo.
"""
from . import create_app
from .models import Company
from .services import chunking, rag

SAMPLE_DOCS = {
    "Telecom": [
        ("telecom_billing.txt",
         "Telecom billing operates on a monthly cycle. Invoices are issued "
         "on the first of each month. Customers on the Fiber Pro plan are billed "
         "79 euros per month. Late payments incur a 5 percent fee after 14 days."),
        ("telecom_support.txt",
         "Telecom technical support is available 24/7 for Fiber Pro "
         "subscribers. To reset your router, hold the reset button for 10 "
         "seconds. The default WiFi password is printed on the underside label."),
    ],
    "BIAT": [
        ("biat_accounts.txt",
         "BIAT current accounts cost 5 dinars per month. Savings accounts have "
         "no monthly fee and earn 3 percent annual interest. Opening an account "
         "requires a national ID and a minimum deposit of 20 dinars."),
        ("biat_cards.txt",
         "A BIAT Visa Classic card costs 90 dinars per year with a 1000 dinar "
         "daily ATM withdrawal limit. If your card is lost, block it in the BIAT "
         "Net app immediately and request a replacement at any branch."),
    ],
}


def seed_kb():
    for company_name, docs in SAMPLE_DOCS.items():
        company = Company.query.filter_by(name=company_name).first()
        if company is None:
            print(f"  ! company {company_name!r} not found — run app.seed first")
            continue
        rag.reset_company_collection(company.id)  # idempotent re-seed
        total = 0
        for filename, body in docs:
            chunks = chunking.chunk_text(body)
            total += rag.index_chunks(
                company.id, chunks, base_payload={"filename": filename}
            )
        print(f"  indexed {total} chunks into kb_{company.id} ({company_name})")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        seed_kb()
