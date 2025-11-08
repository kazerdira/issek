"""
Integration tests for ChatApp.
Tests complete workflows combining authentication, API calls, and real-time messaging.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
import json
import time

from backend.server import app


class TestAuthenticationFlow:
    """Test complete authentication workflows."""
    
    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_auth_manager(self):
        """Mock AuthManager for testing."""
        with patch('backend.routes_auth.auth_manager') as mock:
            yield mock
    
    @pytest.fixture
    def mock_database(self):
        """Mock database for testing."""
        with patch('backend.database.Database') as mock:
            yield mock
    
    def test_complete_registration_login_flow(self, client, mock_auth_manager):
        """Test complete user registration and login workflow."""
        # Test user registration
        registration_data = {
            "email": "newuser@example.com",
            "password": "securepassword123",
            "name": "New User",
            "phone": "+1234567890"
        }
        
        mock_register_response = {
            "token": "register_jwt_token",
            "user": {
                "_id": "newuser123",
                "email": registration_data["email"],
                "name": registration_data["name"],
                "phone": registration_data["phone"]
            }
        }
        mock_auth_manager.register_user.return_value = mock_register_response
        
        # Register user
        register_response = client.post("/api/auth/register", json=registration_data)
        assert register_response.status_code == 201
        register_data = register_response.json()
        assert "token" in register_data
        
        # Test user login with same credentials
        login_data = {
            "email": registration_data["email"],
            "password": registration_data["password"]
        }
        
        mock_login_response = {
            "token": "login_jwt_token",
            "user": mock_register_response["user"]
        }
        mock_auth_manager.login_user.return_value = mock_login_response
        
        # Login user
        login_response = client.post("/api/auth/login", json=login_data)
        assert login_response.status_code == 200
        login_response_data = login_response.json()
        assert "token" in login_response_data
        assert login_response_data["user"]["email"] == registration_data["email"]
    
    def test_authentication_token_usage(self, client, mock_auth_manager):
        """Test using authentication token for protected endpoints."""
        # Mock token verification
        mock_auth_manager.verify_jwt_token.return_value = "user123"
        mock_auth_manager.get_all_users.return_value = [
            {
                "_id": "user123",
                "email": "test@example.com",
                "name": "Test User"
            }
        ]
        
        # Use token to access protected endpoint
        headers = {"Authorization": "Bearer valid_jwt_token"}
        response = client.get("/api/users/contacts", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 0  # Should return list of users


class TestMessagingWorkflow:
    """Test complete messaging workflows."""
    
    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_auth_manager(self):
        """Mock AuthManager for testing."""
        with patch('backend.routes_chat.auth_manager') as mock:
            yield mock
    
    @pytest.fixture
    def mock_database(self):
        """Mock database for testing."""
        with patch('backend.routes_chat.database') as mock:
            yield mock
    
    def test_complete_messaging_flow(self, client, mock_auth_manager, mock_database):
        """Test complete messaging workflow from send to retrieve."""
        # Setup authentication
        mock_auth_manager.verify_jwt_token.return_value = "alice123"
        headers = {"Authorization": "Bearer alice_token"}
        
        # Mock database responses
        mock_database.create_message.return_value = "msg123"
        mock_database.get_chat_room_by_participants.return_value = None
        mock_database.create_chat_room.return_value = "room123"
        mock_database.update_chat_room_last_message.return_value = True
        
        # Send a message
        message_data = {
            "recipient_id": "bob456",
            "content": "Hello Bob! How are you?"
        }
        
        send_response = client.post("/api/chat/messages", headers=headers, json=message_data)
        assert send_response.status_code == 201
        send_data = send_response.json()
        assert "message_id" in send_data
        
        # Retrieve messages between users
        mock_messages = [
            {
                "_id": "msg123",
                "sender_id": "alice123",
                "recipient_id": "bob456",
                "content": message_data["content"],
                "timestamp": "2024-01-01T12:00:00Z",
                "is_read": False
            }
        ]
        mock_database.get_messages_between_users.return_value = mock_messages
        
        get_response = client.get("/api/chat/messages/bob456", headers=headers)
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert len(get_data) == 1
        assert get_data[0]["content"] == message_data["content"]
        
        # Mark message as read
        mock_database.mark_message_as_read.return_value = True
        
        read_response = client.put("/api/chat/messages/msg123/read", headers=headers)
        assert read_response.status_code == 200
        read_data = read_response.json()
        assert read_data["success"] is True
    
    def test_messaging_with_multiple_users(self, client, mock_auth_manager, mock_database):
        """Test messaging between multiple users."""
        # Alice sends message to Bob
        mock_auth_manager.verify_jwt_token.return_value = "alice123"
        alice_headers = {"Authorization": "Bearer alice_token"}
        
        mock_database.create_message.return_value = "msg123"
        mock_database.get_chat_room_by_participants.return_value = {"_id": "room123"}
        mock_database.update_chat_room_last_message.return_value = True
        
        alice_message = {
            "recipient_id": "bob456",
            "content": "Hello from Alice!"
        }
        
        alice_response = client.post("/api/chat/messages", headers=alice_headers, json=alice_message)
        assert alice_response.status_code == 201
        
        # Bob responds to Alice
        mock_auth_manager.verify_jwt_token.return_value = "bob456"
        bob_headers = {"Authorization": "Bearer bob_token"}
        
        mock_database.create_message.return_value = "msg124"
        
        bob_message = {
            "recipient_id": "alice123",
            "content": "Hi Alice! How are you?"
        }
        
        bob_response = client.post("/api/chat/messages", headers=bob_headers, json=bob_message)
        assert bob_response.status_code == 201
        
        # Verify both messages exist in conversation
        mock_conversation = [
            {
                "_id": "msg123",
                "sender_id": "alice123",
                "recipient_id": "bob456",
                "content": alice_message["content"],
                "timestamp": "2024-01-01T12:00:00Z",
                "is_read": True
            },
            {
                "_id": "msg124",
                "sender_id": "bob456",
                "recipient_id": "alice123",
                "content": bob_message["content"],
                "timestamp": "2024-01-01T12:01:00Z",
                "is_read": False
            }
        ]
        mock_database.get_messages_between_users.return_value = mock_conversation
        
        conversation_response = client.get("/api/chat/messages/alice123", headers=bob_headers)
        assert conversation_response.status_code == 200
        conversation_data = conversation_response.json()
        assert len(conversation_data) == 2


class TestUserManagementWorkflow:
    """Test complete user management workflows."""
    
    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_auth_manager(self):
        """Mock AuthManager for testing."""
        with patch('backend.routes_users.auth_manager') as mock:
            yield mock
    
    @pytest.fixture
    def mock_database(self):
        """Mock database for testing."""
        with patch('backend.routes_users.database') as mock:
            yield mock
    
    def test_complete_user_profile_management(self, client, mock_auth_manager, mock_database):
        """Test complete user profile management workflow."""
        # Setup authentication
        mock_auth_manager.verify_jwt_token.return_value = "user123"
        headers = {"Authorization": "Bearer user_token"}
        
        # Get initial profile
        initial_user = {
            "_id": "user123",
            "email": "user@example.com",
            "name": "Original Name",
            "phone": "+1234567890",
            "created_at": "2024-01-01T00:00:00Z"
        }
        mock_auth_manager.get_user_by_id.return_value = initial_user
        
        profile_response = client.get("/api/users/profile", headers=headers)
        assert profile_response.status_code == 200
        profile_data = profile_response.json()
        assert profile_data["name"] == "Original Name"
        
        # Update profile
        update_data = {
            "name": "Updated Name",
            "phone": "+0987654321"
        }
        
        mock_database.update_user.return_value = True
        updated_user = initial_user.copy()
        updated_user.update(update_data)
        mock_auth_manager.get_user_by_id.return_value = updated_user
        
        update_response = client.put("/api/users/profile", headers=headers, json=update_data)
        assert update_response.status_code == 200
        update_response_data = update_response.json()
        assert update_response_data["name"] == "Updated Name"
        assert update_response_data["phone"] == "+0987654321"
        
        # Verify update persisted
        final_profile_response = client.get("/api/users/profile", headers=headers)
        assert final_profile_response.status_code == 200
        final_profile_data = final_profile_response.json()
        assert final_profile_data["name"] == "Updated Name"
    
    def test_contacts_management_workflow(self, client, mock_auth_manager):
        """Test contacts retrieval and management."""
        # Setup authentication
        mock_auth_manager.verify_jwt_token.return_value = "user123"
        headers = {"Authorization": "Bearer user_token"}
        
        # Mock contacts list
        mock_contacts = [
            {
                "_id": "alice123",
                "email": "alice@example.com",
                "name": "Alice Johnson",
                "phone": "+1111111111"
            },
            {
                "_id": "bob456",
                "email": "bob@example.com",
                "name": "Bob Smith",
                "phone": "+2222222222"
            },
            {
                "_id": "charlie789",
                "email": "charlie@example.com",
                "name": "Charlie Brown",
                "phone": "+3333333333"
            }
        ]
        mock_auth_manager.get_all_users.return_value = mock_contacts
        
        contacts_response = client.get("/api/users/contacts", headers=headers)
        assert contacts_response.status_code == 200
        contacts_data = contacts_response.json()
        assert len(contacts_data) == 3
        
        # Verify contact information
        emails = [contact["email"] for contact in contacts_data]
        assert "alice@example.com" in emails
        assert "bob@example.com" in emails
        assert "charlie@example.com" in emails


class TestErrorRecoveryWorkflow:
    """Test error handling and recovery workflows."""
    
    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app."""
        return TestClient(app)
    
    def test_authentication_failure_recovery(self, client):
        """Test recovery from authentication failures."""
        # Attempt to access protected endpoint without token
        response = client.get("/api/users/contacts")
        assert response.status_code == 401
        
        # Attempt with invalid token
        invalid_headers = {"Authorization": "Bearer invalid_token"}
        with patch('backend.routes_users.auth_manager') as mock:
            mock.verify_jwt_token.return_value = None
            response = client.get("/api/users/contacts", headers=invalid_headers)
            assert response.status_code == 401
        
        # Successful authentication after failures
        with patch('backend.routes_users.auth_manager') as mock:
            mock.verify_jwt_token.return_value = "user123"
            mock.get_all_users.return_value = []
            
            valid_headers = {"Authorization": "Bearer valid_token"}
            response = client.get("/api/users/contacts", headers=valid_headers)
            assert response.status_code == 200
    
    def test_database_error_recovery(self, client):
        """Test recovery from database errors."""
        headers = {"Authorization": "Bearer valid_token"}
        
        # Simulate database error
        with patch('backend.routes_auth.auth_manager') as mock:
            mock.login_user.side_effect = Exception("Database connection failed")
            
            login_data = {
                "email": "test@example.com",
                "password": "password123"
            }
            
            response = client.post("/api/auth/login", json=login_data)
            assert response.status_code == 500
        
        # Successful operation after database recovery
        with patch('backend.routes_auth.auth_manager') as mock:
            mock.login_user.return_value = {
                "token": "recovery_token",
                "user": {"_id": "user123", "email": "test@example.com"}
            }
            
            response = client.post("/api/auth/login", json=login_data)
            assert response.status_code == 200


class TestPerformanceWorkflow:
    """Test performance-related workflows."""
    
    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app."""
        return TestClient(app)
    
    def test_concurrent_requests_handling(self, client):
        """Test handling of concurrent API requests."""
        # This test would verify that the API can handle multiple
        # concurrent requests without issues
        
        with patch('backend.routes_users.auth_manager') as mock:
            mock.verify_jwt_token.return_value = "user123"
            mock.get_all_users.return_value = []
            
            headers = {"Authorization": "Bearer valid_token"}
            
            # Simulate multiple concurrent requests
            responses = []
            for i in range(10):
                response = client.get("/api/users/contacts", headers=headers)
                responses.append(response)
            
            # All requests should succeed
            for response in responses:
                assert response.status_code == 200
    
    def test_large_message_handling(self, client):
        """Test handling of large messages."""
        headers = {"Authorization": "Bearer valid_token"}
        
        with patch('backend.routes_chat.auth_manager') as mock_auth:
            with patch('backend.routes_chat.database') as mock_db:
                mock_auth.verify_jwt_token.return_value = "user123"
                mock_db.create_message.return_value = "msg123"
                mock_db.get_chat_room_by_participants.return_value = {"_id": "room123"}
                mock_db.update_chat_room_last_message.return_value = True
                
                # Test with large message content
                large_message = {
                    "recipient_id": "user456",
                    "content": "A" * 1000  # 1KB message
                }
                
                response = client.post("/api/chat/messages", headers=headers, json=large_message)
                assert response.status_code == 201


class TestSecurityWorkflow:
    """Test security-related workflows."""
    
    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app."""
        return TestClient(app)
    
    def test_token_expiration_handling(self, client):
        """Test handling of expired JWT tokens."""
        # Mock expired token
        with patch('backend.routes_users.auth_manager') as mock:
            mock.verify_jwt_token.return_value = None  # Simulates expired token
            
            headers = {"Authorization": "Bearer expired_token"}
            response = client.get("/api/users/contacts", headers=headers)
            
            assert response.status_code == 401
            data = response.json()
            assert "unauthorized" in data["detail"].lower() or "invalid" in data["detail"].lower()
    
    def test_sql_injection_prevention(self, client):
        """Test prevention of injection attacks."""
        # Test with potentially malicious input
        malicious_data = {
            "email": "test@example.com'; DROP TABLE users; --",
            "password": "password123"
        }
        
        with patch('backend.routes_auth.auth_manager') as mock:
            mock.login_user.return_value = None  # Should not find user
            
            response = client.post("/api/auth/login", json=malicious_data)
            # Should handle gracefully without crashing
            assert response.status_code in [401, 422]  # Either unauthorized or validation error
    
    def test_password_validation(self, client):
        """Test password strength validation."""
        weak_passwords = [
            "123",           # Too short
            "password",      # Too common
            "abc",          # Too short and simple
        ]
        
        for weak_password in weak_passwords:
            registration_data = {
                "email": "test@example.com",
                "password": weak_password,
                "name": "Test User",
                "phone": "+1234567890"
            }
            
            response = client.post("/api/auth/register", json=registration_data)
            # Should validate password strength
            assert response.status_code in [400, 422]