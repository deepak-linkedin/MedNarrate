from pydantic import BaseModel


class EvidenceChunk(BaseModel):
    source: str
    chunk_id: int
    topic: str | None = None
    organization: str | None = None
    title: str | None = None
    source_reference: str | None = None
    text: str
    score: float
    origin: str = "local"  # local | online | cached_online
    retrieved_at: str | None = None
