"""

when we add a company it auto create a company admin
"""
from . import create_app
from .blueprints.admin import _ensure_company_admin
from .extensions import db
from .models import Company


def run():
    app = create_app()
    with app.app_context():
        created = []
        skipped_no_domain = []
        for company in Company.query.order_by(Company.id).all():
            admin = _ensure_company_admin(company)
            if admin is not None:
                created.append(admin.email)
            elif not company.domain:
                skipped_no_domain.append(company.name)
        db.session.commit()

        if created:
            print(f"Created {len(created)} admin account(s):")
            for email in created:
                print(f"  {email}")
        else:
            print("No companies were missing an admin.")
        if skipped_no_domain:
            print(f"Skipped (no domain set): {', '.join(skipped_no_domain)}")


if __name__ == "__main__":
    run()
