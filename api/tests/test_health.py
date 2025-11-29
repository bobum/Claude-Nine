"""
Tests for health check endpoints.
"""

import pytest


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_check(self, client):
        """Test basic health check."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert data["service"] == "claude-nine-api"

    def test_database_health_check(self, client):
        """Test database health check."""
        response = client.get("/health/db")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["database"] == "connected"

    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Claude-Nine API"
        assert "version" in data
        assert "docs" in data
