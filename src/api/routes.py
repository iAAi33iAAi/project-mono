"""API route definitions."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/version")
async def version() -> dict:
    from src import __version__
    return {"version": __version__}
