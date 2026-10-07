from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.core.database import init_db
from app.api.routes.analyze import router as analyze_router
from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.reports import router as reports_router

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_create_tables:
        init_db()
    yield

app = FastAPI(
    title=settings.app_name,
    version="2.2.0",
    description="Personalized medical report explanation using RAG and Narrative Engineering.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(analyze_router, prefix=settings.api_prefix)
app.include_router(reports_router, prefix=settings.api_prefix)

@app.get("/")
def root():
    return {"message": "MedNarrate API", "version": "2.2.0", "docs": "/docs"}
