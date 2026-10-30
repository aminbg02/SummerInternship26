"""
emphasies the isolation of the qdrant collection of the clients

"""
import hashlib
import uuid

from flask import current_app
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
    PointStruct,
    VectorParams,
)

from ..extensions import db


EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
VECTOR_SIZE = 384
DISTANCE = Distance.COSINE


_fastembed_model = None


# --------------------------------------------------------------------------- #
# Client + model construction
# --------------------------------------------------------------------------- #
def _company_qdrant_url(company_id: int | None) -> str | None:
    """
    A company with `qdrant_url` set was given an instance of its own at creation
    time (services/qdrant_pool.py); everyone else shares config QDRANT_URL.
    """
    if company_id is None:
        return None
    from ..models import Company

    company = db.session.get(Company, company_id)
    return company.qdrant_url if company is not None else None


def _get_client(company_id: int | None = None) -> QdrantClient:
    """Return the Qdrant client for a tenant its dedicated instance if it has one, else the shared one. Cached per URL."""
    url = _company_qdrant_url(company_id) or current_app.config.get("QDRANT_URL")


    cache_key = url or "__shared__"
    clients = current_app.extensions.setdefault("qdrant_clients", {})
    client = clients.get(cache_key)
    if client is not None:
        return client

    if current_app.config.get("TESTING_IN_MEMORY"):
        client = QdrantClient(location=":memory:")
    elif url:
        client = QdrantClient(url=url, api_key=current_app.config.get("QDRANT_API_KEY"))
    else:
        raise RuntimeError(
            "QDRANT_URL is not set. Qdrant runs in Docker — start it with "
            "`docker compose up -d`, or set QDRANT_URL in your .env."
        )

    clients[cache_key] = client
    return client


def _get_fastembed():
    global _fastembed_model
    if _fastembed_model is None:
        from fastembed import TextEmbedding  # lazy import: heavy

        _fastembed_model = TextEmbedding(model_name=EMBEDDING_MODEL)
    return _fastembed_model


def _fake_embed(text: str):
    """

    Bag-of-token-hashes into VECTOR_SIZE dims, L2-normalised. Not semantically
    strong, but stable and offline — enough to exercise indexing/search/scoping
    without downloading a model. Enabled via config EMBEDDING_FAKE=True.
    """
    vec = [0.0] * VECTOR_SIZE
    for token in text.lower().split():
        h = int(hashlib.md5(token.encode()).hexdigest(), 16)
        vec[h % VECTOR_SIZE] += 1.0
    norm = sum(v * v for v in vec) ** 0.5
    if norm == 0:
        vec[0] = 1.0
        norm = 1.0
    return [v / norm for v in vec]


def embed_texts(texts):
    """Embed a list of strings -> list of float vectors (len == VECTOR_SIZE)."""
    if current_app.config.get("EMBEDDING_FAKE"):
        return [_fake_embed(t) for t in texts]
    model = _get_fastembed()
    return [list(v) for v in model.embed(list(texts))]


def embed_query(text: str):
    return embed_texts([text])[0]



def _collection_name(company_id: int) -> str:
    """Physical collection name for a tenant: ``kb_<id>_<slug>``.
   """
    from ..models import Company  # lazy: avoid import cycle at module load

    company = db.session.get(Company, company_id)
    if company is None:
        return f"kb_{company_id}"
    return company.qdrant_collection or company.default_collection_name()


def get_or_create_company_collection(company_id: int) -> str:
    """Ensure `kb_<company_id>` exists; return its name.
    """
    from ..models import Company  # lazy: avoid import cycle at module load

    client = _get_client(company_id)
    name = _collection_name(company_id)
    company = db.session.get(Company, company_id)

    if client.collection_exists(name):

        info = client.get_collection(name)
        existing = info.config.params.vectors.size
        if existing != VECTOR_SIZE:
            raise RuntimeError(
                f"Collection {name} has vector size {existing}, but the active "
                f"embedding model produces {VECTOR_SIZE}. Refusing to mix "
                f"embedding models in one collection — re-index instead."
            )

        if company is not None:
            if company.embedding_model is None:

                company.embedding_model = EMBEDDING_MODEL
                db.session.commit()
            elif company.embedding_model != EMBEDDING_MODEL:
                raise RuntimeError(
                    f"Collection {name} was built with embedding model "
                    f"{company.embedding_model!r}, but the active model is "
                    f"{EMBEDDING_MODEL!r}. Both may produce {VECTOR_SIZE}-dim "
                    "vectors, so the size check above would not catch this. "
                    "Refusing to index/search with a mismatched model — re-index "
                    "the collection, then update Company.embedding_model."
                )
        return name

    client.create_collection(
        collection_name=name,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=DISTANCE),
    )
    if company is not None:
        company.embedding_model = EMBEDDING_MODEL
        db.session.commit()
    return name


def ensure_all_company_collections() -> list[str]:
    """Backfill missing collection names, then create any missing collections.
    Returns what it created.


    """
    from ..models import Company  # lazy: avoid import cycle at module load

    created = []
    for company in Company.query.order_by(Company.id).all():
        company.assign_collection_name()

        client = _get_client(company.id)
        if not client.collection_exists(company.qdrant_collection):
            created.append(get_or_create_company_collection(company.id))

    db.session.commit()  # persist any names filled in above
    return created


def index_chunks(company_id: int, chunks, base_payload=None) -> int:
    """Embed and upsert text chunks into the company's collection.


    """
    chunks = [c for c in chunks if c and c.strip()]
    if not chunks:
        return 0

    name = get_or_create_company_collection(company_id)
    client = _get_client(company_id)
    vectors = embed_texts(chunks)

    points = []
    for text, vector in zip(chunks, vectors):
        payload = {"text": text, "company_id": company_id}
        if base_payload:
            payload.update(base_payload)
        points.append(
            PointStruct(id=str(uuid.uuid4()), vector=vector, payload=payload)
        )

    client.upsert(collection_name=name, points=points)
    return len(points)


def search(company_id: int, query: str, k: int = 5):
    """Return up to k chunks from THIS company's collection only."""

    client = _get_client(company_id)
    name = _collection_name(company_id)
    if not client.collection_exists(name):
        # Company has no indexed documents yet — return empty, don't error.
        return []

    query_vec = embed_query(query)  # embed the question into the same vector space
    hits = client.search(
        collection_name=name, query_vector=query_vec, limit=k, with_payload=True
    )
    return [
        {
            "id": h.id,
            "score": h.score,
            "text": (h.payload or {}).get("text", ""),
            "payload": h.payload or {},
        }
        for h in hits
    ]


def get_document_chunks(company_id: int, document_id: int):
    """Read back the chunks of ONE indexed document — the text as it really sits
    in the collection, post-screening and split as it was embedded.

    """
    client = _get_client(company_id)
    name = _collection_name(company_id)
    if not client.collection_exists(name):
        return []

    selector = Filter(
        must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
    )
    points, _ = client.scroll(
        collection_name=name,
        scroll_filter=selector,
        limit=500,  # a single document's chunks; far above any real document
        with_payload=True,
        with_vectors=False,  # 384 floats are noise to a human reader
    )
    return [{"id": str(p.id), "text": (p.payload or {}).get("text", "")} for p in points]


def delete_document(company_id: int, document_id: int) -> int:
    """Remove every chunk of ONE document from a company's collection.
    """
    client = _get_client(company_id)
    name = _collection_name(company_id)
    if not client.collection_exists(name):
        return 0

    selector = Filter(
        must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
    )


    removed = client.count(
        collection_name=name, count_filter=selector, exact=True
    ).count
    if removed:
        client.delete(collection_name=name, points_selector=FilterSelector(filter=selector))
    return removed


def reset_company_collection(company_id: int) -> None:
    """Delete a company's collection if it exists ."""
    client = _get_client(company_id)
    name = _collection_name(company_id)
    if client.collection_exists(name):
        client.delete_collection(name)
