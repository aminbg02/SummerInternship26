"""MLflow tracing/tracking + prompt registry  the RAG pipeline's observability layer.

"""
from flask import current_app

_prompt_cache = {}


def _enabled() -> bool:
    return bool(current_app.config.get("MLFLOW_TRACING_ENABLED", False))


def init_app(app) -> None:
    """Point the mlflow SDK at the tracking server. Called once from create_app()."""
    if not app.config.get("MLFLOW_TRACING_ENABLED", False):
        return
    try:
        import mlflow

        mlflow.set_tracking_uri(app.config["MLFLOW_TRACKING_URI"])
        mlflow.set_experiment(app.config["MLFLOW_EXPERIMENT_NAME"])
    except Exception as e:  # noqa: BLE001 — startup must never fail on this
        app.logger.warning("mlflow init_app failed, tracing disabled: %s", e)


def get_system_prompt(default: str) -> str:

    if not _enabled():
        return default
    if "system_prompt" in _prompt_cache:
        return _prompt_cache["system_prompt"]
    try:
        import mlflow

        prompt = mlflow.genai.load_prompt("prompts:/rag-system-prompt@production")
        text = prompt.template
        _prompt_cache["system_prompt"] = text
        return text
    except Exception as e:  # noqa: BLE001 — no version registered yet, or server down
        current_app.logger.warning("mlflow get_system_prompt falling back: %s", e)
        return default


def record_trace(
    *, question, messages, chunks, answer, result, provider,
    company_id, conversation_id, message_id, blocked_count, low_relevance_count,
) -> None:

    if not _enabled():
        return
    try:
        import mlflow

        with mlflow.start_span(name="rag_query") as span:
            span.set_inputs({
                "question": question,
                "messages": messages,
                "retrieved_chunks": [
                    {"id": c["id"], "score": c["score"], "text": c["text"]}
                    for c in chunks
                ],
            })
            span.set_outputs({
                "answer": answer,
                "model": result.get("model"),
                "prompt_tokens": result.get("prompt_tokens"),
                "completion_tokens": result.get("completion_tokens"),
                "total_tokens": result.get("total_tokens"),
            })
            span.set_attributes({
                "company_id": company_id,
                "conversation_id": conversation_id,
                "message_id": message_id,
                "provider_key": provider.provider_key,
                "model_name": provider.model_name,
                "blocked_count": blocked_count,
                "low_relevance_count": low_relevance_count,
            })
    except Exception as e:
        current_app.logger.warning("mlflow record_trace failed: %s", e)
