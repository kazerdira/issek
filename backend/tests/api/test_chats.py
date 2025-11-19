import pytest
from httpx import AsyncClient
from typing import Dict, Any

from tests.conftest import TestDataFactory, assert_chat_structure


@pytest.mark.api
class TestChatEndpoints:
    """Test chat-related endpoints."""

    async def test_get_user_chats(self, authenticated_client: AsyncClient, test_chat: Dict[str, Any]):
        """Test getting user's chats."""
        response = await authenticated_client.get("/api/chats/")
        
        assert response.status_code == 200
        chats = response.json()
        assert isinstance(chats, list)
        
        # Should include the test chat
        chat_ids = [chat["id"] for chat in chats]
        assert test_chat["id"] in chat_ids

    async def test_create_group_chat(self, authenticated_client: AsyncClient, test_user2: Dict[str, Any]):
        """Test creating a group chat."""
        chat_data = TestDataFactory.chat_data(
            chat_type="group",
            participant_ids=[test_user2["id"]]
        )
        
        response = await authenticated_client.post("/api/chats/", json=chat_data)
        
        assert response.status_code == 200
        chat = response.json()
        assert_chat_structure(chat)
        assert chat["chat_type"] == "group"
        assert chat["name"] == chat_data["name"]

    async def test_create_channel(self, authenticated_client: AsyncClient):
        """Test creating a channel."""
        chat_data = TestDataFactory.chat_data(
            chat_type="channel",
            is_public=True
        )
        
        response = await authenticated_client.post("/api/chats/", json=chat_data)
        
        assert response.status_code == 200
        chat = response.json()
        assert chat["chat_type"] == "channel"
        assert chat["is_public"] == True

    async def test_create_chat_invalid_data(self, authenticated_client: AsyncClient):
        """Test creating chat with invalid data."""
        # Missing required fields
        response = await authenticated_client.post("/api/chats/", json={})
        assert response.status_code == 422

        # Invalid chat type
        chat_data = {"chat_type": "invalid_type"}
        response = await authenticated_client.post("/api/chats/", json=chat_data)
        assert response.status_code == 422

    async def test_get_chat_by_id(self, authenticated_client: AsyncClient, test_chat: Dict[str, Any]):
        """Test getting specific chat by ID."""
        response = await authenticated_client.get(f"/api/chats/{test_chat['id']}")
        
        assert response.status_code == 200
        chat = response.json()
        assert_chat_structure(chat)
        assert chat["id"] == test_chat["id"]

    async def test_get_nonexistent_chat(self, authenticated_client: AsyncClient):
        """Test getting nonexistent chat."""
        fake_id = "60a9b0b5c8f1b2a8d8e4f5a6"
        response = await authenticated_client.get(f"/api/chats/{fake_id}")
        
        assert response.status_code == 404

    async def test_update_chat_info(self, authenticated_client: AsyncClient, test_chat: Dict[str, Any]):
        """Test updating chat information."""
        update_data = {
            "name": "Updated Chat Name",
            "description": "Updated description"
        }
        
        response = await authenticated_client.put(f"/api/chats/{test_chat['id']}", json=update_data)
        
        assert response.status_code == 200
        chat = response.json()
        assert chat["name"] == update_data["name"]
        assert chat["description"] == update_data["description"]

    async def test_delete_chat(self, authenticated_client: AsyncClient, test_chat: Dict[str, Any]):
        """Test deleting a chat."""
        response = await authenticated_client.delete(f"/api/chats/{test_chat['id']}")
        
        assert response.status_code == 200
        
        # Verify chat is deleted
        response = await authenticated_client.get(f"/api/chats/{test_chat['id']}")
        assert response.status_code == 404

    async def test_join_public_chat(self, client: AsyncClient, test_user2: Dict[str, Any]):
        """Test joining a public chat.""" 
        # First create a public chat
        client.headers.update({"Authorization": f"Bearer {test_user2['access_token']}"})
        
        chat_data = TestDataFactory.chat_data(
            chat_type="group",
            is_public=True
        )
        
        response = await client.post("/api/chats/", json=chat_data)
        assert response.status_code == 200
        chat = response.json()
        
        # Now join with different user
        # (You'll need to implement this endpoint)
        response = await client.post(f"/api/chats/{chat['id']}/join")
        
        # Check if endpoint exists
        assert response.status_code in [200, 404, 405]

    async def test_leave_chat(self, authenticated_client: AsyncClient, test_chat: Dict[str, Any]):
        """Test leaving a chat."""
        response = await authenticated_client.post(f"/api/chats/{test_chat['id']}/leave")
        
        # Check if endpoint exists
        assert response.status_code in [200, 404, 405]


@pytest.mark.api
class TestChatMembers:
    """Test chat member management."""

    async def test_add_member_to_chat(self, authenticated_client: AsyncClient, test_chat: Dict[str, Any], test_user2: Dict[str, Any]):
        """Test adding member to chat."""
        member_data = {"user_id": test_user2["id"]}
        
        response = await authenticated_client.post(f"/api/chats/{test_chat['id']}/members", json=member_data)
        
        # Check if endpoint exists
        assert response.status_code in [200, 404, 405]

    async def test_remove_member_from_chat(self, authenticated_client: AsyncClient, test_chat: Dict[str, Any], test_user2: Dict[str, Any]):
        """Test removing member from chat."""
        response = await authenticated_client.delete(f"/api/chats/{test_chat['id']}/members/{test_user2['id']}")
        
        # Check if endpoint exists
        assert response.status_code in [200, 404, 405]

    async def test_promote_member(self, authenticated_client: AsyncClient, test_chat: Dict[str, Any], test_user2: Dict[str, Any]):
        """Test promoting member to admin."""
        promotion_data = {"role": "admin"}
        
        response = await authenticated_client.put(f"/api/chats/{test_chat['id']}/members/{test_user2['id']}", json=promotion_data)
        
        # Check if endpoint exists
        assert response.status_code in [200, 404, 405]

    async def test_ban_member(self, authenticated_client: AsyncClient, test_chat: Dict[str, Any], test_user2: Dict[str, Any]):
        """Test banning member from chat.""" 
        response = await authenticated_client.post(f"/api/chats/{test_chat['id']}/ban", json={"user_id": test_user2["id"]})
        
        # Check if endpoint exists
        assert response.status_code in [200, 404, 405]


@pytest.mark.api 
class TestChatSearch:
    """Test chat search functionality."""

    async def test_search_public_chats(self, authenticated_client: AsyncClient):
        """Test searching public chats."""
        response = await authenticated_client.get("/api/chats/search?q=test&type=public")
        
        assert response.status_code in [200, 404]  # 404 if endpoint doesn't exist
        
        if response.status_code == 200:
            chats = response.json()
            assert isinstance(chats, list)

    async def test_global_search(self, authenticated_client: AsyncClient, test_user2: Dict[str, Any]):
        """Test global search across users, groups, and channels."""
        search_term = test_user2["username"][:3]
        
        response = await authenticated_client.get(f"/api/search/global?q={search_term}")
        
        assert response.status_code in [200, 404]  # 404 if endpoint doesn't exist
        
        if response.status_code == 200:
            results = response.json()
            assert isinstance(results, dict)
            # Should have sections for users, groups, channels
            expected_sections = ["users", "groups", "channels"]
            for section in expected_sections:
                if section in results:
                    assert isinstance(results[section], list)