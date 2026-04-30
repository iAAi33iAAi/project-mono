"""Shared test fixtures."""

import pytest
from fastapi.testclient import TestClient

from src.api.routes import create_app


@pytest.fixture()
def client() -> TestClient:
    """Return a TestClient wired to the app."""
    return TestClient(create_app())
