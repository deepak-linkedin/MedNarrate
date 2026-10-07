from __future__ import annotations

import hashlib
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.db_models import MedicalKnowledgeChunk
from app.rag.embeddings import EmbeddingService
from app.schemas.rag import EvidenceChunk


class PgVectorStore:
    """Persistent semantic store for both curated and dynamically retrieved evidence."""

    def __init__(self, db: Session, embedding: EmbeddingService):
        self.db = db
        self.embedding = embedding

    @staticmethod
    def _hash(source_reference: str | None, text: str) -> str:
        payload = f"{source_reference or ''}\n{text}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def add_chunks(self, chunks: list[dict], origin: str = "local", retrieved_at: datetime | None = None) -> int:
        if not chunks:
            return 0

        prepared = []
        hashes = []
        for chunk in chunks:
            digest = self._hash(chunk.get("source_reference"), chunk["text"])
            item = dict(chunk)
            item["content_hash"] = digest
            prepared.append(item)
            hashes.append(digest)

        existing = set(
            self.db.scalars(
                select(MedicalKnowledgeChunk.content_hash).where(MedicalKnowledgeChunk.content_hash.in_(hashes))
            ).all()
        )
        new_items = [item for item in prepared if item["content_hash"] not in existing]
        if not new_items:
            return 0

        vectors = self.embedding.encode([item["text"] for item in new_items])
        for item, vector in zip(new_items, vectors):
            self.db.add(MedicalKnowledgeChunk(
                topic=item.get("topic") or "medical concept",
                source=item.get("source") or "unknown",
                organization=item.get("organization") or "Unknown source",
                title=item.get("title") or item.get("topic") or "Medical reference",
                source_reference=item.get("source_reference") or "",
                chunk_id=int(item.get("chunk_id") or 0),
                text=item["text"],
                content_hash=item["content_hash"],
                origin=origin,
                embedding=vector.tolist(),
                retrieved_at=retrieved_at,
            ))
        self.db.commit()
        return len(new_items)

    def search(self, query: str, top_k: int, score_threshold: float = 0.0) -> list[EvidenceChunk]:
        query_vector = self.embedding.encode([query])[0].tolist()
        distance = MedicalKnowledgeChunk.embedding.cosine_distance(query_vector).label("distance")
        rows = self.db.execute(
            select(MedicalKnowledgeChunk, distance)
            .order_by(distance)
            .limit(top_k)
        ).all()

        results: list[EvidenceChunk] = []
        for row, dist in rows:
            score = 1.0 - float(dist)
            if score < score_threshold:
                continue
            results.append(EvidenceChunk(
                source=row.source,
                chunk_id=row.chunk_id,
                topic=row.topic,
                organization=row.organization,
                title=row.title,
                source_reference=row.source_reference,
                text=row.text,
                score=score,
                origin="cached_online" if row.origin == "online" else "local",
                retrieved_at=row.retrieved_at.isoformat() if row.retrieved_at else None,
            ))
        return results
