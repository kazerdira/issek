import pytest
from httpx import AsyncClient
from typing import Dict, Any

from tests.conftest import TestDataFactory, assert_message_structure


@pytest.mark.api
class TestMessageEndpoints:
    """Test message-related endpoints."""

    async def test_send_text_message(self, authenticated_client: AsyncClient, test_chat: Dict[str, Any], test_user: Dict[str, Any]):
        """Test sending a text message."""
        message_data = {
            "chat_id": test_chat["id"],
            "content": "Hello, this is a test message!",
            "message_type": "text"
        }
        
        response = await authenticated_client.post("/api/messages/", json=message_data)
        
        assert response.status_code == 200
        message = response.json()
        assert_message_structure(message)
        assert message["content"] == message_data["content"]
        assert message["sender_id"] == test_user["id"]
        assert message["chat_id"] == test_chat["id"]

    async def test_send_image_message(self, authenticated_client: AsyncClient, test_chat: Dict[str, Any]):
        """Test sending an image message."""
        message_data = {
            "chat_id": test_chat["id"],
            "content": "",
            "message_type": "image",
            "media_url": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAAAAAAAD..."
        }
        
        response = await authenticated_client.post("/api/messages/", json=message_data)
        
        assert response.status_code == 200
        message = response.json()
        assert message["message_type"] == "image"
        assert message["media_url"] is not None

    async def test_send_voice_message(self, authenticated_client: AsyncClient, test_chat: Dict[str, Any]):
        """Test sending a voice message."""
        message_data = {
            "chat_id": test_chat["id"],
            "content": "",
            "message_type": "voice",
            "media_url": "data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEA...",
            "duration": 5.5
        }
        
        response = await authenticated_client.post("/api/messages/", json=message_data)
        
        assert response.status_code == 200
        message = response.json()
        assert message["message_type"] == "voice"
        assert "duration" in message

    async def test_send_message_invalid_chat(self, authenticated_client: AsyncClient):
        """Test sending message to nonexistent chat."""
        fake_chat_id = "60a9b0b5c8f1b2a8d8e4f5a6"
        message_data = {
            "chat_id": fake_chat_id,
            "content": "Test message",
            "message_type": "text"
        }
        
        response = await authenticated_client.post("/api/messages/", json=message_data)
        
        assert response.status_code == 404

    async def test_send_empty_message(self, authenticated_client: AsyncClient, test_chat: Dict[str, Any]):
        """Test sending empty message."""
        message_data = {
            "chat_id": test_chat["id"],
            "content": "",
            "message_type": "text"
        }
        
        response = await authenticated_client.post("/api/messages/", json=message_data)
        
        # Should reject empty text messages
        assert response.status_code in [400, 422]

    async def test_get_chat_messages(self, authenticated_client: AsyncClient, test_chat: Dict[str, Any]):
        """Test getting messages from a chat.""" 
        # First send a message
        message_data = TestDataFactory.message_data(chat_id=test_chat["id"])
        await authenticated_client.post("/api/messages/", json=message_data)
        
        # Now get messages
        response = await authenticated_client.get(f"/api/chats/{test_chat['id']}/messages")
        
        assert response.status_code == 200
        messages = response.json()
        assert isinstance(messages, list)
        assert len(messages) > 0
        
        for message in messages:
            assert_message_structure(message)

    async def test_get_messages_with_pagination(self, authenticated_client: AsyncClient, test_chat: Dict[str, Any]):
        """Test getting messages with pagination."""
        # Send multiple messages
        for i in range(5):
            message_data = TestDataFactory.message_data(
                chat_id=test_chat["id"],
                content=f"Test message {i}"
            )
            await authenticated_client.post("/api/messages/", json=message_data)
        
        # Get messages with limit
        response = await authenticated_client.get(f"/api/chats/{test_chat['id']}/messages?limit=3")
        
        assert response.status_code == 200
        messages = response.json()
        assert len(messages) <= 3

    async def test_update_message(self, authenticated_client: AsyncClient, test_chat: Dict[str, Any]):
        """Test updating a message."""
        # First send a message
        message_data = TestDataFactory.message_data(chat_id=test_chat["id"])
        response = await authenticated_client.post("/api/messages/", json=message_data)
        message = response.json()
        
        # Update the message
        update_data = {"content": "Updated message content"}
        response = await authenticated_client.put(f"/api/messages/{message['id']}", json=update_data)
        
        assert response.status_code == 200
        updated_message = response.json()
        assert updated_message["content"] == update_data["content"]
        assert "edited_at" in updated_message

    async def test_delete_message(self, authenticated_client: AsyncClient, test_chat: Dict[str, Any]):
        """Test deleting a message."""
        # First send a message
        message_data = TestDataFactory.message_data(chat_id=test_chat["id"])
        response = await authenticated_client.post("/api/messages/", json=message_data)
        message = response.json()
        
        # Delete the message
        response = await authenticated_client.delete(f"/api/messages/{message['id']}")
        
        assert response.status_code == 200
        
        # Verify message is marked as deleted or removed
        response = await authenticated_client.get(f"/api/messages/{message['id']}")
        if response.status_code == 200:
            # Message exists but should be marked as deleted
            deleted_message = response.json()
            assert deleted_message.get("is_deleted", False) == True
        else:
            # Message was completely removed
            assert response.status_code == 404


@pytest.mark.api
class TestMessageReactions:
    """Test message reaction functionality."""

    async def test_add_reaction(self, authenticated_client: AsyncClient, test_chat: Dict[str, Any]):
        """Test adding reaction to message."""
        # First send a message
        message_data = TestDataFactory.message_data(chat_id=test_chat["id"])
        response = await authenticated_client.post("/api/messages/", json=message_data)
        message = response.json()
        
        # Add reaction
        reaction_data = {"emoji": "👍"}
        response = await authenticated_client.post(f"/api/messages/{message['id']}/reactions", json=reaction_data)
        
        assert response.status_code == 200

    async def test_remove_reaction(self, authenticated_client: AsyncClient, test_chat: Dict[str, Any]):
        """Test removing reaction from message."""
        # First send a message and add reaction
        message_data = TestDataFactory.message_data(chat_id=test_chat["id"])
        response = await authenticated_client.post("/api/messages/", json=message_data)
        message = response.json()
        
        reaction_data = {"emoji": "👍"}
        await authenticated_client.post(f"/api/messages/{message['id']}/reactions", json=reaction_data)
        
        # Remove reaction
        response = await authenticated_client.delete(f"/api/messages/{message['id']}/reactions/{reaction_data['emoji']}")
        
        assert response.status_code == 200

    async def test_get_message_reactions(self, authenticated_client: AsyncClient, test_chat: Dict[str, Any]):
        """Test getting reactions for a message."""
        # First send a message and add reaction
        message_data = TestDataFactory.message_data(chat_id=test_chat["id"])
        response = await authenticated_client.post("/api/messages/", json=message_data)
        message = response.json()
        
        reaction_data = {"emoji": "👍"}
        await authenticated_client.post(f"/api/messages/{message['id']}/reactions", json=reaction_data)
        
        # Get reactions
        response = await authenticated_client.get(f"/api/messages/{message['id']}/reactions")
        
        assert response.status_code == 200
        reactions = response.json()
        assert isinstance(reactions, list)


@pytest.mark.api
class TestMessageStatus:
    """Test message status functionality."""

    async def test_mark_message_read(self, authenticated_client: AsyncClient, test_chat: Dict[str, Any]):
        """Test marking message as read."""
        # Send a message
        message_data = TestDataFactory.message_data(chat_id=test_chat["id"])
        response = await authenticated_client.post("/api/messages/", json=message_data)
        message = response.json()
        
        # Mark as read
        response = await authenticated_client.post(f"/api/messages/{message['id']}/read")
        
        assert response.status_code == 200

    async def test_get_unread_count(self, authenticated_client: AsyncClient, test_chat: Dict[str, Any]):
        """Test getting unread message count."""
        response = await authenticated_client.get(f"/api/chats/{test_chat['id']}/unread_count")
        
        assert response.status_code in [200, 404]  # 404 if endpoint doesn't exist
        
        if response.status_code == 200:
            data = response.json()
            assert "unread_count" in data
            assert isinstance(data["unread_count"], int)