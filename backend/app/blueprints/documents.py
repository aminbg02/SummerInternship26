"""Document upload either add it to the knowledge base or ephermal just for the current conversation

"""
from datetime import datetime, timedelta, timezone

from flask import Blueprint, g, jsonify, request

from ..extensions import db
from ..models import Document, KbDeletion, KbIngestion, StagedChunk
from ..security import current_company_id, require_auth, require_role
from ..services import chunking, extract, rag, retention, screening

documents_bp = Blueprint("documents", __name__, url_prefix="/api/documents")

# How long staged  chunks live before they're  expired.
STAGED_TTL_HOURS = 24

MAX_UPLOAD_BYTES = 10_000_000  # 10 MB raw


def _extract_text():
    """Pull the upload's filename + text from either a multipart file or JSON.
    Returns (filename, text, conversation_id, error_response).
    """
    conversation_id = None

    # Multipart file upload.
    if "file" in request.files:
        f = request.files["file"]
        raw = f.read()
        if len(raw) > MAX_UPLOAD_BYTES:
            return None, None, None, (jsonify(error="file_too_large"), 413)
        filename = f.filename or "upload.txt"
        try:
            text = extract.extract_text(filename, raw)
        except extract.ExtractionError as e:
            # Bad/corrupt/undecodable file
            return None, None, None, (
                jsonify(error="unsupported_file", hint=str(e)),
                415,
            )
        conversation_id = request.form.get("conversation_id", type=int)
        return filename, text, conversation_id, None

    # JSON body: {filename, text, conversation_id}.
    data = request.get_json(silent=True) or {}
    text = data.get("text")
    if text:
        return (
            data.get("filename") or "upload.txt",
            text,
            data.get("conversation_id"),
            None,
        )

    return None, None, None, (jsonify(error="no_file_or_text"), 400)


@documents_bp.post("/upload")
@require_auth
def upload():

    company_id, err = current_company_id()
    if err:
        return err

    filename, text, conversation_id, err = _extract_text()
    if err:
        return err
    if not text.strip():
        return jsonify(error="empty_document"), 400

    retention.purge_expired_staged_chunks()

    document = Document(
        company_id=company_id,
        filename=filename,
        scope="ephemeral",
        status="uploaded",
        created_by=g.current_user.id,
    )
    db.session.add(document)
    db.session.flush()

    expires_at = datetime.now(timezone.utc) + timedelta(hours=STAGED_TTL_HOURS)

    accepted = blocked = redacted = 0
    categories = set()
    staged_ids = []

    for chunk in chunking.chunk_text(text):
        verdict = screening.screen_chunk(chunk, company_id=company_id)
        if verdict["action"] == "blocked":
            blocked += 1
            continue
        if verdict["action"] == "redacted":
            redacted += 1
        accepted += 1
        categories.add(verdict["category"])

        staged = StagedChunk(
            company_id=company_id,
            conversation_id=conversation_id,
            document_id=document.id,
            text=verdict["text"],
            category=verdict["category"],
            expires_at=expires_at,
        )
        db.session.add(staged)
        db.session.flush()
        staged_ids.append(staged.id)


    document.status = "filtered" if accepted else "rejected"
    db.session.commit()

    return jsonify(
        document_id=document.id,
        filename=filename,
        scope="ephemeral",
        conversation_id=conversation_id,
        accepted_chunks=accepted,
        blocked_chunks=blocked,
        redacted_chunks=redacted,
        categories=sorted(categories),
        staged_chunk_ids=staged_ids,
    )


def get_staged_context(company_id, conversation_id):
    """Return the still-valid staged chunk texts for a conversation.
    """
    if conversation_id is None:
        return []
    now = datetime.now(timezone.utc)
    chunks = (
        StagedChunk.query.filter(
            StagedChunk.company_id == company_id,
            StagedChunk.conversation_id == conversation_id,
            db.or_(StagedChunk.expires_at.is_(None), StagedChunk.expires_at > now),
        )
        .order_by(StagedChunk.id)
        .all()
    )
    return [c.text for c in chunks]


@documents_bp.get("/staged")
@require_auth
def list_staged():
    """Return the still-valid staged chunks for a conversation (own company only).
    """
    company_id, err = current_company_id()
    if err:
        return err

    conversation_id = request.args.get("conversation_id", type=int)
    now = datetime.now(timezone.utc)

    q = StagedChunk.query.filter(
        StagedChunk.company_id == company_id,
        db.or_(StagedChunk.expires_at.is_(None), StagedChunk.expires_at > now),
    )
    if conversation_id is not None:
        q = q.filter(StagedChunk.conversation_id == conversation_id)

    chunks = q.order_by(StagedChunk.id).all()
    return jsonify(
        chunks=[
            {"id": c.id, "text": c.text, "category": c.category}
            for c in chunks
        ]
    )


@documents_bp.post("/ingest")
@require_role("super_admin", "company_admin")
def ingest():
    """Add-to-knowledge-base aka qdrant
    """
    company_id, err = current_company_id()
    if err:
        return err

    filename, text, _conversation_id, err = _extract_text()
    if err:
        return err
    if not text.strip():
        return jsonify(error="empty_document"), 400

    # Screen first
    passing = []
    blocked = 0
    categories = set()
    for chunk in chunking.chunk_text(text):
        verdict = screening.screen_chunk(chunk, company_id=company_id)
        if verdict["action"] == "blocked":
            blocked += 1
            continue
        passing.append(verdict["text"])  # redacted where needed
        categories.add(verdict["category"])

    if not passing:

        return jsonify(error="nothing_to_ingest", blocked_chunks=blocked), 400

    # Record the document, then permanently index into the company's collection.
    document = Document(
        company_id=company_id,
        filename=filename,
        scope="kb",  # permanent, unlike 'ephemeral'
        status="ingested",
        created_by=g.current_user.id,
    )
    db.session.add(document)
    db.session.flush()

    indexed = rag.index_chunks(
        company_id, passing,
        base_payload={"filename": filename, "document_id": document.id, "source": "kb"},
    )

    # Audit trail: who ingested what, into which company, when.
    db.session.add(
        KbIngestion(
            company_id=company_id,
            document_id=document.id,
            user_id=g.current_user.id,
            filename=filename,
            chunks_indexed=indexed,
            chunks_blocked=blocked,
        )
    )
    db.session.commit()

    return jsonify(
        document_id=document.id,
        filename=filename,
        scope="kb",  # explicitly added to the permanent knowledge base
        company_id=company_id,
        chunks_indexed=indexed,
        chunks_blocked=blocked,
        categories=sorted(categories),
    )


@documents_bp.get("/kb/<int:document_id>/content")
@require_role("super_admin", "company_admin")
def kb_document_content(document_id):
    """What is actually indexed for ONE document.
    The ingest log only proves a file was accepted.
    This shows the text as it
    really sits in the collectionpost-screening
    """
    company_id, err = current_company_id()
    if err:
        return err

    document = Document.query.filter_by(
        id=document_id, company_id=company_id
    ).first()
    if document is None:
        return jsonify(error="document_not_found"), 404
    if document.scope != "kb":
        return jsonify(error="not_a_kb_document", scope=document.scope), 400

    chunks = rag.get_document_chunks(company_id, document.id)
    return jsonify(
        document_id=document.id,
        filename=document.filename,
        company_id=company_id,
        chunks=chunks,
    )


@documents_bp.delete("/kb/<int:document_id>")
@require_role("super_admin", "company_admin")
def delete_from_kb(document_id):
    """The undo for /ingest: remove one document's chunks from kb_<company_id>.

    """
    company_id, err = current_company_id()
    if err:
        return err

    document = Document.query.filter_by(
        id=document_id, company_id=company_id
    ).first()
    if document is None:
        return jsonify(error="document_not_found"), 404
    if document.scope != "kb":
        # Ephemeral uploads were never in the KB; they expire on their own.
        return jsonify(error="not_a_kb_document", scope=document.scope), 400

    removed = rag.delete_document(company_id, document.id)

    document.status = "deleted"
    db.session.add(
        KbDeletion(
            company_id=company_id,
            document_id=document.id,
            user_id=g.current_user.id,
            filename=document.filename,
            chunks_deleted=removed,
        )
    )
    db.session.commit()

    return jsonify(
        document_id=document.id,
        filename=document.filename,
        company_id=company_id,
        chunks_deleted=removed,
    )
