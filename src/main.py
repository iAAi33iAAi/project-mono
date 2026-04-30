"""Application entrypoint."""

import logging

from src.api.routes import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Boot the application."""
    logger.info("Starting project-mono v%s", "0.1.0")
    app = create_app()
    # In production, use a proper ASGI server (uvicorn, gunicorn).
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
