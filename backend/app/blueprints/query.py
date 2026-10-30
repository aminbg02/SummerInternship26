"""The RAG pipeline.

    question (+ provider_id)
        screen the question       (least-trusted input in the request)
        RAG search, company-scoped
        screen every chunk
        [+ staged upload chunks]
         llm_router.complete()     (rate-limited, usage-logged)
        filter the reply
         grounded answer

"""
from flask import Blueprint, current_app, g, jsonify, request

from ..extensions import db
from ..models import Company, Conversation, Message
from ..security import current_company_id, require_auth
from ..services import languages, llm_router, rag, screening, tracing, translation, usage
from ..services import filter as content_filter
from .documents import get_staged_context
from .providers import enabled_providers_for, resolve_enabled_provider

query_bp = Blueprint("query", __name__, url_prefix="/api")

SYSTEM_PROMPT = (
    "You are a friendly customer-support assistant for {company}. "
    "For factual questions about products, services, or policies, answer using "
    "ONLY the information in the provided context. If the answer is not in the "
    "context, say you don't have that information — do not invent details or "
    "use outside knowledge. Don't offer to look further or search for more "
    "details yourself — you only have the documents already given to you, so "
    "instead tell the customer to contact human support for that request. "
    "Greetings, thanks, and small talk are not factual questions: respond to "
    "them warmly and naturally (e.g. greet back, offer to help) without needing "
    "any context. "
    "Keep answers concise: 2-3 sentences for most questions, and use a short "
    "bullet list only when there are 3 or more distinct items to enumerate."
)


LANGUAGE_INSTRUCTION = (
    " The user's language is {language}. Write your entire reply in {language}, "
    "even though the context documents are in English. Do not translate product "
    "names, or quote the English text verbatim — answer naturally in {language}."
)


def _to_float_or_none(value):
    """None rather than an error, so the router falls back to its default."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int_or_none(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _build_messages(company_name, context_texts, question, locale=None):
    if context_texts:
        context = "\n---\n".join(context_texts)
    else:
        context = "(no relevant documents were found)"
    system = tracing.get_system_prompt(default=SYSTEM_PROMPT).format(
        company=company_name or "the company"
    )
    if not languages.is_english(locale):
        system += LANGUAGE_INSTRUCTION.format(language=languages.name_of(locale))
    user = f"Context:\n{context}\n\nQuestion: {question}"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _resolve_conversation(company_id, user_id, conversation_id):
    """Existing conversation or a new one. Someone else's is rejected, never reused."""
    if conversation_id is not None:
        convo = db.session.get(Conversation, conversation_id)
        if convo is None or convo.company_id != company_id or convo.user_id != user_id:
            return None, (jsonify(error="conversation_not_found"), 404)
        return convo, None

    convo = Conversation(company_id=company_id, user_id=user_id)
    db.session.add(convo)
    db.session.flush()  # assign an id
    return convo, None


def _retrieve_and_screen(company_id, question, k, threshold):

    hits = rag.search(company_id, question, k=k)
    chunks = []
    blocked = 0
    low_relevance = 0
    for hit in hits:
        if hit.get("score", 0.0) < threshold:
            low_relevance += 1
            continue
        verdict = screening.screen_chunk(hit.get("text", ""), company_id=company_id)
        if verdict["action"] == "blocked":
            blocked += 1
            continue
        chunks.append({
            "id": hit["id"],
            "score": hit["score"],
            "text": verdict["text"],  # redacted where needed
            "category": verdict["category"],
            "redacted": bool(verdict["pii"]),
            "payload": hit.get("payload", {}),
        })
    return chunks, blocked, low_relevance


def _sources_from_chunks(chunks):
    """A compact,citation list to persist with an assistant answer."""
    best = {}
    for chunk in chunks:
        payload = chunk.get("payload") or {}
        filename = payload.get("filename")
        if not filename:
            continue
        document_id = payload.get("document_id")
        key = document_id if document_id is not None else filename
        score = float(chunk.get("score") or 0.0)
        if key not in best or score > best[key]["score"]:
            best[key] = {
                "document_id": document_id,
                "filename": filename,
                "score": round(score, 4),
            }
    return sorted(best.values(), key=lambda s: s["score"], reverse=True)


def _candidate_providers(chosen, company_id):
    """The chosen provider first, then the rest by priority if fallback is on."""
    if not current_app.config.get("PROVIDER_FALLBACK_ENABLED", True):
        return [chosen]
    chain = [chosen]
    for candidate in enabled_providers_for(company_id):
        if candidate.id != chosen.id:
            chain.append(candidate)
    return chain


@query_bp.post("/query")
@require_auth
def query():
    company_id, err = current_company_id()
    if err:
        return err  #  an admin who forgot the X-Company-Id header

    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify(error="question_required"), 400


    q_verdict = screening.screen_chunk(question, company_id=company_id)
    if q_verdict["action"] == "blocked":
        return jsonify(error="question_blocked", reasons=q_verdict["reasons"]), 400
    question_redacted = bool(q_verdict["pii"])
    question = q_verdict["text"]
    # Clamp k so a caller can't ask for a huge or negative number.
    k = data.get("k", 5)
    try:
        k = max(1, min(int(k), 20))
    except (TypeError, ValueError):
        k = 5

    provider_id = data.get("provider_id")
    conversation_id = data.get("conversation_id")

    locale = languages.normalise(data.get("locale"))


    temperature = _to_float_or_none(data.get("temperature"))
    max_tokens = _to_int_or_none(data.get("max_tokens"))


    threshold = data.get("min_score")
    try:
        threshold = float(threshold)
    except (TypeError, ValueError):
        threshold = current_app.config.get("SEARCH_SCORE_THRESHOLD", 0.0)

    # The documents and their vectors are English, and so is the embedding model,so a non-English question has to be translated BEFORE it is embedded
    search_question, was_translated = translation.to_english(
        question, locale, company_id=company_id, user_id=g.current_user.id
    )

    # company_id came from the token. A company_id in the body is never read.
    chunks, blocked, low_relevance = _retrieve_and_screen(
        company_id, search_question, k, threshold
    )

    response = {
        "company_id": company_id,
        "question": question,  # screened, not raw
        "question_redacted": question_redacted,
        "chunks": chunks,
        "count": len(chunks),
        "blocked": blocked,
        "low_relevance": low_relevance,
        "grounded": len(chunks) > 0,
        "locale": locale,
        "search_question": search_question if was_translated else None,
    }


    if provider_id is None:
        return jsonify(response)

    provider = resolve_enabled_provider(provider_id, company_id)
    if provider is None:
        return jsonify(error="provider_not_available", provider_id=provider_id), 400

    convo, err = _resolve_conversation(company_id, g.current_user.id, conversation_id)
    if err:
        return err

    context_texts = [c["text"] for c in chunks]
    context_texts += get_staged_context(company_id, convo.id)

    company = db.session.get(Company, company_id)

    messages = _build_messages(
        company.name if company else None, context_texts, question, locale
    )


    result = None
    used = None
    last_rate_error = None
    for candidate in _candidate_providers(provider, company_id):
        try:
            result = llm_router.complete(
                candidate, messages,
                company_id=company_id, user_id=g.current_user.id, conversation_id=convo.id,
                temperature=temperature, max_tokens=max_tokens,
            )
            used = candidate
            break
        except usage.QuotaExceeded as e:

            db.session.rollback()
            return jsonify(
                error="quota_exceeded", scope=e.scope, quota_type=e.quota_type,
                limit=e.limit, detail=str(e),
            ), 429
        except usage.RateLimitExceeded as e:

            last_rate_error = e
            continue
        except llm_router.LlmRouterError as e:

            db.session.rollback()
            cooldown, reason = usage.classify_failure(str(e))
            return jsonify(
                error="llm_call_failed", detail=str(e), provider_id=candidate.id,
                reason=reason, retry_after=int(cooldown.total_seconds()),
            ), 502

    if used is None:

        db.session.rollback()
        return jsonify(
            error="rate_limited", detail=str(last_rate_error), provider_id=provider.id,
            reason=usage.REASON_AT_CAPACITY,
            retry_after=last_rate_error.window_seconds if last_rate_error else 60,
        ), 429


    answer_verdict = content_filter.apply_filter(result["content"], company_id=company_id)
    answer = answer_verdict["clean_text"]


    answer_sources = _sources_from_chunks(chunks)
    db.session.add(Message(conversation_id=convo.id, role="user", content=question))
    assistant_msg = Message(
        conversation_id=convo.id, role="assistant", content=answer,
        sources=answer_sources or None,

        provider_id=used.id,
    )
    db.session.add(assistant_msg)
    if not convo.title:
        convo.title = question[:80]
    db.session.commit()

    tracing.record_trace(
        question=question, messages=messages, chunks=chunks, answer=answer,
        result=result, provider=used, company_id=company_id,
        conversation_id=convo.id, message_id=assistant_msg.id,
        blocked_count=blocked, low_relevance_count=low_relevance,
    )

    response.update(
        answer=answer,
        answer_redacted=bool(answer_verdict["pii"]),
        provider_id=used.id,
        provider=used.display_name,
        requested_provider_id=provider.id,
        fell_back=used.id != provider.id,
        conversation_id=convo.id,
        message_id=assistant_msg.id,
        sources=answer_sources,
        grounded=len(context_texts) > 0,
        usage={
            "prompt_tokens": result["prompt_tokens"],
            "completion_tokens": result["completion_tokens"],
            "total_tokens": result["total_tokens"],
        },
        params=result["params"],
    )
    return jsonify(response)
