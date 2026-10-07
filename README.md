# MedNarrate

**MedNarrate** is a full-stack capstone application that converts medical reports into evidence-grounded, audience-adapted educational explanations.

The central design principle is:

> **Medical understanding and communication personalization are separate stages.**

The same medical facts can therefore be communicated differently to users with different ages, education levels, and medical knowledge without changing the underlying report values.

## Major features

- Landing page
- Registration and login
- JWT authentication in **HttpOnly cookies**
- CSRF protection for authenticated mutations
- Persistent user profile: name, age, education, medical knowledge, preferred language
- Protected dashboard and user-specific report history
- Upload **PDF, TXT, PNG, JPG, or JPEG** reports
- OCR for report images
- OCR fallback for scanned/image-only PDFs
- Structured medical finding extraction
- **Persistent RAG with PostgreSQL + pgvector**
- Trusted online medical retrieval when stored knowledge is insufficient
- Allow-listed medical domains only
- Online evidence is embedded and permanently added to pgvector for future retrieval
- Source/provenance display in the UI
- Report-level clinical interpretation
- Deterministic Narrative Engineering
- Personalized narrative realization
- Safety/fidelity validation
- Rich result page with important findings, relationships, limitations, clinician questions, and sources

## Final architecture

```text
Medical Report
(PDF / TXT / PNG / JPG / JPEG)
        ↓
Document Extraction
  ├─ native text extraction
  └─ OCR for images/scanned PDFs
        ↓
Structured Medical Finding Extraction (LLM)
        ↓
Hybrid RAG
  ├─ PostgreSQL + pgvector semantic retrieval
  │    ├─ bundled curated medical chunks
  │    └─ previously cached trusted-online chunks
  └─ trusted online search fallback when coverage is weak
        ↓
Report-Level Clinical Interpretation (LLM)
        ↓
User Profile
        +
Deterministic Narrative Engineering
        ↓
Narrative Realization (LLM)
        ↓
Safety / Fidelity Validation
        ↓
Personalized Medical Explanation
        ↓
PostgreSQL persistence
```

## Why pgvector instead of FAISS?

This version intentionally removes FAISS.

The application already depends on PostgreSQL, so pgvector gives one persistent storage layer for:

- user/account data;
- report sessions;
- extracted findings;
- medical knowledge chunks;
- vector embeddings;
- trusted source provenance.

This is especially useful in cloud deployments where a local FAISS index can be lost when the backend filesystem is recreated.

The default embedding model is:

```text
sentence-transformers/all-MiniLM-L6-v2
```

It produces **384-dimensional normalized embeddings**, so the vector column is `vector(384)`.

## Hybrid RAG behavior

For each extracted medical finding:

```text
Finding
  ↓
Create medical retrieval query
  ↓
Cosine similarity search in pgvector
  ↓
Enough relevant evidence?
  ├─ Yes → use stored evidence
  └─ No
       ↓
Domain-restricted trusted online search
       ↓
Validate returned source domain
       ↓
Chunk trusted content
       ↓
Use evidence for current report
       ↓
Generate embeddings
       ↓
Persist chunks + embeddings + provenance in pgvector
       ↓
Future reports can retrieve them directly from PostgreSQL
```

The online provider is currently **Tavily** because it supports domain-restricted search and source URLs. Returned URLs are checked again against the application allow-list.

Default trusted domains:

- `medlineplus.gov`
- `nih.gov`
- `nlm.nih.gov`
- `cdc.gov`
- `who.int`
- `nhs.uk`
- `msdmanuals.com`

The online query contains the medical concept/test name and general interpretation context, not the user's name, age, uploaded document, or full report text.

## Persistent RAG table

The main knowledge table is:

```text
medical_knowledge_chunks
```

It stores approximately:

```text
id
topic
source
organization
title
source_reference
chunk_id
text
content_hash
origin
embedding vector(384)
retrieved_at
created_at
updated_at
```

`content_hash` makes ingestion idempotent, so restarting the service does not duplicate the same chunks.

An HNSW index using cosine distance is created automatically:

```sql
USING hnsw (embedding vector_cosine_ops)
```

## OCR

Image reports are processed with **RapidOCR + ONNX Runtime**, so deployment does not require a separate Tesseract executable.

Supported report formats:

- `.txt`
- `.pdf`
- `.png`
- `.jpg`
- `.jpeg`

For PDFs, MedNarrate first attempts native text extraction. If there is insufficient text, the pages are rendered and OCR is used.

## Product result page

The UI presents:

1. Report at a glance
2. Important findings with the uploaded report's reference intervals
3. Personalized explanation
4. How findings relate to each other
5. Possible patterns when supported
6. Possible symptom/experience associations
7. What the report cannot determine
8. Questions to discuss with a clinician
9. Why the explanation was personalized this way
10. Medical evidence sources and provenance

## Technology stack

**Backend:** Python, FastAPI, SQLAlchemy, PostgreSQL, pgvector, Pydantic, PyJWT  
**LLM:** Gemini through a provider abstraction + deterministic mock provider  
**RAG:** Sentence Transformers (`all-MiniLM-L6-v2`) + PostgreSQL/pgvector + Tavily trusted-web fallback  
**OCR:** RapidOCR + ONNX Runtime + PyMuPDF  
**Frontend:** React, Vite, React Router, JavaScript  
**Auth:** PBKDF2-SHA256 password hashing, HttpOnly JWT cookies, CSRF protection

# Local setup

## 1. PostgreSQL + pgvector

Create the database once:

```sql
CREATE DATABASE mednarrate;
```

The backend runs:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

at startup before creating tables.

If your PostgreSQL installation does not have pgvector available, install/enable the pgvector extension for that PostgreSQL server first. Managed deployment providers must also support the `vector` extension.

For this pgvector release, using a fresh database is recommended if you previously ran the FAISS-based MedNarrate versions.

## 2. Backend

Windows PowerShell:

```powershell
cd backend
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Fill only the actual values in `.env`.

Minimum local values:

```env
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/mednarrate
JWT_SECRET_KEY=YOUR_LONG_RANDOM_SECRET
```

For a quota-free local generation test:

```env
LLM_PROVIDER=mock
```

For Gemini:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=YOUR_GEMINI_KEY
```

For trusted online RAG fallback:

```env
ONLINE_RAG_ENABLED=true
TAVILY_API_KEY=YOUR_TAVILY_KEY
```

Start the API:

```powershell
uvicorn app.main:app --reload
```

The application creates the `vector` extension, database tables, and HNSW vector index automatically when `AUTO_CREATE_TABLES=true`.

The bundled medical knowledge is seeded lazily on the first RAG request. You can optionally seed it in advance:

```powershell
python scripts\bootstrap_knowledge_base.py
```

That command is idempotent.

Backend: `http://127.0.0.1:8000`  
Swagger: `http://127.0.0.1:8000/docs`

## 3. Frontend

```powershell
cd ..\frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Frontend: `http://localhost:5173`

# Production environment

Backend:

```env
APP_ENV=production
DATABASE_URL=...
JWT_SECRET_KEY=...
GEMINI_API_KEY=...
TAVILY_API_KEY=...
LLM_PROVIDER=gemini
ONLINE_RAG_ENABLED=true
FRONTEND_URL=https://YOUR-FRONTEND
CORS_ORIGINS=https://YOUR-FRONTEND
COOKIE_SECURE=true
COOKIE_SAMESITE=none
AUTO_CREATE_TABLES=true
PERSIST_RESULTS=true
OCR_ENABLED=true
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

Frontend:

```env
VITE_API_BASE_URL=https://YOUR-BACKEND/api
```

# Deployment

## Backend — Render

A root `render.yaml` is included.

1. Push the repository to GitHub.
2. Create a PostgreSQL database/provider that supports pgvector.
3. Create the Render web service from `render.yaml`.
4. Fill `DATABASE_URL`, `JWT_SECRET_KEY`, `GEMINI_API_KEY`, `TAVILY_API_KEY`, `FRONTEND_URL`, and `CORS_ORIGINS`.
5. Deploy.
6. At API startup, MedNarrate enables the `vector` extension and creates its tables/indexes.
7. On the first report analysis, bundled knowledge chunks are inserted into pgvector if they are not already present.

No FAISS index file and no persistent backend filesystem are required.

## Frontend — Vercel

1. Import the repository.
2. Set Root Directory to `frontend`.
3. Framework: Vite.
4. Set `VITE_API_BASE_URL`.
5. Deploy.

# Database tables

The application creates:

- `users`
- `user_profiles`
- `report_sessions`
- `finding_records`
- `medical_knowledge_chunks`

The last table replaces both the old FAISS index and the old `rag_knowledge_cache` design.

# Security and privacy notes

- Passwords are hashed; plaintext passwords are never stored.
- JWTs remain in HttpOnly cookies.
- Authenticated mutations use CSRF protection.
- CORS is restricted to configured frontend origins.
- Reports belong to the authenticated user.
- Raw uploads are processed in memory and are not intentionally persisted.
- Online RAG queries do not include user identity or the full report.
- Retrieved medical content retains source provenance.

This is a capstone/MVP security design, not a claim of regulatory compliance.

# Medical safety boundary

MedNarrate is an educational explanation tool, not a doctor, diagnostic system, prescription system, or replacement for professional medical advice.

The system is designed to:

- preserve extracted values and units;
- prioritize the reference interval printed on the uploaded report;
- avoid unsupported definitive diagnoses;
- avoid prescriptions and unsupported treatment recommendations;
- communicate uncertainty;
- explain relationships only when supported;
- show evidence provenance;
- validate generated narratives for fidelity and risky language.

# Testing

```powershell
cd backend
pytest -q
```

The tests avoid downloading the embedding model where RAG is not under test. A live pgvector integration test requires a PostgreSQL database with the `vector` extension enabled.

# Capstone demo

Use `backend/sample_reports/sample_cbc.txt` or `sample_cbc_image.png` and compare different profiles:

1. Age 8 / Primary School / Beginner
2. Age 25 / Engineering / Beginner
3. Age 65 / Primary School / Beginner
4. Age 25 / MBBS / Advanced

The medical facts should remain consistent while vocabulary, technical depth, analogy usage, detail, and communication structure change.
