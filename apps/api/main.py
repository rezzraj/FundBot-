from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.config import get_settings
from apps.api.dependencies import get_services
from apps.api.api import grants, profiles, matching, applications, chat, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup: Initialize services, build vector index
    services = get_services()
    print("[OK] Services initialized")

    # Index existing grants on startup
    all_grants = services.cloudant.get_all_active_grants()
    count = services.embedding.index_all_grants(all_grants)
    print(f"[OK] Indexed {count} grants in vector store")

    yield

    # Shutdown: cleanup
    print("[INFO] Shutting down...")


app = FastAPI(
    title="AI Grant & Funding Finder API",
    description="AI-powered startup grant discovery, matching, and proposal drafting",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(grants.router, prefix="/api/grants", tags=["Grants"])
app.include_router(profiles.router, prefix="/api/profiles", tags=["Profiles"])
app.include_router(matching.router, prefix="/api/match", tags=["Matching"])
app.include_router(applications.router, prefix="/api/applications", tags=["Applications"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "grant-finder-api"}
