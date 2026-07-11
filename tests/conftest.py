"""
Shared test fixtures — ALL tests use mocks by default.
"""
import os
import pytest

# FORCE mock mode for ALL tests
os.environ["USE_MOCK_AI"] = "true"

from fastapi.testclient import TestClient
from apps.api.main import app

@pytest.fixture(scope="session")
def client():
    """FastAPI test client with mock services."""
    with TestClient(app) as c:
        yield c

@pytest.fixture
def sample_profile():
    return {
        "company_name": "TestAgriTech",
        "stage": "early-stage",
        "industries": ["agriculture", "technology"],
        "location": {"country": "India", "state": "Karnataka"},
        "funding_needed": {"amount": 5000000, "currency": "INR"},
    }
