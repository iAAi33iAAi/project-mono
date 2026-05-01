"""API route definitions."""

from fastapi import APIRouter, FastAPI

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/version")
async def version() -> dict[str, str]:
    from src import __version__

    return {"version": __version__}


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="project-mono")
    app.include_router(router)
    return app
