"""Integration tests for API endpoints using Starlette TestClient."""

import pytest
from unittest.mock import MagicMock, patch
from starlette.testclient import TestClient

from src.main import create_app
from src.shell.auth import generate_api_key, hash_api_key


@pytest.fixture
def mock_firestore():
    """Mock Firestore client for testing."""
    with patch("src.shell.mcp_server.firestore") as mock_fs:
        mock_client = MagicMock()
        mock_fs.Client.return_value = mock_client
        yield mock_client


@pytest.fixture
def client(mock_firestore):
    """Create test client with mocked Firestore."""
    app = create_app()
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_200(self, client):
        """Health endpoint returns 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_json(self, client):
        """Health endpoint returns JSON with status."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "foodlogr-mcp"


class TestRegisterEndpoint:
    """Tests for /auth/register endpoint."""

    def test_register_success(self, client, mock_firestore):
        """Successful registration returns API key."""
        # Mock the document set operation
        mock_doc = MagicMock()
        mock_firestore.collection.return_value.document.return_value = mock_doc

        response = client.post(
            "/auth/register",
            json={"email": "test@example.com"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "api_key" in data
        assert data["api_key"].startswith("flr_")
        assert "message" in data
        assert "claude_command" in data

    def test_register_missing_email(self, client):
        """Registration without email returns 400."""
        response = client.post("/auth/register", json={})
        assert response.status_code == 400
        assert "error" in response.json()

    def test_register_invalid_email(self, client):
        """Registration with invalid email returns 400."""
        response = client.post(
            "/auth/register",
            json={"email": "not-an-email"}
        )
        assert response.status_code == 400
        assert "error" in response.json()

    def test_register_empty_email(self, client):
        """Registration with empty email returns 400."""
        response = client.post(
            "/auth/register",
            json={"email": ""}
        )
        assert response.status_code == 400


class TestValidateEndpoint:
    """Tests for /auth/validate endpoint."""

    def test_validate_missing_key(self, client):
        """Validation without key returns invalid."""
        response = client.post("/auth/validate", json={})
        data = response.json()
        assert data["valid"] is False

    def test_validate_invalid_format(self, client):
        """Validation with invalid format returns invalid."""
        response = client.post(
            "/auth/validate",
            json={"api_key": "invalid_key"}
        )
        data = response.json()
        assert data["valid"] is False

    def test_validate_nonexistent_key(self, client, mock_firestore):
        """Validation of non-existent key returns invalid."""
        # Mock document that doesn't exist
        mock_doc = MagicMock()
        mock_doc.get.return_value.exists = False
        mock_firestore.collection.return_value.document.return_value = mock_doc

        valid_format_key = generate_api_key()
        response = client.post(
            "/auth/validate",
            json={"api_key": valid_format_key}
        )
        data = response.json()
        assert data["valid"] is False

    def test_validate_existing_key(self, client, mock_firestore):
        """Validation of existing key returns valid."""
        # Mock document that exists
        mock_doc = MagicMock()
        mock_doc.get.return_value.exists = True
        mock_firestore.collection.return_value.document.return_value = mock_doc

        valid_key = generate_api_key()
        response = client.post(
            "/auth/validate",
            json={"api_key": valid_key}
        )
        data = response.json()
        assert data["valid"] is True


class TestCORS:
    """Tests for CORS configuration."""

    def test_cors_preflight_allowed_origin(self, client):
        """CORS preflight from allowed origin returns correct headers."""
        response = client.options(
            "/auth/register",
            headers={
                "Origin": "https://foodlogr.app",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            }
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "https://foodlogr.app"

    def test_cors_preflight_localhost(self, client):
        """CORS preflight from localhost is allowed for dev."""
        response = client.options(
            "/auth/register",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            }
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"

    def test_cors_actual_request(self, client, mock_firestore):
        """Actual request from allowed origin includes CORS headers."""
        mock_doc = MagicMock()
        mock_firestore.collection.return_value.document.return_value = mock_doc

        response = client.post(
            "/auth/register",
            json={"email": "test@example.com"},
            headers={"Origin": "https://foodlogr.app"}
        )
        assert response.headers.get("access-control-allow-origin") == "https://foodlogr.app"
