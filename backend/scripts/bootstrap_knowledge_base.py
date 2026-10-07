from app.core.database import SessionLocal, init_db
from app.rag.retriever import Retriever


if __name__ == "__main__":
    init_db()
    with SessionLocal() as db:
        retriever = Retriever(db=db)
        added = retriever.ensure_local_knowledge()
        print(f"MedNarrate pgvector knowledge base is ready. Added {added} new chunk(s).")
