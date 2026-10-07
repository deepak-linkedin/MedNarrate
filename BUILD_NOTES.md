# MedNarrate pgvector Build Notes

## Migration completed

- Removed FAISS and all local vector-index files.
- Added the Python `pgvector` package.
- Added PostgreSQL `vector` extension initialization.
- Added `medical_knowledge_chunks` with `vector(384)` embeddings.
- Added HNSW cosine index creation.
- Bundled medical documents are chunked, embedded, and inserted idempotently into PostgreSQL.
- Trusted online evidence is now embedded directly into the same pgvector table with provenance.
- Dynamic web knowledge survives backend restarts because vectors are stored in PostgreSQL.
- Hybrid flow is now: pgvector semantic search → trusted online fallback → persist new evidence into pgvector.
- Retained PNG/JPG/JPEG OCR and scanned-PDF OCR support.
- Retained JWT HttpOnly-cookie authentication, profiles, protected report history, Narrative Engineering, and safety validation.

## Important database note

Use a fresh database for the cleanest transition from older FAISS builds. The new required extension is:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

The backend executes this automatically when `AUTO_CREATE_TABLES=true`.

## Embedding contract

The current embedding model is `sentence-transformers/all-MiniLM-L6-v2` and the database column is `vector(384)`.
If the embedding model is replaced with a model that has a different dimension, the vector column/schema must also be migrated.

## Validation limitation in the build environment

The execution environment used to package this repository did not have outbound package-registry access, so the newly added `pgvector` Python dependency could not be installed there. Source-level compilation and the dependency-independent test suite were still checked; run `pip install -r requirements.txt` in your normal development/deployment environment before executing the application.
