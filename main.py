from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401 — register models with Base.metadata
from app.database import Base, engine
from app.routers import notes, users

try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(
        "WARNING: Could not create database tables. "
        "Check MySQL is running and .env has your real DB_PASSWORD."
    )
    print(f"Details: {e}")

app = FastAPI(
    title="Notes App API",
    description="A multi-user notes service with JWT authentication",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(notes.router)


@app.get("/")
def root():
    return {
        "message": "Notes App API is running!",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


@app.get("/about")
def about():
    return {
        "name": "tejshah",
        "email": "tejshah@email.com",
        "my_features": {
            "Pin Notes": (
                "POST /notes/{id}/pin toggles pin on a note. "
                "Pinned notes appear first in GET /notes. Chosen because it improves UX."
            ),
            "Pagination": (
                "GET /notes?page=1&limit=10 paginates results for performance."
            ),
            "Full-text Search": (
                "GET /notes?q=keyword searches title and content."
            ),
        },
    }


@app.get("/search")
def search_hint():
    return {
        "tip": "Use GET /notes?q=keyword to search notes",
        "example": "/notes?q=meeting",
    }
