from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.routes import auth, analysis, experiences, interview, research, user
from core.config import settings
from core.logging import setup_logging
from models.base import Base
from models.database import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Job Copilot",
    description="AI Job Search Companion API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(research.router, prefix="/api/research", tags=["research"])
app.include_router(interview.router, prefix="/api/interview", tags=["interview"])
app.include_router(user.router, prefix="/api/user", tags=["user"])
app.include_router(experiences.router, prefix="/api/experiences", tags=["experiences"])


from fastapi.responses import FileResponse

@app.get("/api/files/{filename}")
async def download_file(filename: str):
    import os
    path = os.path.join(os.path.dirname(__file__), "uploads", filename)
    if not os.path.exists(path):
        raise HTTPException(404)
    return FileResponse(path, filename=filename)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
