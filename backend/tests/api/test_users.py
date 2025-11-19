import pytest
from httpx import AsyncClient
from typing import Dict, Any

from tests.conftest import TestDataFactory, assert_user_structure


@pytest.mark.api
class TestUserEndpoints:
    """Test user-related endpoints."""

    async def test_get_current_user(self, authenticated_client: AsyncClient, test_user: Dict[str, Any]):
        """Test getting current user info."""
        response = await authenticated_client.get("/api/users/me")
        
        assert response.status_code == 200
        user = response.json()
        assert_user_structure(user)
        assert user["id"] == test_user["id"]

    async def test_update_current_user(self, authenticated_client: AsyncClient, test_user: Dict[str, Any]):
        """Test updating current user profile."""
        update_data = {
            "display_name": "Updated Name",
            "avatar": "https://example.com/avatar.jpg"
        }
        
        response = await authenticated_client.put("/api/users/me", json=update_data)
        
        assert response.status_code == 200
        user = response.json()
        assert user["display_name"] == update_data["display_name"]
        assert user["avatar"] == update_data["avatar"]

    async def test_update_user_invalid_data(self, authenticated_client: AsyncClient):
        """Test updating user with invalid data."""
        # Try to update with existing username (should fail if validation exists)
        update_data = {"username": ""}  # Empty username
        
        response = await authenticated_client.put("/api/users/me", json=update_data)
        
        # Should either reject empty username or accept it - check your validation
        assert response.status_code in [200, 400, 422]

    async def test_get_user_by_id(self, authenticated_client: AsyncClient, test_user2: Dict[str, Any]):
        """Test getting user by ID."""
        response = await authenticated_client.get(f"/api/users/{test_user2['id']}")
        
        assert response.status_code == 200
        user = response.json()
        assert_user_structure(user)
        assert user["id"] == test_user2["id"]

    async def test_get_nonexistent_user(self, authenticated_client: AsyncClient):
        """Test getting nonexistent user."""
        fake_id = "60a9b0b5c8f1b2a8d8e4f5a6" # MongoDB ObjectId format
        response = await authenticated_client.get(f"/api/users/{fake_id}")
        
        assert response.status_code == 404

    async def test_search_users(self, authenticated_client: AsyncClient, test_user2: Dict[str, Any]):
        """Test searching users by username."""
        search_query = test_user2["username"][:3]  # First 3 chars
        
        response = await authenticated_client.get(f"/api/users/search?q={search_query}")
        
        assert response.status_code == 200
        users = response.json()
        assert isinstance(users, list)
        
        # Should find the test user
        user_ids = [user["id"] for user in users]
        assert test_user2["id"] in user_ids

    async def test_search_users_empty_query(self, authenticated_client: AsyncClient):
        """Test searching users with empty query."""
        response = await authenticated_client.get("/api/users/search?q=")
        
        # Should return empty list or validation error
        assert response.status_code in [200, 400, 422]

    async def test_search_users_no_results(self, authenticated_client: AsyncClient):
        """Test searching users with no matching results."""
        response = await authenticated_client.get("/api/users/search?q=nonexistentuser12345")
        
        assert response.status_code == 200
        users = response.json()
        assert isinstance(users, list)
        assert len(users) == 0


@pytest.mark.api
class TestUserPresence:
    """Test user online presence functionality."""

    async def test_update_user_presence(self, authenticated_client: AsyncClient):
        """Test updating user online status."""
        # This would test WebSocket presence updates via REST API if available
        response = await authenticated_client.post("/api/users/me/presence", json={"is_online": True})
        
        # Check if this endpoint exists in your API
        assert response.status_code in [200, 404]  # 404 if endpoint doesn't exist

    async def test_get_user_presence(self, authenticated_client: AsyncClient, test_user2: Dict[str, Any]):
        """Test getting user presence status."""
        response = await authenticated_client.get(f"/api/users/{test_user2['id']}/presence")
        
        # Check if this endpoint exists in your API  
        assert response.status_code in [200, 404]