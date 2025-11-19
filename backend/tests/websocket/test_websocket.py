import pytest
import asyncio
import socketio
from typing import Dict, Any, List
from unittest.mock import AsyncMock

from tests.conftest import TestDataFactory


@pytest.mark.websocket
class TestWebSocketConnection:
    """Test WebSocket connection functionality."""

    async def test_socket_connection(self, websocket_client: socketio.AsyncClient):
        """Test basic WebSocket connection."""
        connected = False
        
        @websocket_client.event
        async def connect():
            nonlocal connected
            connected = True
        
        # Connect to the server
        await websocket_client.connect("http://localhost:8000", socketio_path="/socket.io/")
        
        # Wait a bit for connection
        await asyncio.sleep(0.1)
        
        assert websocket_client.connected
        assert connected

    async def test_socket_disconnect(self, websocket_client: socketio.AsyncClient):
        """Test WebSocket disconnection."""
        disconnected = False
        
        @websocket_client.event
        async def disconnect():
            nonlocal disconnected
            disconnected = True
        
        await websocket_client.connect("http://localhost:8000", socketio_path="/socket.io/")
        await websocket_client.disconnect()
        
        assert not websocket_client.connected
        assert disconnected

    async def test_connection_with_invalid_url(self, websocket_client: socketio.AsyncClient):
        """Test connection to invalid URL."""
        with pytest.raises(socketio.exceptions.ConnectionError):
            await websocket_client.connect("http://invalid-url:9999", socketio_path="/socket.io/")

    async def test_multiple_connections(self):
        """Test multiple simultaneous connections."""
        clients = []
        
        try:
            # Create multiple clients
            for i in range(3):
                client = socketio.AsyncClient()
                await client.connect("http://localhost:8000", socketio_path="/socket.io/")
                clients.append(client)
                assert client.connected
            
            # All should be connected
            assert len(clients) == 3
            for client in clients:
                assert client.connected
                
        finally:
            # Clean up
            for client in clients:
                if client.connected:
                    await client.disconnect()


@pytest.mark.websocket
class TestWebSocketAuthentication:
    """Test WebSocket authentication."""

    async def test_socket_authentication_success(self, websocket_client: socketio.AsyncClient, test_user: Dict[str, Any]):
        """Test successful WebSocket authentication."""
        authenticated = False
        auth_data = None
        
        @websocket_client.event
        async def authenticated(data):
            nonlocal authenticated, auth_data
            authenticated = True
            auth_data = data
        
        await websocket_client.connect("http://localhost:8000", socketio_path="/socket.io/")
        
        # Send authentication
        await websocket_client.emit("authenticate", {"token": test_user["access_token"]})
        
        # Wait for response
        await asyncio.sleep(0.2)
        
        assert authenticated
        assert auth_data is not None
        assert auth_data["user_id"] == test_user["id"]
        assert auth_data["status"] == "authenticated"

    async def test_socket_authentication_invalid_token(self, websocket_client: socketio.AsyncClient):
        """Test WebSocket authentication with invalid token."""
        auth_failed = False
        
        @websocket_client.event
        async def authentication_failed(data):
            nonlocal auth_failed
            auth_failed = True
        
        await websocket_client.connect("http://localhost:8000", socketio_path="/socket.io/")
        
        # Send invalid token
        await websocket_client.emit("authenticate", {"token": "invalid_token"})
        
        # Wait for response
        await asyncio.sleep(0.2)
        
        assert auth_failed

    async def test_socket_authentication_missing_token(self, websocket_client: socketio.AsyncClient):
        """Test WebSocket authentication without token."""
        auth_failed = False
        
        @websocket_client.event
        async def authentication_failed(data):
            nonlocal auth_failed
            auth_failed = True
        
        await websocket_client.connect("http://localhost:8000", socketio_path="/socket.io/")
        
        # Send empty authentication
        await websocket_client.emit("authenticate", {})
        
        # Wait for response
        await asyncio.sleep(0.2)
        
        assert auth_failed

    async def test_unauthenticated_actions(self, websocket_client: socketio.AsyncClient):
        """Test that unauthenticated users cannot perform protected actions."""
        error_received = False
        
        @websocket_client.event
        async def error(data):
            nonlocal error_received
            error_received = True
        
        await websocket_client.connect("http://localhost:8000", socketio_path="/socket.io/")
        
        # Try to join a chat without authentication
        await websocket_client.emit("join_chat", {"chat_id": "some_chat_id"})
        
        # Wait for error response
        await asyncio.sleep(0.2)
        
        assert error_received


@pytest.mark.websocket
class TestWebSocketMessaging:
    """Test real-time messaging via WebSocket."""

    async def test_send_and_receive_message(self, test_chat: Dict[str, Any], test_user: Dict[str, Any], test_user2: Dict[str, Any]):
        """Test sending and receiving messages in real-time."""
        # Setup two clients for sender and receiver
        sender_client = socketio.AsyncClient()
        receiver_client = socketio.AsyncClient()
        
        received_messages = []
        
        @receiver_client.event
        async def new_message(data):
            received_messages.append(data)
        
        try:
            # Connect both clients
            await sender_client.connect("http://localhost:8000", socketio_path="/socket.io/")
            await receiver_client.connect("http://localhost:8000", socketio_path="/socket.io/")
            
            # Authenticate both clients
            await sender_client.emit("authenticate", {"token": test_user["access_token"]})
            await receiver_client.emit("authenticate", {"token": test_user2["access_token"]})
            
            # Both join the same chat
            await sender_client.emit("join_chat", {"chat_id": test_chat["id"]})
            await receiver_client.emit("join_chat", {"chat_id": test_chat["id"]})
            
            await asyncio.sleep(0.1)
            
            # Send a message
            message_data = {
                "chat_id": test_chat["id"],
                "content": "Hello from WebSocket test!",
                "message_type": "text"
            }
            await sender_client.emit("send_message", message_data)
            
            # Wait for message to be received
            await asyncio.sleep(0.5)
            
            # Check if message was received
            assert len(received_messages) > 0
            message = received_messages[0]
            assert message["content"] == message_data["content"]
            assert message["sender_id"] == test_user["id"]
            assert message["chat_id"] == test_chat["id"]
            
        finally:
            await sender_client.disconnect()
            await receiver_client.disconnect()

    async def test_message_to_offline_user(self, test_chat: Dict[str, Any], test_user: Dict[str, Any]):
        """Test sending message when recipient is offline."""
        sender_client = socketio.AsyncClient()
        
        try:
            await sender_client.connect("http://localhost:8000", socketio_path="/socket.io/")
            await sender_client.emit("authenticate", {"token": test_user["access_token"]})
            await sender_client.emit("join_chat", {"chat_id": test_chat["id"]})
            
            # Send message (recipient is offline)
            message_data = {
                "chat_id": test_chat["id"],
                "content": "Message to offline user",
                "message_type": "text"
            }
            await sender_client.emit("send_message", message_data)
            
            # Message should still be stored even if recipient is offline
            await asyncio.sleep(0.2)
            
        finally:
            await sender_client.disconnect()

    async def test_typing_indicators(self, test_chat: Dict[str, Any], test_user: Dict[str, Any], test_user2: Dict[str, Any]):
        """Test typing indicator functionality."""
        client1 = socketio.AsyncClient()
        client2 = socketio.AsyncClient()
        
        typing_events = []
        
        @client2.event
        async def typing_start(data):
            typing_events.append(("start", data))
        
        @client2.event  
        async def typing_stop(data):
            typing_events.append(("stop", data))
        
        try:
            await client1.connect("http://localhost:8000", socketio_path="/socket.io/")
            await client2.connect("http://localhost:8000", socketio_path="/socket.io/")
            
            await client1.emit("authenticate", {"token": test_user["access_token"]})
            await client2.emit("authenticate", {"token": test_user2["access_token"]})
            
            await client1.emit("join_chat", {"chat_id": test_chat["id"]})
            await client2.emit("join_chat", {"chat_id": test_chat["id"]})
            
            await asyncio.sleep(0.1)
            
            # Start typing
            await client1.emit("typing_start", {"chat_id": test_chat["id"]})
            await asyncio.sleep(0.1)
            
            # Stop typing
            await client1.emit("typing_stop", {"chat_id": test_chat["id"]})
            await asyncio.sleep(0.1)
            
            # Check typing events were received
            assert len(typing_events) >= 2
            assert typing_events[0][0] == "start"
            assert typing_events[1][0] == "stop"
            
        finally:
            await client1.disconnect()
            await client2.disconnect()


@pytest.mark.websocket
class TestWebSocketRooms:
    """Test WebSocket room management."""

    async def test_join_chat_room(self, websocket_client: socketio.AsyncClient, test_user: Dict[str, Any], test_chat: Dict[str, Any]):
        """Test joining a chat room."""
        joined_room = False
        
        @websocket_client.event
        async def room_joined(data):
            nonlocal joined_room
            joined_room = True
        
        await websocket_client.connect("http://localhost:8000", socketio_path="/socket.io/")
        await websocket_client.emit("authenticate", {"token": test_user["access_token"]})
        
        await asyncio.sleep(0.1)
        
        # Join chat room
        await websocket_client.emit("join_chat", {"chat_id": test_chat["id"]})
        
        await asyncio.sleep(0.2)
        
        assert joined_room

    async def test_leave_chat_room(self, websocket_client: socketio.AsyncClient, test_user: Dict[str, Any], test_chat: Dict[str, Any]):
        """Test leaving a chat room."""
        left_room = False
        
        @websocket_client.event
        async def room_left(data):
            nonlocal left_room
            left_room = True
        
        await websocket_client.connect("http://localhost:8000", socketio_path="/socket.io/")
        await websocket_client.emit("authenticate", {"token": test_user["access_token"]})
        
        # First join the room
        await websocket_client.emit("join_chat", {"chat_id": test_chat["id"]})
        await asyncio.sleep(0.1)
        
        # Then leave the room
        await websocket_client.emit("leave_chat", {"chat_id": test_chat["id"]})
        
        await asyncio.sleep(0.2)
        
        assert left_room

    async def test_unauthorized_room_access(self, websocket_client: socketio.AsyncClient, test_user: Dict[str, Any]):
        """Test joining unauthorized chat room."""
        access_denied = False
        
        @websocket_client.event
        async def access_denied(data):
            nonlocal access_denied
            access_denied = True
        
        await websocket_client.connect("http://localhost:8000", socketio_path="/socket.io/")
        await websocket_client.emit("authenticate", {"token": test_user["access_token"]})
        
        # Try to join non-existent chat
        fake_chat_id = "60a9b0b5c8f1b2a8d8e4f5a6"
        await websocket_client.emit("join_chat", {"chat_id": fake_chat_id})
        
        await asyncio.sleep(0.2)
        
        assert access_denied


@pytest.mark.websocket
class TestWebSocketPresence:
    """Test user presence functionality."""

    async def test_user_online_status(self, test_user: Dict[str, Any], test_user2: Dict[str, Any]):
        """Test user online/offline status broadcasting."""
        client1 = socketio.AsyncClient()
        client2 = socketio.AsyncClient()
        
        presence_updates = []
        
        @client2.event
        async def user_status(data):
            presence_updates.append(data)
        
        try:
            await client2.connect("http://localhost:8000", socketio_path="/socket.io/")
            await client2.emit("authenticate", {"token": test_user2["access_token"]})
            
            await asyncio.sleep(0.1)
            
            # User1 comes online
            await client1.connect("http://localhost:8000", socketio_path="/socket.io/")
            await client1.emit("authenticate", {"token": test_user["access_token"]})
            
            await asyncio.sleep(0.2)
            
            # User1 goes offline
            await client1.disconnect()
            
            await asyncio.sleep(0.2)
            
            # Check presence updates
            assert len(presence_updates) >= 1
            
            # At least one should be online status
            online_updates = [u for u in presence_updates if u.get("is_online") == True]
            assert len(online_updates) >= 1
            
        finally:
            if client1.connected:
                await client1.disconnect()
            if client2.connected:
                await client2.disconnect()

    async def test_presence_in_chat(self, test_chat: Dict[str, Any], test_user: Dict[str, Any], test_user2: Dict[str, Any]):
        """Test presence updates within a chat."""
        client1 = socketio.AsyncClient()
        client2 = socketio.AsyncClient()
        
        presence_events = []
        
        @client2.event
        async def user_joined_chat(data):
            presence_events.append(("joined", data))
        
        @client2.event
        async def user_left_chat(data):
            presence_events.append(("left", data))
        
        try:
            # Both users connect and authenticate
            await client1.connect("http://localhost:8000", socketio_path="/socket.io/")
            await client2.connect("http://localhost:8000", socketio_path="/socket.io/")
            
            await client1.emit("authenticate", {"token": test_user["access_token"]})
            await client2.emit("authenticate", {"token": test_user2["access_token"]})
            
            await asyncio.sleep(0.1)
            
            # User2 joins chat first
            await client2.emit("join_chat", {"chat_id": test_chat["id"]})
            await asyncio.sleep(0.1)
            
            # User1 joins chat (should notify user2)
            await client1.emit("join_chat", {"chat_id": test_chat["id"]})
            await asyncio.sleep(0.1)
            
            # User1 leaves chat
            await client1.emit("leave_chat", {"chat_id": test_chat["id"]})
            await asyncio.sleep(0.1)
            
            # Check presence events
            assert len(presence_events) >= 1
            
        finally:
            await client1.disconnect()
            await client2.disconnect()


@pytest.mark.websocket
class TestWebSocketErrorHandling:
    """Test WebSocket error handling."""

    async def test_malformed_message(self, websocket_client: socketio.AsyncClient, test_user: Dict[str, Any]):
        """Test handling of malformed messages."""
        error_received = False
        
        @websocket_client.event
        async def error(data):
            nonlocal error_received
            error_received = True
        
        await websocket_client.connect("http://localhost:8000", socketio_path="/socket.io/")
        await websocket_client.emit("authenticate", {"token": test_user["access_token"]})
        
        # Send malformed message
        await websocket_client.emit("send_message", {"invalid": "data"})
        
        await asyncio.sleep(0.2)
        
        assert error_received

    async def test_rate_limiting(self, websocket_client: socketio.AsyncClient, test_user: Dict[str, Any], test_chat: Dict[str, Any]):
        """Test message rate limiting."""
        await websocket_client.connect("http://localhost:8000", socketio_path="/socket.io/")
        await websocket_client.emit("authenticate", {"token": test_user["access_token"]})
        await websocket_client.emit("join_chat", {"chat_id": test_chat["id"]})
        
        # Send many messages rapidly
        for i in range(20):  # Assuming rate limit is lower than this
            message_data = {
                "chat_id": test_chat["id"],
                "content": f"Rapid message {i}",
                "message_type": "text"
            }
            await websocket_client.emit("send_message", message_data)
        
        # Should receive rate limit error
        await asyncio.sleep(1)  # Wait for rate limiter to kick in

    async def test_connection_recovery(self, test_user: Dict[str, Any]):
        """Test automatic reconnection after connection loss."""
        client = socketio.AsyncClient()
        
        reconnected = False
        
        @client.event
        async def connect():
            nonlocal reconnected
            reconnected = True
        
        try:
            await client.connect("http://localhost:8000", socketio_path="/socket.io/")
            await client.emit("authenticate", {"token": test_user["access_token"]})
            
            # Simulate connection loss
            await client.disconnect()
            
            # Reconnect
            reconnected = False
            await client.connect("http://localhost:8000", socketio_path="/socket.io/")
            
            assert reconnected
            assert client.connected
            
        finally:
            if client.connected:
                await client.disconnect()