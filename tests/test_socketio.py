"""
Enhanced Socket.IO tests with pytest integration.
Tests real-time messaging, authentication, room management, and error handling.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock
from socketio import AsyncClient
import sys
import os

# Add backend path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from backend.socket_manager import SocketIOManager


class TestSocketIOManager:
    """Test suite for Socket.IO manager functionality."""
    
    @pytest.fixture
    def socket_manager(self):
        """Create SocketIO manager instance for testing."""
        return SocketIOManager()
    
    @pytest.fixture
    def mock_auth_manager(self):
        """Mock authentication manager."""
        with patch('backend.socket_manager.auth_manager') as mock:
            yield mock
    
    @pytest.fixture
    def mock_database(self):
        """Mock database instance."""
        with patch('backend.socket_manager.database') as mock:
            yield mock
    
    @pytest.mark.asyncio
    async def test_authenticate_valid_token(self, socket_manager, mock_auth_manager):
        """Test successful Socket.IO authentication with valid token."""
        # Mock valid token verification
        mock_auth_manager.verify_jwt_token.return_value = "user123"
        mock_auth_manager.get_user_by_id.return_value = {
            "_id": "user123",
            "email": "test@example.com",
            "name": "Test User"
        }
        
        # Mock socket session
        mock_sid = "socket123"
        mock_environ = {"socket_sessions": {}}
        
        # Call authenticate method
        result = await socket_manager.authenticate(mock_sid, {"token": "valid_token"}, mock_environ)
        
        assert result is True
        mock_auth_manager.verify_jwt_token.assert_called_once_with("valid_token")
        mock_auth_manager.get_user_by_id.assert_called_once_with("user123")
    
    @pytest.mark.asyncio
    async def test_authenticate_invalid_token(self, socket_manager, mock_auth_manager):
        """Test Socket.IO authentication with invalid token."""
        # Mock invalid token verification
        mock_auth_manager.verify_jwt_token.return_value = None
        
        mock_sid = "socket123"
        mock_environ = {"socket_sessions": {}}
        
        result = await socket_manager.authenticate(mock_sid, {"token": "invalid_token"}, mock_environ)
        
        assert result is False
        mock_auth_manager.get_user_by_id.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_authenticate_missing_token(self, socket_manager, mock_auth_manager):
        """Test Socket.IO authentication without token."""
        mock_sid = "socket123"
        mock_environ = {"socket_sessions": {}}
        
        result = await socket_manager.authenticate(mock_sid, {}, mock_environ)
        
        assert result is False
        mock_auth_manager.verify_jwt_token.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, socket_manager, mock_auth_manager):
        """Test Socket.IO authentication when user not found in database."""
        mock_auth_manager.verify_jwt_token.return_value = "user123"
        mock_auth_manager.get_user_by_id.return_value = None
        
        mock_sid = "socket123"
        mock_environ = {"socket_sessions": {}}
        
        result = await socket_manager.authenticate(mock_sid, {"token": "valid_token"}, mock_environ)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_join_room_success(self, socket_manager, mock_auth_manager):
        """Test successful room joining."""
        # Setup authenticated session
        mock_sid = "socket123"
        mock_environ = {
            "socket_sessions": {
                mock_sid: {
                    "user_id": "user123",
                    "user": {"_id": "user123", "name": "Test User"}
                }
            }
        }
        
        # Mock socket.io server methods
        mock_sio = MagicMock()
        mock_sio.enter_room = AsyncMock()
        mock_sio.emit = AsyncMock()
        socket_manager.sio = mock_sio
        
        await socket_manager.join_room(mock_sid, {"room_id": "room123"}, mock_environ)
        
        # Verify room was joined and events were emitted
        mock_sio.enter_room.assert_called_once_with(mock_sid, "room123")
        assert mock_sio.emit.call_count == 2  # room_joined and user_joined_room events
    
    @pytest.mark.asyncio
    async def test_join_room_unauthenticated(self, socket_manager):
        """Test room joining without authentication."""
        mock_sid = "socket123"
        mock_environ = {"socket_sessions": {}}
        
        mock_sio = MagicMock()
        mock_sio.emit = AsyncMock()
        socket_manager.sio = mock_sio
        
        await socket_manager.join_room(mock_sid, {"room_id": "room123"}, mock_environ)
        
        # Should emit authentication error
        mock_sio.emit.assert_called_once_with(
            'authentication_error',
            {'message': 'Please authenticate first'},
            room=mock_sid
        )
    
    @pytest.mark.asyncio
    async def test_send_message_success(self, socket_manager, mock_database):
        """Test successful message sending."""
        # Setup authenticated session
        mock_sid = "socket123"
        mock_environ = {
            "socket_sessions": {
                mock_sid: {
                    "user_id": "user123",
                    "user": {"_id": "user123", "name": "Test User"}
                }
            }
        }
        
        # Mock database operations
        mock_database.create_message.return_value = "msg123"
        mock_database.get_chat_room_by_participants.return_value = {"_id": "room123"}
        mock_database.update_chat_room_last_message.return_value = True
        
        # Mock socket.io server methods
        mock_sio = MagicMock()
        mock_sio.emit = AsyncMock()
        socket_manager.sio = mock_sio
        
        message_data = {
            "room_id": "room123",
            "content": "Hello World!",
            "message_type": "text"
        }
        
        await socket_manager.send_message(mock_sid, message_data, mock_environ)
        
        # Verify message was created and emitted
        mock_database.create_message.assert_called_once()
        mock_sio.emit.assert_called_once_with('new_message', message_data, room="room123")
    
    @pytest.mark.asyncio
    async def test_send_message_unauthenticated(self, socket_manager):
        """Test message sending without authentication."""
        mock_sid = "socket123"
        mock_environ = {"socket_sessions": {}}
        
        mock_sio = MagicMock()
        mock_sio.emit = AsyncMock()
        socket_manager.sio = mock_sio
        
        await socket_manager.send_message(mock_sid, {"content": "Hello"}, mock_environ)
        
        # Should emit authentication error
        mock_sio.emit.assert_called_once_with(
            'authentication_error',
            {'message': 'Please authenticate first'},
            room=mock_sid
        )
    
    @pytest.mark.asyncio
    async def test_send_message_missing_content(self, socket_manager):
        """Test message sending without content."""
        mock_sid = "socket123"
        mock_environ = {
            "socket_sessions": {
                mock_sid: {
                    "user_id": "user123",
                    "user": {"_id": "user123", "name": "Test User"}
                }
            }
        }
        
        mock_sio = MagicMock()
        mock_sio.emit = AsyncMock()
        socket_manager.sio = mock_sio
        
        await socket_manager.send_message(mock_sid, {"room_id": "room123"}, mock_environ)
        
        # Should emit error for missing content
        mock_sio.emit.assert_called_once_with(
            'error',
            {'message': 'Message content is required'},
            room=mock_sid
        )
    
    @pytest.mark.asyncio
    async def test_disconnect_cleanup(self, socket_manager):
        """Test session cleanup on disconnect."""
        mock_sid = "socket123"
        mock_environ = {
            "socket_sessions": {
                mock_sid: {
                    "user_id": "user123",
                    "user": {"_id": "user123", "name": "Test User"}
                }
            }
        }
        
        await socket_manager.disconnect(mock_sid, mock_environ)
        
        # Session should be removed
        assert mock_sid not in mock_environ["socket_sessions"]


class TestSocketIOIntegration:
    """Integration tests for Socket.IO with real client connections."""
    
    @pytest.fixture
    def mock_server(self):
        """Mock Socket.IO server for integration testing."""
        return MagicMock()
    
    @pytest.mark.asyncio
    async def test_client_connection_flow(self, mock_server):
        """Test complete client connection flow."""
        # This would test the actual connection flow
        # In a real environment, you'd start the actual server
        pass
    
    @pytest.mark.asyncio
    async def test_multiple_clients_messaging(self, mock_server):
        """Test messaging between multiple clients."""
        # This would test real-time messaging between clients
        pass


class TestSocketIOErrorHandling:
    """Test error handling in Socket.IO operations."""
    
    @pytest.fixture
    def socket_manager(self):
        """Create SocketIO manager instance for testing."""
        return SocketIOManager()
    
    @pytest.mark.asyncio
    async def test_database_error_handling(self, socket_manager, mock_database):
        """Test handling of database errors during message operations."""
        mock_sid = "socket123"
        mock_environ = {
            "socket_sessions": {
                mock_sid: {
                    "user_id": "user123",
                    "user": {"_id": "user123", "name": "Test User"}
                }
            }
        }
        
        # Mock database error
        mock_database.create_message.side_effect = Exception("Database error")
        
        mock_sio = MagicMock()
        mock_sio.emit = AsyncMock()
        socket_manager.sio = mock_sio
        
        message_data = {
            "room_id": "room123",
            "content": "Hello World!",
            "message_type": "text"
        }
        
        await socket_manager.send_message(mock_sid, message_data, mock_environ)
        
        # Should emit error message
        mock_sio.emit.assert_called_once_with(
            'error',
            {'message': 'Failed to send message'},
            room=mock_sid
        )
    
    @pytest.mark.asyncio
    async def test_invalid_room_id(self, socket_manager):
        """Test handling of invalid room ID."""
        mock_sid = "socket123"
        mock_environ = {
            "socket_sessions": {
                mock_sid: {
                    "user_id": "user123",
                    "user": {"_id": "user123", "name": "Test User"}
                }
            }
        }
        
        mock_sio = MagicMock()
        mock_sio.emit = AsyncMock()
        socket_manager.sio = mock_sio
        
        # Test with None room_id
        await socket_manager.join_room(mock_sid, {"room_id": None}, mock_environ)
        
        mock_sio.emit.assert_called_once_with(
            'error',
            {'message': 'Invalid room ID'},
            room=mock_sid
        )
    
    @pytest.mark.asyncio
    async def test_malformed_data_handling(self, socket_manager):
        """Test handling of malformed data."""
        mock_sid = "socket123"
        mock_environ = {
            "socket_sessions": {
                mock_sid: {
                    "user_id": "user123",
                    "user": {"_id": "user123", "name": "Test User"}
                }
            }
        }
        
        mock_sio = MagicMock()
        mock_sio.emit = AsyncMock()
        socket_manager.sio = mock_sio
        
        # Test with malformed message data
        await socket_manager.send_message(mock_sid, "not_a_dict", mock_environ)
        
        # Should handle gracefully and emit error
        mock_sio.emit.assert_called_once()


# Keep the original integration tester for manual testing
class SocketIOTester:
    """Manual testing helper for Socket.IO integration tests."""
    
    def __init__(self, server_url="http://localhost:8001"):
        self.server_url = server_url
        self.clients = {}
        self.received_messages = {}
        
    async def create_client(self, user_name, token):
        """Create and connect a Socket.IO client"""
        client = AsyncClient(logger=False, engineio_logger=False)
        
        @client.event
        async def connect():
            print(f"✅ {user_name} connected to Socket.IO server")
            await client.emit('authenticate', {'token': token})
        
        @client.event
        async def connect_error(data):
            print(f"❌ {user_name} connection error: {data}")
        
        @client.event
        async def disconnect():
            print(f"🔌 {user_name} disconnected from Socket.IO server")
        
        @client.event
        async def authenticated(data):
            print(f"🔐 {user_name} authenticated successfully: {data}")
        
        @client.event
        async def authentication_error(data):
            print(f"❌ {user_name} authentication error: {data}")
        
        @client.event
        async def room_joined(data):
            print(f"🏠 {user_name} joined room: {data.get('room_id')}")
        
        @client.event
        async def new_message(data):
            print(f"📨 {user_name} received message: {data}")
            if user_name not in self.received_messages:
                self.received_messages[user_name] = []
            self.received_messages[user_name].append(data)
        
        @client.event
        async def user_joined_room(data):
            print(f"👥 {user_name} sees user joined room: {data}")
        
        @client.event
        async def user_left_room(data):
            print(f"👋 {user_name} sees user left room: {data}")
        
        # Connect to server
        await client.connect(self.server_url)
        self.clients[user_name] = client
        return client
    
    async def join_room(self, user_name, room_id):
        """Join a chat room"""
        client = self.clients.get(user_name)
        if client:
            await client.emit('join_room', {'room_id': room_id})
            print(f"🔄 {user_name} attempting to join room: {room_id}")
    
    async def send_message(self, user_name, room_id, message):
        """Send a message to a room"""
        client = self.clients.get(user_name)
        if client:
            await client.emit('send_message', {
                'room_id': room_id,
                'content': message,
                'message_type': 'text'
            })
            print(f"📤 {user_name} sent message: '{message}' to room {room_id}")
    
    async def disconnect_all(self):
        """Disconnect all clients"""
        for user_name, client in self.clients.items():
            await client.disconnect()
            print(f"🔌 {user_name} disconnected")


# Manual testing functions for integration testing
async def manual_test_socketio_messaging():
    """Manual test for Socket.IO real-time messaging functionality"""
    print("🚀 Starting Socket.IO messaging tests...\n")
    
    # Test tokens (these would come from login API calls)
    alice_token = "test_token_alice"
    bob_token = "test_token_bob"
    
    tester = SocketIOTester()
    
    try:
        print("1️⃣ Testing Alice connection and authentication...")
        alice_client = await tester.create_client("Alice", alice_token)
        await asyncio.sleep(2)
        
        print("\n2️⃣ Testing room joining...")
        test_room_id = "test_room_123"
        await tester.join_room("Alice", test_room_id)
        await asyncio.sleep(2)
        
        print("\n3️⃣ Testing message sending...")
        await tester.send_message("Alice", test_room_id, "Hello from Alice! 👋")
        await asyncio.sleep(2)
        
        print("\n Test Results:")
        print(f"- Alice received {len(tester.received_messages.get('Alice', []))} messages")
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n🔚 Cleaning up...")
        await tester.disconnect_all()
    
    print("✅ Socket.IO tests completed!")


if __name__ == "__main__":
    # Run manual tests if executed directly
    asyncio.run(manual_test_socketio_messaging())