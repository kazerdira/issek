import pytest
import asyncio
import socketio
from typing import Dict, Any, List
from httpx import AsyncClient

from tests.conftest import TestDataFactory


@pytest.mark.integration
class TestUserFlows:
    """Test complete user flows combining REST API and WebSocket."""

    async def test_complete_user_registration_and_chat_flow(self, client: AsyncClient):
        """Test complete flow from user registration to sending messages."""
        # 1. Register new user
        user_data = TestDataFactory.create_user_data()
        response = await client.post("/api/auth/register", json=user_data)
        assert response.status_code == 201
        
        # Extract user info and token
        user_response = response.json()
        user_id = user_response["id"]
        access_token = user_response["access_token"]
        
        # 2. Create a chat via REST API
        chat_data = {
            "name": "Integration Test Chat",
            "description": "Test chat for integration testing",
            "chat_type": "group",
            "is_public": True
        }
        
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await client.post("/api/chats", json=chat_data, headers=headers)
        assert response.status_code == 201
        chat = response.json()
        
        # 3. Connect to WebSocket and join chat
        ws_client = socketio.AsyncClient()
        messages_received = []
        
        @ws_client.event
        async def new_message(data):
            messages_received.append(data)
        
        try:
            await ws_client.connect("http://localhost:8000", socketio_path="/socket.io/")
            await ws_client.emit("authenticate", {"token": access_token})
            await ws_client.emit("join_chat", {"chat_id": chat["id"]})
            
            await asyncio.sleep(0.1)
            
            # 4. Send message via WebSocket
            message_data = {
                "chat_id": chat["id"],
                "content": "Hello from integration test!",
                "message_type": "text"
            }
            await ws_client.emit("send_message", message_data)
            
            await asyncio.sleep(0.2)
            
            # 5. Verify message was sent and received
            assert len(messages_received) > 0
            assert messages_received[0]["content"] == message_data["content"]
            
            # 6. Get messages via REST API to confirm persistence
            response = await client.get(f"/api/chats/{chat['id']}/messages", headers=headers)
            assert response.status_code == 200
            messages = response.json()
            assert len(messages) > 0
            assert any(msg["content"] == message_data["content"] for msg in messages)
            
        finally:
            await ws_client.disconnect()

    async def test_multi_user_chat_session(self, client: AsyncClient):
        """Test multiple users chatting in real-time."""
        # Create two users
        user1_data = TestDataFactory.create_user_data()
        user2_data = TestDataFactory.create_user_data()
        
        # Register both users
        response1 = await client.post("/api/auth/register", json=user1_data)
        response2 = await client.post("/api/auth/register", json=user2_data)
        
        assert response1.status_code == 201
        assert response2.status_code == 201
        
        user1 = response1.json()
        user2 = response2.json()
        
        # User1 creates a chat
        chat_data = {
            "name": "Multi-User Test Chat",
            "description": "Integration test for multiple users",
            "chat_type": "group",
            "is_public": True
        }
        
        headers1 = {"Authorization": f"Bearer {user1['access_token']}"}
        headers2 = {"Authorization": f"Bearer {user2['access_token']}"}
        
        response = await client.post("/api/chats", json=chat_data, headers=headers1)
        assert response.status_code == 201
        chat = response.json()
        
        # User2 joins the chat via REST API
        response = await client.post(f"/api/chats/{chat['id']}/members", 
                                   json={"user_id": user2["id"]}, 
                                   headers=headers1)
        assert response.status_code == 200
        
        # Setup WebSocket clients
        client1 = socketio.AsyncClient()
        client2 = socketio.AsyncClient()
        
        messages1 = []
        messages2 = []
        
        @client1.event
        async def new_message(data):
            messages1.append(data)
            
        @client2.event
        async def new_message(data):
            messages2.append(data)
        
        try:
            # Connect both clients
            await client1.connect("http://localhost:8000", socketio_path="/socket.io/")
            await client2.connect("http://localhost:8000", socketio_path="/socket.io/")
            
            # Authenticate both clients
            await client1.emit("authenticate", {"token": user1["access_token"]})
            await client2.emit("authenticate", {"token": user2["access_token"]})
            
            # Both join the chat
            await client1.emit("join_chat", {"chat_id": chat["id"]})
            await client2.emit("join_chat", {"chat_id": chat["id"]})
            
            await asyncio.sleep(0.1)
            
            # User1 sends message
            message1_data = {
                "chat_id": chat["id"],
                "content": "Hello from user 1!",
                "message_type": "text"
            }
            await client1.emit("send_message", message1_data)
            
            await asyncio.sleep(0.1)
            
            # User2 sends message
            message2_data = {
                "chat_id": chat["id"], 
                "content": "Hello from user 2!",
                "message_type": "text"
            }
            await client2.emit("send_message", message2_data)
            
            await asyncio.sleep(0.2)
            
            # Both users should have received both messages
            assert len(messages1) >= 1  # User1 should receive user2's message
            assert len(messages2) >= 1  # User2 should receive user1's message
            
            # Check cross-delivery
            user2_message_to_user1 = any(msg["content"] == message2_data["content"] 
                                       for msg in messages1)
            user1_message_to_user2 = any(msg["content"] == message1_data["content"] 
                                       for msg in messages2)
            
            assert user2_message_to_user1
            assert user1_message_to_user2
            
        finally:
            await client1.disconnect()
            await client2.disconnect()

    async def test_friend_request_notification_flow(self, client: AsyncClient):
        """Test friend request flow with real-time notifications."""
        # Create two users
        user1_data = TestDataFactory.create_user_data()
        user2_data = TestDataFactory.create_user_data()
        
        response1 = await client.post("/api/auth/register", json=user1_data)
        response2 = await client.post("/api/auth/register", json=user2_data)
        
        user1 = response1.json()
        user2 = response2.json()
        
        headers1 = {"Authorization": f"Bearer {user1['access_token']}"}
        headers2 = {"Authorization": f"Bearer {user2['access_token']}"}
        
        # Setup WebSocket for user2 to receive notifications
        client2 = socketio.AsyncClient()
        notifications = []
        
        @client2.event
        async def friend_request_received(data):
            notifications.append(("friend_request", data))
            
        @client2.event  
        async def friend_request_accepted(data):
            notifications.append(("friend_accepted", data))
        
        try:
            await client2.connect("http://localhost:8000", socketio_path="/socket.io/")
            await client2.emit("authenticate", {"token": user2["access_token"]})
            
            await asyncio.sleep(0.1)
            
            # User1 sends friend request via REST API
            response = await client.post(f"/api/friends/request", 
                                       json={"user_id": user2["id"]}, 
                                       headers=headers1)
            assert response.status_code == 200
            
            await asyncio.sleep(0.2)
            
            # User2 should receive real-time notification
            friend_requests = [n for n in notifications if n[0] == "friend_request"]
            assert len(friend_requests) > 0
            
            # User2 accepts friend request via REST API
            response = await client.post(f"/api/friends/accept", 
                                       json={"user_id": user1["id"]}, 
                                       headers=headers2)
            assert response.status_code == 200
            
            await asyncio.sleep(0.2)
            
            # Both users should be friends now
            response = await client.get("/api/friends", headers=headers1)
            friends = response.json()
            assert any(friend["id"] == user2["id"] for friend in friends)
            
        finally:
            await client2.disconnect()

    async def test_chat_creation_and_member_management_flow(self, client: AsyncClient):
        """Test complete chat creation and member management."""
        # Create admin user
        admin_data = TestDataFactory.create_user_data()
        response = await client.post("/api/auth/register", json=admin_data)
        admin = response.json()
        admin_headers = {"Authorization": f"Bearer {admin['access_token']}"}
        
        # Create multiple regular users
        users = []
        for i in range(3):
            user_data = TestDataFactory.create_user_data()
            response = await client.post("/api/auth/register", json=user_data)
            users.append(response.json())
        
        # Admin creates a group chat
        chat_data = {
            "name": "Team Chat",
            "description": "Team coordination chat",
            "chat_type": "group",
            "is_public": False
        }
        
        response = await client.post("/api/chats", json=chat_data, headers=admin_headers)
        assert response.status_code == 201
        chat = response.json()
        
        # Admin adds members
        for user in users:
            response = await client.post(f"/api/chats/{chat['id']}/members",
                                       json={"user_id": user["id"]}, 
                                       headers=admin_headers)
            assert response.status_code == 200
        
        # Setup WebSocket connections for all users
        clients = []
        member_updates = []
        
        async def setup_client(user):
            ws_client = socketio.AsyncClient()
            
            @ws_client.event
            async def member_added(data):
                member_updates.append(("added", data))
                
            @ws_client.event
            async def member_removed(data):
                member_updates.append(("removed", data))
                
            @ws_client.event
            async def member_promoted(data):
                member_updates.append(("promoted", data))
            
            await ws_client.connect("http://localhost:8000", socketio_path="/socket.io/")
            await ws_client.emit("authenticate", {"token": user["access_token"]})
            await ws_client.emit("join_chat", {"chat_id": chat["id"]})
            
            return ws_client
        
        try:
            # Connect all users
            for user in users:
                client_ws = await setup_client(user)
                clients.append(client_ws)
            
            await asyncio.sleep(0.2)
            
            # Admin promotes first user to moderator
            response = await client.post(f"/api/chats/{chat['id']}/members/{users[0]['id']}/promote",
                                       headers=admin_headers)
            assert response.status_code == 200
            
            await asyncio.sleep(0.2)
            
            # Admin removes last user
            response = await client.delete(f"/api/chats/{chat['id']}/members/{users[2]['id']}",
                                         headers=admin_headers)
            assert response.status_code == 200
            
            await asyncio.sleep(0.2)
            
            # Check that member updates were broadcast
            assert len(member_updates) > 0
            
            # Verify final member list via REST API
            response = await client.get(f"/api/chats/{chat['id']}/members", headers=admin_headers)
            assert response.status_code == 200
            members = response.json()
            
            # Should have admin + 2 remaining users
            assert len(members) == 3
            
        finally:
            for client_ws in clients:
                await client_ws.disconnect()


@pytest.mark.integration
class TestErrorRecovery:
    """Test error recovery and edge cases in integration scenarios."""

    async def test_websocket_reconnection_preserves_state(self, client: AsyncClient):
        """Test that WebSocket reconnection preserves user state."""
        # Register user
        user_data = TestDataFactory.create_user_data()
        response = await client.post("/api/auth/register", json=user_data)
        user = response.json()
        
        headers = {"Authorization": f"Bearer {user['access_token']}"}
        
        # Create a chat
        chat_data = {
            "name": "Reconnection Test Chat",
            "description": "Testing reconnection",
            "chat_type": "group",
            "is_public": True
        }
        
        response = await client.post("/api/chats", json=chat_data, headers=headers)
        chat = response.json()
        
        ws_client = socketio.AsyncClient()
        messages = []
        
        @ws_client.event
        async def new_message(data):
            messages.append(data)
        
        try:
            # Initial connection
            await ws_client.connect("http://localhost:8000", socketio_path="/socket.io/")
            await ws_client.emit("authenticate", {"token": user["access_token"]})
            await ws_client.emit("join_chat", {"chat_id": chat["id"]})
            
            # Send initial message
            await ws_client.emit("send_message", {
                "chat_id": chat["id"],
                "content": "Message before disconnect",
                "message_type": "text"
            })
            
            await asyncio.sleep(0.1)
            
            # Simulate connection loss
            await ws_client.disconnect()
            
            # Reconnect
            messages.clear()  # Clear previous messages
            await ws_client.connect("http://localhost:8000", socketio_path="/socket.io/")
            await ws_client.emit("authenticate", {"token": user["access_token"]})
            await ws_client.emit("join_chat", {"chat_id": chat["id"]})
            
            # Send message after reconnection
            await ws_client.emit("send_message", {
                "chat_id": chat["id"],
                "content": "Message after reconnect",
                "message_type": "text"
            })
            
            await asyncio.sleep(0.2)
            
            # Should receive message after reconnection
            assert len(messages) > 0
            assert any(msg["content"] == "Message after reconnect" for msg in messages)
            
            # Verify both messages are in database
            response = await client.get(f"/api/chats/{chat['id']}/messages", headers=headers)
            db_messages = response.json()
            assert len(db_messages) >= 2
            
        finally:
            await ws_client.disconnect()

    async def test_concurrent_operations_consistency(self, client: AsyncClient):
        """Test that concurrent REST and WebSocket operations maintain consistency."""
        # Create user
        user_data = TestDataFactory.create_user_data()
        response = await client.post("/api/auth/register", json=user_data)
        user = response.json()
        
        headers = {"Authorization": f"Bearer {user['access_token']}"}
        
        # Create chat
        chat_data = {
            "name": "Concurrent Test Chat",
            "description": "Testing concurrent operations",
            "chat_type": "group",
            "is_public": True
        }
        
        response = await client.post("/api/chats", json=chat_data, headers=headers)
        chat = response.json()
        
        ws_client = socketio.AsyncClient()
        ws_messages = []
        
        @ws_client.event
        async def new_message(data):
            ws_messages.append(data)
        
        try:
            await ws_client.connect("http://localhost:8000", socketio_path="/socket.io/")
            await ws_client.emit("authenticate", {"token": user["access_token"]})
            await ws_client.emit("join_chat", {"chat_id": chat["id"]})
            
            await asyncio.sleep(0.1)
            
            # Concurrent operations: send messages via both REST and WebSocket
            tasks = []
            
            # REST API message
            async def send_rest_message():
                await client.post(f"/api/chats/{chat['id']}/messages",
                                json={
                                    "content": "REST API message",
                                    "message_type": "text"
                                },
                                headers=headers)
            
            # WebSocket message
            async def send_ws_message():
                await ws_client.emit("send_message", {
                    "chat_id": chat["id"],
                    "content": "WebSocket message", 
                    "message_type": "text"
                })
            
            # Send both concurrently
            tasks = [send_rest_message(), send_ws_message()]
            await asyncio.gather(*tasks)
            
            await asyncio.sleep(0.5)
            
            # Check final state via REST API
            response = await client.get(f"/api/chats/{chat['id']}/messages", headers=headers)
            all_messages = response.json()
            
            # Should have both messages
            assert len(all_messages) >= 2
            
            rest_msg = any(msg["content"] == "REST API message" for msg in all_messages)
            ws_msg = any(msg["content"] == "WebSocket message" for msg in all_messages)
            
            assert rest_msg
            assert ws_msg
            
            # WebSocket should have received the REST message too
            ws_rest_msg = any(msg["content"] == "REST API message" for msg in ws_messages)
            assert ws_rest_msg
            
        finally:
            await ws_client.disconnect()

    async def test_token_expiration_handling(self, client: AsyncClient):
        """Test handling of expired tokens in WebSocket connections."""
        # This test would require token expiration to be set to a very short time
        # For now, we'll test with an invalid token to simulate expiration
        
        user_data = TestDataFactory.create_user_data()
        response = await client.post("/api/auth/register", json=user_data)
        user = response.json()
        
        ws_client = socketio.AsyncClient()
        auth_failed = False
        
        @ws_client.event
        async def authentication_failed(data):
            nonlocal auth_failed
            auth_failed = True
        
        try:
            await ws_client.connect("http://localhost:8000", socketio_path="/socket.io/")
            
            # Use corrupted token to simulate expiration
            expired_token = user["access_token"] + "corrupted"
            await ws_client.emit("authenticate", {"token": expired_token})
            
            await asyncio.sleep(0.2)
            
            assert auth_failed
            
        finally:
            await ws_client.disconnect()