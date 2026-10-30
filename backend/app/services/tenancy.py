"""

the platform infers which company a user belongs to from the domain of their
email address
"""
from ..extensions import db
from ..models import Company, User


def domain_of_email(email: str) -> str | None:

    if not email or email.count("@") != 1:
        return None
    domain = email.split("@", 1)[1].strip().lower()
    return domain or None


def company_name_from_domain(domain: str) -> str:

    label = domain.split(".", 1)[0] if domain else domain
    return label.capitalize() if label else domain


def get_company_by_domain(domain: str) -> Company | None:

    if not domain:
        return None
    return Company.query.filter_by(domain=domain).first()


def get_or_create_company_by_domain(domain: str, *, name: str | None = None) -> Company:

    company = get_company_by_domain(domain)
    if company is not None:
        return company
    company = Company(name=name or company_name_from_domain(domain), domain=domain)
    db.session.add(company)
    db.session.flush()  # assign company.id without ending the transaction
    company.assign_collection_name()  # needs the id; fixed now so a later rename can't move it
    return company


def move_users_to_domain(company, old_domain: str | None, new_domain: str | None) -> dict:

    result = {"moved": [], "skipped": []}
    if not old_domain or not new_domain or old_domain == new_domain:
        return result

    for user in list(company.users):
        if domain_of_email(user.email) != old_domain:
            continue

        local_part = user.email.split("@", 1)[0]
        new_email = f"{local_part}@{new_domain}".lower()

        clash = User.query.filter(
            User.email == new_email, User.id != user.id
        ).first()
        if clash is not None:
            result["skipped"].append({"email": user.email, "reason": "email_taken"})
            continue

        result["moved"].append({"from": user.email, "to": new_email})
        user.email = new_email

    return result
