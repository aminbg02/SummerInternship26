from flask import Flask, jsonify, request

from .config import Config, validate_runtime_config
from .extensions import cors, db, jwt


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    # insta fails if the secret keys are not set
    validate_runtime_config(app.config)

    # --- Extensions ---
    db.init_app(app)
    jwt.init_app(app)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=True,
    )


    from . import models


    from .services import tracing
    tracing.init_app(app)

    # --- Blueprints ---
    from .blueprints.account import account_bp
    from .blueprints.admin import admin_bp
    from .blueprints.auth import auth_bp
    from .blueprints.conversations import conversations_bp
    from .blueprints.documents import documents_bp
    from .blueprints.providers import providers_bp
    from .blueprints.query import query_bp
    from .blueprints.token_requests import token_requests_bp
    from .blueprints.users import users_bp

    app.register_blueprint(account_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(conversations_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(providers_bp)
    app.register_blueprint(query_bp)
    app.register_blueprint(token_requests_bp)
    app.register_blueprint(users_bp)

    # health check to make sure the api is working
    @app.get("/api/health")
    def health():
        return jsonify(status="ok")

    # --- API responses are never cached ---
    @app.after_request
    def no_store(response):
        """
        never cache header in case the page shows old data after deletion/insert
        """
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    # --- Auto-create tables in dev/test ---
    with app.app_context():
        db.create_all()
        _ensure_added_columns()
        _purge_expired_staged_chunks(app)
        _ensure_company_collections(app)
        _backfill_message_providers(app)


    if not app.config.get("TESTING"):
        _log_active_backends(app)

    return app


def _purge_expired_staged_chunks(app) -> None:
    """
        get rid of all expired ehermal uploads everytime we boot the app
    """
    from .services import retention

    deleted = retention.purge_expired_staged_chunks()
    if deleted and not app.config.get("TESTING"):
        print(f"[orange] Retention: purged {deleted} expired staged chunk(s)")


def _backfill_message_providers(app) -> None:
    """fills in which AI model wrote each saved answer, for old answers where that wasn't recorded.
    """
    from sqlalchemy import func

    from .models import Message, TokenUsage

    # Cheap guard: the common case is nothing to do, so don't run the group-by.
    stale = (
        db.session.query(Message.id)
        .filter(Message.role == "assistant", Message.provider_id.is_(None))
        .first()
    )
    if stale is None:
        return

    rows = (
        db.session.query(
            TokenUsage.conversation_id,
            func.min(TokenUsage.provider_id),
            func.count(func.distinct(TokenUsage.provider_id)),
        )
        .filter(
            TokenUsage.conversation_id.isnot(None),
            TokenUsage.provider_id.isnot(None),
        )
        .group_by(TokenUsage.conversation_id)
        .all()
    )

    # Group conversations BY provider so we update once per provider,

    by_provider: dict = {}
    for conversation_id, provider_id, distinct_providers in rows:
        if distinct_providers == 1:
            by_provider.setdefault(provider_id, []).append(conversation_id)

    updated = 0
    for provider_id, conversation_ids in by_provider.items():
        updated += (
            Message.query.filter(
                Message.conversation_id.in_(conversation_ids),
                Message.role == "assistant",
                Message.provider_id.is_(None),
            ).update({"provider_id": provider_id}, synchronize_session=False)
        )
    db.session.commit()

    if updated and not app.config.get("TESTING"):
        print(f"[orange] Backfilled provider attribution on {updated} answer(s)")


def _ensure_company_collections(app) -> None:
    """
    if a company doesn't have a company qdrant,we create it on boot

    """
    if app.config.get("TESTING"):
        return

    from .services import rag

    try:
        created = rag.ensure_all_company_collections()
    except Exception as exc:
        print(f"[orange] Qdrant: could not provision company collections ({exc})")
        return

    if created:
        print(f"[orange] Qdrant: created {len(created)} missing collection(s): {', '.join(created)}")


def _log_active_backends(app) -> None:
    """logs all active backends and creates missing tables if any
    """
    db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if db_uri.startswith("postgresql"):
        db_desc = f"Postgres ({db_uri.rsplit('@', 1)[-1]})"  # host/db only, no creds
    else:
        db_desc = f"{db_uri!r} (expected Postgres — check DATABASE_URL)"

    qdrant_url = app.config.get("QDRANT_URL")
    vec_desc = (
        f"Qdrant server ({qdrant_url})"
        if qdrant_url
        else "NOT CONFIGURED — set QDRANT_URL, or run `docker compose up -d`"
    )

    print(f"[orange] Database: {db_desc}")
    print(f"[orange] Vectors:  {vec_desc}")



_ADDED_COLUMNS = {
    # table: [(column_name, SQL type)]
    "llm_providers": [
        ("default_temperature", "FLOAT"),
        ("max_output_tokens", "INTEGER"),
        ("unavailable_until", "TIMESTAMP"),
        ("last_error", "VARCHAR(200)"),
        ("rate_limit_group", "VARCHAR(60)"),
    ],
    "token_usage": [
        ("reasoning_tokens", "INTEGER"),
    ],

    "companies": [
        ("domain", "VARCHAR(255)"),
        ("qdrant_collection", "VARCHAR(255)"),
        ("qdrant_url", "VARCHAR(255)"),
        ("embedding_model", "VARCHAR(255)"),
    ],
    "users": [
        ("daily_token_limit", "INTEGER"),
    ],
    "messages": [
        ("sources", "JSON"),
        ("feedback", "VARCHAR(10)"),
        ("provider_id", "INTEGER"),
    ],
    "pii_rules": [
        ("company_id", "INTEGER"),
    ],
}


def _ensure_added_columns():
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    existing_tables = set(inspector.get_table_names())
    for table, columns in _ADDED_COLUMNS.items():
        if table not in existing_tables:
            continue
        have = {c["name"] for c in inspector.get_columns(table)}
        for name, sql_type in columns:
            if name not in have:
                db.session.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}")
                )
        db.session.commit()
