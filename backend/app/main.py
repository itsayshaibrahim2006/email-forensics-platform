from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import emails, threads, geolocation, reports

app = FastAPI(
    title="AI-Powered Email Thread Detection, Geolocation & Forensic Intelligence Platform",
    description="Backend API for ingesting raw emails, reconstructing threads, "
                 "geolocating routing hops, detecting spoofing, and generating "
                 "forensic reports.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(emails.router)
app.include_router(threads.router)
app.include_router(geolocation.router)
app.include_router(reports.router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "email-forensics-platform-api",
        "docs": "/docs",
    }


@app.get("/api/health")
def health():
    return {"status": "healthy"}
