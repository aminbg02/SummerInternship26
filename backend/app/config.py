import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


class Config:
   #flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-change-me")

    #Db

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "postgresql+psycopg://orange:orange@localhost:5432/orange"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    #JWT
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET", "dev-jwt-insecure-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        hours=int(os.environ.get("JWT_HOURS", "12"))
    )

    #encryption  for  api  keys  ---
    FERNET_KEY = os.environ.get("FERNET_KEY")

    # --- Qdrant ---

    QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
    QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")

    # Dedicated Qdrant instances

    QDRANT_DEDICATED_URLS = [
        u.strip()
        for u in os.environ.get(
            "QDRANT_DEDICATED_URLS",

            "http://localhost:6343,http://localhost:6353,http://localhost:6363,"
            "http://localhost:6373,http://localhost:6383,http://localhost:6393,"
            "http://localhost:6403",
        ).split(",")
        if u.strip()
    ]

    # --- Languages ---

    QUERY_TRANSLATION_ENABLED = (
        os.environ.get("QUERY_TRANSLATION_ENABLED", "true").lower() == "true"
    )

    # --- CORS ---
    CORS_ORIGINS = os.environ.get(
        "CORS_ORIGINS", "http://localhost:4200"
    ).split(",")

    # if true => rag.py uses the deterministic in-process embedder (no model download).
    EMBEDDING_FAKE = os.environ.get("EMBEDDING_FAKE", "false").lower() == "true"


    SEARCH_SCORE_THRESHOLD = float(os.environ.get("SEARCH_SCORE_THRESHOLD", "0.0"))

    REQUIRE_SECURE_SECRETS = False

    # --- Generation controls ---

    GEN_DEFAULT_TEMPERATURE = float(os.environ.get("GEN_DEFAULT_TEMPERATURE", "0.2"))
    GEN_TEMPERATURE_MAX = float(os.environ.get("GEN_TEMPERATURE_MAX", "2.0"))
    GEN_DEFAULT_MAX_TOKENS = int(os.environ.get("GEN_DEFAULT_MAX_TOKENS", "1024"))
    GEN_MAX_TOKENS_CEILING = int(os.environ.get("GEN_MAX_TOKENS_CEILING", "4096"))


    PROVIDER_FALLBACK_ENABLED = (
        os.environ.get("PROVIDER_FALLBACK_ENABLED", "false").lower() == "true"
    )

    LLM_TIMEOUT_SECONDS = int(os.environ.get("LLM_TIMEOUT_SECONDS", "15"))
    LLM_NUM_RETRIES = int(os.environ.get("LLM_NUM_RETRIES", "0"))

    LLM_LOCAL_TIMEOUT_SECONDS = int(
        os.environ.get("LLM_LOCAL_TIMEOUT_SECONDS", "120")
    )

    DEFAULT_USER_DAILY_TOKEN_LIMIT = int(
        os.environ.get("DEFAULT_USER_DAILY_TOKEN_LIMIT", "10000")
    )


    FREE_ONLY = os.environ.get("FREE_ONLY", "true").lower() == "true"


    MLFLOW_TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5001")
    MLFLOW_EXPERIMENT_NAME = os.environ.get("MLFLOW_EXPERIMENT_NAME", "rag-queries")
    MLFLOW_TRACING_ENABLED = (
        os.environ.get("MLFLOW_TRACING_ENABLED", "true").lower() == "true"
    )


INSECURE_SECRETS = {
    None,
    "",
    "change-me",
    "dev-insecure-change-me",
    "dev-jwt-insecure-change-me",
}


def validate_runtime_config(config) -> None:
    """dossnt run the app with insecure keys,only works if  the REQUIRE_SECURE_SECRETS variable is turned on """
    if not config.get("REQUIRE_SECURE_SECRETS"):
        return
    problems = []
    if config.get("SECRET_KEY") in INSECURE_SECRETS:
        problems.append("SECRET_KEY")
    if config.get("JWT_SECRET_KEY") in INSECURE_SECRETS:
        problems.append("JWT_SECRET_KEY")
    if not config.get("FERNET_KEY"):
        problems.append("FERNET_KEY")
    if problems:
        raise RuntimeError(
            "Refusing to start with insecure/missing secrets: "
            f"{', '.join(problems)}. Set them via environment variables."
        )


class ProductionConfig(Config):
    DEBUG = False
    REQUIRE_SECURE_SECRETS = True


class TestConfig(Config):
    TESTING = True

    TESTING_IN_MEMORY = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_SECRET_KEY = "test-jwt-secret-at-least-32-bytes-long-000"

    FERNET_KEY = "P8z53l8fINaohIlOWJIq4gukGP30NWrWEOV4hlPt3Sc="
    QDRANT_URL = None

    QDRANT_DEDICATED_URLS = ["memory://dedicated-1", "memory://dedicated-2"]
    EMBEDDING_FAKE = True

    PROVIDER_FALLBACK_ENABLED = False

    SEARCH_SCORE_THRESHOLD = 0.0

    QUERY_TRANSLATION_ENABLED = True

    MLFLOW_TRACING_ENABLED = False
