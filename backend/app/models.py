"""
Company=Tenant, a customer belongs to one and only one company
every company has an admin
the super admin is not linked to any company but has a x-company-od header in his request
"""
import re
from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def _utcnow():
    return datetime.now(timezone.utc)


def _slugify(name: str) -> str:
    """standarises the names of companies """
    slug = re.sub(r"[^a-z0-9]+", "_", (name or "").lower()).strip("_")
    return slug or "co"


class Company(db.Model):
    __tablename__ = "companies"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)

    # Email domain that identifies this tenant, e.g. "orange.com".
    domain = db.Column(db.String(255), nullable=True, unique=True, index=True)

    daily_token_limit = db.Column(db.Integer, nullable=True)
    daily_request_limit = db.Column(db.Integer, nullable=True)


    qdrant_collection = db.Column(db.String(255), nullable=True, index=True)

    # Which Qdrant INSTANCE holds this tenant's collection.
    #   NULL -> the shared instance
    #   set  -> a dedicated instance claimed from config QDRANT_DEDICATED_URLS.

    qdrant_url = db.Column(db.String(255), nullable=True, index=True)

    # Which embedding model built this tenant's collection,for now all embded by bge-small-en-v1.5
    embedding_model = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)
    users = db.relationship("User", back_populates="company")

    def default_collection_name(self) -> str:
        """The name a collection would get: ``kb_<id>_<slug>``"""
        return f"kb_{self.id}_{_slugify(self.name)}"

    def assign_collection_name(self) -> str:
        """Set the collection name once. Never recomputed — the vectors are already
        under the old one."""
        if not self.qdrant_collection:
            self.qdrant_collection = self.default_collection_name()
        return self.qdrant_collection

    @property
    def isolation(self) -> str:
        """"dedicated" if this tenant has a Qdrant instance to itself, else "shared" ."""
        return "dedicated" if self.qdrant_url else "shared"

    def __repr__(self):
        return f"<Company {self.id} {self.name!r}>"


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)


    role = db.Column(db.String(20), nullable=False, default="customer")

    # NULL only for super_admins

    company_id = db.Column(
        db.Integer, db.ForeignKey("companies.id"), nullable=True, index=True
    )


    daily_token_limit = db.Column(db.Integer, nullable=True)

    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)

    company = db.relationship("Company", back_populates="users")

    def set_password(self, raw: str):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.password_hash, raw)

    @property
    def is_super_admin(self) -> bool:
        return self.role == "super_admin"

    @property
    def is_company_admin(self) -> bool:
        return self.role == "company_admin"

    @property
    def is_company_bound(self) -> bool:
        return self.role in ("company_admin", "customer")

    def __repr__(self):
        return f"<User {self.id} {self.email!r} role={self.role}>"


class LlmProvider(db.Model):

    __tablename__ = "llm_providers"

    id = db.Column(db.Integer, primary_key=True)
    display_name = db.Column(db.String(120), nullable=False)
    provider_key = db.Column(db.String(50), nullable=False)
    base_url = db.Column(db.String(300), nullable=True)  # OpenAI-compatible endpoint
    api_key_encrypted = db.Column(db.Text, nullable=True)
    model_name = db.Column(db.String(150), nullable=False)

    enabled = db.Column(db.Boolean, default=True, nullable=False)
    is_free = db.Column(db.Boolean, default=True, nullable=False)

    rate_limit_rpm = db.Column(db.Integer, nullable=True)
    rate_limit_rpd = db.Column(db.Integer, nullable=True)


    rate_limit_group = db.Column(db.String(60), nullable=True, index=True)
    priority = db.Column(db.Integer, default=100, nullable=False)

    unavailable_until = db.Column(db.DateTime, nullable=True)
    last_error = db.Column(db.String(200), nullable=True)


    default_temperature = db.Column(db.Float, nullable=True)
    max_output_tokens = db.Column(db.Integer, nullable=True)

    company_id = db.Column(
        db.Integer, db.ForeignKey("companies.id"), nullable=True, index=True
    )

    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)

    def public_dict(self) -> dict:
        """data that its okay to expose ,basically not to expose the base url or api keys for a customer/user """
        return {
            "id": self.id,
            "display_name": self.display_name,
            "model_name": self.model_name,
            "is_free": self.is_free,

            "default_temperature": self.default_temperature,
            "max_output_tokens": self.max_output_tokens,
        }

    def admin_dict(self) -> dict:
        """admin view  still never returns the decrypted key, only whether one is set or not """
        return {
            "id": self.id,
            "display_name": self.display_name,
            "provider_key": self.provider_key,
            "base_url": self.base_url,
            "model_name": self.model_name,
            "enabled": self.enabled,
            "is_free": self.is_free,
            "rate_limit_rpm": self.rate_limit_rpm,
            "rate_limit_rpd": self.rate_limit_rpd,
            "rate_limit_group": self.rate_limit_group,
            "priority": self.priority,
            "default_temperature": self.default_temperature,
            "max_output_tokens": self.max_output_tokens,
            "company_id": self.company_id,
            "has_api_key": bool(self.api_key_encrypted),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<LlmProvider {self.id} {self.display_name!r} enabled={self.enabled}>"


class PiiRule(db.Model):

    __tablename__ = "pii_rules"

    id = db.Column(db.Integer, primary_key=True)
    entity_name = db.Column(db.String(50), nullable=False)
    pattern = db.Column(db.String(300), nullable=False)
    score = db.Column(db.Float, default=0.85, nullable=False)
    enabled = db.Column(db.Boolean, default=True, nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=True)

    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def admin_dict(self) -> dict:
        return {
            "id": self.id,
            "entity_name": self.entity_name,
            "pattern": self.pattern,
            "score": self.score,
            "enabled": self.enabled,
            "company_id": self.company_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<PiiRule {self.id} {self.entity_name!r} company_id={self.company_id}>"


class Document(db.Model):
    """record of one uploaded or ingested file .
    ephermal means that the user uploaded during a convo which will eventually be deleted
    kb means it exists in the kb
    """
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(
        db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True
    )
    filename = db.Column(db.String(300), nullable=False)
    # 'uploaded', 'filtered', 'rejected', 'ingested'
    status = db.Column(db.String(30), nullable=False, default="uploaded")
    # 'ephemeral' (ask-with-attachment) or 'kb' (added to knowledge base)
    scope = db.Column(db.String(20), nullable=False, default="ephemeral")
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)

    def __repr__(self):
        return f"<Document {self.id} {self.filename!r} company={self.company_id}>"


class StagedChunk(db.Model):
    """ephemeral, screened text from an ask-with-attachment upload .


    """
    __tablename__ = "staged_chunks"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(
        db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True
    )
    conversation_id = db.Column(
        db.Integer, db.ForeignKey("conversations.id"), nullable=True, index=True
    )
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=True)
    text = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(40), nullable=True)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=True, index=True)


class KbIngestion(db.Model):
    """
    ingesting a document permanently changes what EVERY user at a company can
    retrieve, so each ingestion is logged: who did it, into which company, which
    file, and how many chunks were indexed vs. dropped by the safety gate.
    """
    __tablename__ = "kb_ingestions"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(
        db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True
    )
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    filename = db.Column(db.String(300), nullable=False)
    chunks_indexed = db.Column(db.Integer, default=0, nullable=False)
    chunks_blocked = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False, index=True)


class KbDeletion(db.Model):
    """Audit record for removing a document from the knowledge base .


    """
    __tablename__ = "kb_deletions"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(
        db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True
    )
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=True)
    # Nullable so the audit row can outlive the user who acted .
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    filename = db.Column(db.String(300), nullable=False)
    chunks_deleted = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False, index=True)


class Conversation(db.Model):
    """One chat thread between a user and the assistant, scoped to a company.


    """
    __tablename__ = "conversations"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(
        db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)

    messages = db.relationship(
        "Message", back_populates="conversation", order_by="Message.created_at"
    )


class Message(db.Model):
    """A single turn in a Conversation: a 'user' question or 'assistant' answer.

    Persisted after each successful query so chat history survives a page reload.
    """
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(
        db.Integer, db.ForeignKey("conversations.id"), nullable=False, index=True
    )
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)


    sources = db.Column(db.JSON, nullable=True)

    feedback = db.Column(db.String(10), nullable=True)


    provider_id = db.Column(
        db.Integer, db.ForeignKey("llm_providers.id"), nullable=True, index=True
    )

    conversation = db.relationship("Conversation", back_populates="messages")


class TokenUsage(db.Model):
    __tablename__ = "token_usage"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    provider_id = db.Column(db.Integer, db.ForeignKey("llm_providers.id"), nullable=True, index=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversations.id"), nullable=True)
    prompt_tokens = db.Column(db.Integer, default=0, nullable=False)
    completion_tokens = db.Column(db.Integer, default=0, nullable=False)

    reasoning_tokens = db.Column(db.Integer, default=0, nullable=True)
    total_tokens = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False, index=True)


class TokenRequest(db.Model):

    __tablename__ = "token_requests"

    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )

    company_id = db.Column(
        db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True
    )
    scope = db.Column(db.String(10), nullable=False)  # 'user' or 'company'

    requested_limit = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.Text, nullable=False)

    status = db.Column(db.String(10), nullable=False, default="pending", index=True)

    decision_reason = db.Column(db.Text, nullable=True)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False, index=True)

    def __repr__(self):
        return f"<TokenRequest {self.id} scope={self.scope} status={self.status}>"


class ProviderCallLog(db.Model):

    __tablename__ = "provider_call_log"

    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(
        db.Integer, db.ForeignKey("llm_providers.id"), nullable=False, index=True
    )
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False, index=True)
