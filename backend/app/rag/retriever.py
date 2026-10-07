from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import BACKEND_DIR, get_settings
from app.core.database import SessionLocal
from app.rag.chunker import chunk_document
from app.rag.documents import load_documents
from app.rag.embeddings import EmbeddingService
from app.rag.online_retriever import TrustedOnlineRetriever
from app.rag.pgvector_store import PgVectorStore
from app.schemas.extraction import MedicalFinding
from app.schemas.rag import EvidenceChunk


class Retriever:
    """Hybrid RAG: pgvector first, trusted online fallback when coverage is weak."""

    def __init__(self, db: Session | None = None):
        self.settings = get_settings()
        self._owns_db = db is None
        self.db = db or SessionLocal()
        self.embedding = EmbeddingService(self.settings.embedding_model)
        self.store = PgVectorStore(self.db, self.embedding)
        self.docs_dir = BACKEND_DIR / "knowledge_base" / "medical"
        self.online = TrustedOnlineRetriever()

    def close(self) -> None:
        if self._owns_db:
            self.db.close()

    def ensure_local_knowledge(self) -> int:
        """Idempotently seed bundled curated/development documents into pgvector."""
        docs = load_documents(self.docs_dir)
        chunks = [chunk for doc in docs for chunk in chunk_document(doc)]
        if not chunks:
            raise RuntimeError("Knowledge base is empty")
        return self.store.add_chunks(chunks, origin="local")

    # def _query(self, finding: MedicalFinding) -> str:
    #     return (
    #         f"{finding.test_name} medical test meaning clinical significance "
    #         f"{finding.status} result interpretation patient information"
    #     )
    def _query(self, finding: MedicalFinding) -> str:

        context = finding.description or finding.value or ""

        return (
            f"{finding.test_name} {context} "
            f"medical meaning clinical significance "
            f"patient information"
        )

    def _sufficient(self, evidence: list[EvidenceChunk], finding: MedicalFinding) -> bool:
        if len(evidence) < self.settings.rag_min_local_chunks:
            return False
        test_name = finding.test_name.lower().strip()
        return any(
            test_name in (item.topic or "").lower()
            or test_name in (item.title or "").lower()
            or test_name in item.text.lower()[:350]
            for item in evidence
        )

    def _persist_online(self, items: list[EvidenceChunk]) -> int:
        if not items or not self.settings.dynamic_kb_cache_enabled:
            return 0
        chunks = [item.model_dump(exclude={"score", "origin", "retrieved_at"}) for item in items]
        retrieved_at = None
        if items[0].retrieved_at:
            try:
                retrieved_at = datetime.fromisoformat(items[0].retrieved_at)
            except ValueError:
                retrieved_at = None
        return self.store.add_chunks(chunks, origin="online", retrieved_at=retrieved_at)

    def retrieve_for_finding(self, finding: MedicalFinding) -> list[EvidenceChunk]:
        # Seed is idempotent and only computes embeddings for chunks not already stored.
        self.ensure_local_knowledge()

        query = self._query(finding)
        local_and_cached = self.store.search(
            query,
            top_k=max(self.settings.rag_top_k, self.settings.rag_min_local_chunks + 2),
            score_threshold=self.settings.rag_score_threshold,
        )
        if self._sufficient(local_and_cached, finding):
            return local_and_cached[: self.settings.rag_top_k]

        # Local/cached pgvector knowledge did not cover this concept strongly enough.
        online = self.online.search(query, finding.test_name)
        if online:
            self._persist_online(online)
            # Use live evidence now; it is also permanently available through pgvector
            # for later users and future reports.
            return sorted(
                online + local_and_cached[:2],
                key=lambda e: e.score,
                reverse=True,
            )[: self.settings.rag_top_k + 2]

        return local_and_cached[: self.settings.rag_top_k]

    def retrieve_report(self, findings: list[MedicalFinding]) -> list[EvidenceChunk]:
        unique: dict[tuple[str, str], EvidenceChunk] = {}
        try:
            for finding in findings:
                for evidence in self.retrieve_for_finding(finding):
                    key = (evidence.source_reference or evidence.source, evidence.text[:160])
                    if key not in unique or evidence.score > unique[key].score:
                        unique[key] = evidence
            return sorted(unique.values(), key=lambda e: e.score, reverse=True)[
                : self.settings.rag_report_max_chunks
            ]
        finally:
            self.close()
