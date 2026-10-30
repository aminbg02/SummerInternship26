import argparse
import json
import os
import statistics
import sys
import time

# So `import app` resolves regardless of CWD — see register_prompt.py's identical comment.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mlflow

from app import create_app
from app.blueprints.query import _retrieve_and_screen
from app.config import Config
from app.models import Company, LlmProvider
from app.services import filter as content_filter
from app.services import llm_router
from app.services import tracing

PROMPT_NAME = "rag-system-prompt"
EVAL_EXPERIMENT_NAME = "rag-eval"
GOLDEN_SET_PATH = os.path.join(os.path.dirname(__file__), "..", "eval_data", "golden_qa.json")


def keyword_coverage(answer: str, keywords: list[str]) -> float:
    """Fraction of expected_keywords found (case-insensitive substring) in the
    answer. Crude on purpose — this is a fast regression check, not a judge."""
    if not keywords:
        return 1.0
    text = (answer or "").lower()
    hits = sum(1 for kw in keywords if kw.lower() in text)
    return hits / len(keywords)


def _load_golden_set(company_key: str) -> list[dict]:
    """golden_qa.json is keyed per company (matching seed_docs.py's
    COMPANY_LOOKUP keys, lowercased) — each company's sample docs cover
    different ground, so a shared question set can't be grounded/checkable
    for all of them. `company_key` is `company.name.strip().lower()`."""
    with open(GOLDEN_SET_PATH, encoding="utf-8") as f:
        all_golden = json.load(f)
    golden = all_golden.get(company_key)
    if golden is None:
        raise SystemExit(
            f"No golden set for company '{company_key}' — eval_data/golden_qa.json "
            f"only has questions for: {', '.join(sorted(all_golden))}"
        )
    return golden


def _resolve_company(company_id):
    if company_id is not None:
        return Company.query.get(company_id)
    return Company.query.order_by(Company.id).first()


def _resolve_provider(provider_id, company_id):
    if provider_id is not None:
        return LlmProvider.query.get(provider_id)
    return (
        LlmProvider.query.filter_by(enabled=True)
        .filter((LlmProvider.company_id == company_id) | (LlmProvider.company_id.is_(None)))
        .order_by(LlmProvider.priority)
        .first()
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--alias", default="production", help="Prompt alias/version to evaluate")
    parser.add_argument("--company-id", type=int, default=None)
    parser.add_argument("--provider-id", type=int, default=None)
    parser.add_argument("--k", type=int, default=5)
    args = parser.parse_args()


    mlflow.set_tracking_uri(Config.MLFLOW_TRACKING_URI)

    app = create_app(Config)
    with app.app_context():
        mlflow.set_experiment(EVAL_EXPERIMENT_NAME)

        company = _resolve_company(args.company_id)
        if company is None:
            raise SystemExit("No company found — seed the database first.")
        provider = _resolve_provider(args.provider_id, company.id)
        if provider is None:
            raise SystemExit(f"No enabled provider found for company {company.id}.")

        prompt = mlflow.genai.load_prompt(f"prompts:/{PROMPT_NAME}@{args.alias}")
        threshold = app.config.get("SEARCH_SCORE_THRESHOLD", 0.0)

        golden = _load_golden_set(company.name.strip().lower())
        scores = []


        for i, row in enumerate(golden):
            question = row["question"]
            keywords = row["expected_keywords"]


            if i > 0:
                time.sleep(2.5)

            try:
                mlflow.set_experiment(EVAL_EXPERIMENT_NAME)
                with mlflow.start_span(name="golden_qa_question") as span:
                    chunks, _blocked, _low_relevance = _retrieve_and_screen(
                        company.id, question, args.k, threshold
                    )
                    context_texts = [c["text"] for c in chunks]
                    system = prompt.format(company=company.name or "the company")
                    context = "\n---\n".join(context_texts) if context_texts else (
                        "(no relevant documents were found)"
                    )
                    messages = [
                        {"role": "system", "content": system},
                        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
                    ]
                    result = llm_router.complete(provider, messages)
                    answer = content_filter.apply_filter(result["content"])["clean_text"]

                    span.set_inputs({"question": question, "messages": messages})
                    span.set_outputs({"answer": answer, "model": result.get("model")})
                    span.set_attributes({
                        "company_id": company.id,
                        "provider_key": provider.provider_key,
                        "model_name": provider.model_name,
                    })
            except llm_router.LlmRouterError as e:

                print(f"  [ERR ] Q: {question}\n         {e}\n")
                scores.append(0.0)
                continue

            score = keyword_coverage(answer, keywords)
            scores.append(score)


            mlflow.flush_trace_async_logging()
            trace_id = mlflow.get_last_active_trace_id()
            if trace_id:
                mlflow.log_feedback(
                    trace_id=trace_id,
                    name="keyword_coverage",
                    value=score,
                    rationale=f"expected keywords: {keywords}",
                )


            mlflow.set_experiment(app.config["MLFLOW_EXPERIMENT_NAME"])
            tracing.record_trace(
                question=question, messages=messages, chunks=chunks, answer=answer,
                result=result, provider=provider, company_id=company.id,
                conversation_id=None, message_id=None,
                blocked_count=_blocked, low_relevance_count=_low_relevance,
            )

            print(f"  [{score:.2f}] Q: {question}\n         A: {answer}\n")

        mean_score = statistics.mean(scores) if scores else 0.0

        mlflow.set_experiment(EVAL_EXPERIMENT_NAME)
        with mlflow.start_run(run_name=f"golden-qa-{company.name}-{args.alias}") as run:
            mlflow.set_tag("company_id", company.id)
            mlflow.set_tag("company_name", company.name)
            mlflow.set_tag("provider_id", provider.id)
            mlflow.set_tag("prompt_alias", args.alias)
            mlflow.set_tag("prompt_version", prompt.version)
            mlflow.log_metric("mean_keyword_coverage", mean_score)
            mlflow.log_param("num_questions", len(golden))

        print(
            f"Evaluated '{PROMPT_NAME}@{args.alias}' (version {prompt.version}) for "
            f"company '{company.name}' against {len(golden)} golden questions."
        )
        print(f"Mean keyword coverage: {mean_score:.3f}")
        print(f"MLflow run: {run.info.run_id} (experiment '{EVAL_EXPERIMENT_NAME}')")


if __name__ == "__main__":
    main()
