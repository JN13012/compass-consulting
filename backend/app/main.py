from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.benchmarks import router as benchmarks_router
from app.api.health import router as health_router
from app.api.interviews import router as interviews_router
from app.api.kb import router as kb_router
from app.api.missions import router as missions_router
from app.api.poc import router as poc_router
from app.api.watch import router as watch_router
from app.core.config import get_settings

app = FastAPI(title="Compass API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(kb_router)
app.include_router(missions_router)
app.include_router(poc_router)
app.include_router(benchmarks_router)
app.include_router(interviews_router)
app.include_router(watch_router)
