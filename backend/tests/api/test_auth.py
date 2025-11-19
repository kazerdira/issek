import pytest
from httpx import AsyncClient
from typing import Dict, Any

from tests.conftest import TestDataFactory, assert_user_structure


@pytest.mark.api
class TestAuthEndpoints:
    """Test authentication endpoints."""

    async def test_register_success(self, client: AsyncClient):
        """Test successful user registration."""
        user_data = TestDataFactory.user_data()
        
        response = await client.post("/api/auth/register", json=user_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data
        assert_user_structure(data["user"])
        assert data["user"]["username"] == user_data["username"]

    async def test_register_duplicate_username(self, client: AsyncClient, test_user: Dict[str, Any]):
        """Test registration with duplicate username."""
        user_data = TestDataFactory.user_data(username=test_user["username"])
        
        response = await client.post("/api/auth/register", json=user_data)
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    async def test_register_duplicate_email(self, client: AsyncClient, test_user: Dict[str, Any]):
        """Test registration with duplicate email."""
        user_data = TestDataFactory.user_data(email=test_user["email"])
        
        response = await client.post("/api/auth/register", json=user_data)
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    async def test_register_invalid_data(self, client: AsyncClient):
        """Test registration with invalid data."""
        # Missing required fields
        response = await client.post("/api/auth/register", json={})
        assert response.status_code == 422

        # Invalid email format
        user_data = TestDataFactory.user_data(email="invalid-email")
        response = await client.post("/api/auth/register", json=user_data)
        assert response.status_code == 422

    async def test_login_success(self, client: AsyncClient, test_user: Dict[str, Any]):
        """Test successful login with username."""
        login_data = {
            "username": test_user["username"],
            "password": test_user["password"]
        }
        
        response = await client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data
        assert_user_structure(data["user"])

    async def test_login_with_email(self, client: AsyncClient, test_user: Dict[str, Any]):
        """Test successful login with email."""
        login_data = {
            "email": test_user["email"],
            "password": test_user["password"]
        }
        
        response = await client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    async def test_login_invalid_credentials(self, client: AsyncClient, test_user: Dict[str, Any]):
        """Test login with invalid credentials."""
        login_data = {
            "username": test_user["username"],
            "password": "wrong_password"
        }
        
        response = await client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with nonexistent user."""
        login_data = {
            "username": "nonexistent_user",
            "password": "password"
        }
        
        response = await client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 401

    async def test_refresh_token_success(self, client: AsyncClient, test_user: Dict[str, Any]):
        """Test successful token refresh."""
        refresh_data = {"refresh_token": test_user["refresh_token"]}
        
        response = await client.post("/api/auth/refresh", json=refresh_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_refresh_token_invalid(self, client: AsyncClient):
        """Test token refresh with invalid token."""
        refresh_data = {"refresh_token": "invalid_token"}
        
        response = await client.post("/api/auth/refresh", json=refresh_data)
        
        assert response.status_code == 401

    async def test_logout_success(self, authenticated_client: AsyncClient):
        """Test successful logout."""
        response = await authenticated_client.post("/api/auth/logout")
        
        assert response.status_code == 200
        assert "successfully" in response.json()["message"].lower()

    async def test_logout_unauthenticated(self, client: AsyncClient):
        """Test logout without authentication."""
        response = await client.post("/api/auth/logout")
        
        assert response.status_code == 401


@pytest.mark.api  
class TestAuthProtection:
    """Test authentication protection on endpoints."""

    async def test_protected_endpoint_without_token(self, client: AsyncClient):
        """Test accessing protected endpoint without token."""
        response = await client.get("/api/users/me")
        assert response.status_code == 401

    async def test_protected_endpoint_with_invalid_token(self, client: AsyncClient):
        """Test accessing protected endpoint with invalid token.""" 
        client.headers.update({"Authorization": "Bearer invalid_token"})
        response = await client.get("/api/users/me")
        assert response.status_code == 401

    async def test_protected_endpoint_with_valid_token(self, authenticated_client: AsyncClient):
        """Test accessing protected endpoint with valid token."""
        response = await authenticated_client.get("/api/users/me")
        assert response.status_code == 200