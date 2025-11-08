"""
Unit tests for API routes (server.py, routes_auth.py, routes_users.py, routes_chat.py).
Tests all REST API endpoints with various scenarios.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
import json

from backend.server import app


class TestAuthRoutes:
    """Test suite for authentication routes."""
    
    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_auth_manager(self):
        """Mock AuthManager for testing."""
        with patch('backend.routes_auth.auth_manager') as mock:
            yield mock
    
    def test_register_success(self, client, mock_auth_manager, test_user_data):
        """Test successful user registration."""
        # Mock successful registration
        mock_response = {
            "token": "fake_jwt_token",
            "user": {
                "_id": "user123",
                "email": test_user_data["email"],
                "name": test_user_data["name"],
                "phone": test_user_data["phone"]
            }
        }
        mock_auth_manager.register_user.return_value = mock_response
        
        response = client.post("/api/auth/register", json=test_user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == test_user_data["email"]
    
    def test_register_duplicate_email(self, client, mock_auth_manager, test_user_data):
        """Test registration with duplicate email."""
        # Mock duplicate email scenario
        mock_auth_manager.register_user.return_value = None
        
        response = client.post("/api/auth/register", json=test_user_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "already exists" in data["detail"].lower()
    
    def test_register_missing_fields(self, client, mock_auth_manager):
        """Test registration with missing required fields."""
        incomplete_data = {
            "email": "test@example.com",
            "password": "password123"
            # Missing name and phone
        }
        
        response = client.post("/api/auth/register", json=incomplete_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_register_invalid_email(self, client, mock_auth_manager):
        """Test registration with invalid email format."""
        invalid_data = {
            "email": "not_an_email",
            "password": "password123",
            "name": "Test User",
            "phone": "+1234567890"
        }
        
        response = client.post("/api/auth/register", json=invalid_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_login_success(self, client, mock_auth_manager):
        """Test successful login."""
        login_data = {
            "email": "test@example.com",
            "password": "password123"
        }
        
        mock_response = {
            "token": "fake_jwt_token",
            "user": {
                "_id": "user123",
                "email": login_data["email"],
                "name": "Test User",
                "phone": "+1234567890"
            }
        }
        mock_auth_manager.login_user.return_value = mock_response
        
        response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == login_data["email"]
    
    def test_login_invalid_credentials(self, client, mock_auth_manager):
        """Test login with invalid credentials."""
        login_data = {
            "email": "test@example.com",
            "password": "wrongpassword"
        }
        
        mock_auth_manager.login_user.return_value = None
        
        response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 401
        data = response.json()
        assert "invalid" in data["detail"].lower()
    
    def test_login_missing_fields(self, client, mock_auth_manager):
        """Test login with missing fields."""
        incomplete_data = {
            "email": "test@example.com"
            # Missing password
        }
        
        response = client.post("/api/auth/login", json=incomplete_data)
        
        assert response.status_code == 422


class TestUserRoutes:
    """Test suite for user-related routes."""
    
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
    def auth_headers(self, mock_auth_manager):
        """Create authorization headers for authenticated requests."""
        mock_auth_manager.verify_jwt_token.return_value = "user123"
        return {"Authorization": "Bearer fake_jwt_token"}
    
    def test_get_contacts_success(self, client, mock_auth_manager, auth_headers, alice_user, bob_user):
        """Test successful retrieval of contacts."""
        mock_auth_manager.get_all_users.return_value = [alice_user, bob_user]
        
        response = client.get("/api/users/contacts", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        
        emails = [user["email"] for user in data]
        assert alice_user["email"] in emails
        assert bob_user["email"] in emails
    
    def test_get_contacts_unauthorized(self, client, mock_auth_manager):
        """Test contacts retrieval without authentication."""
        response = client.get("/api/users/contacts")
        
        assert response.status_code == 401
    
    def test_get_contacts_invalid_token(self, client, mock_auth_manager):
        """Test contacts retrieval with invalid token."""
        mock_auth_manager.verify_jwt_token.return_value = None
        
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/users/contacts", headers=headers)
        
        assert response.status_code == 401
    
    def test_get_user_profile_success(self, client, mock_auth_manager, auth_headers, alice_user):
        """Test successful user profile retrieval."""
        mock_auth_manager.get_user_by_id.return_value = alice_user
        
        response = client.get("/api/users/profile", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == alice_user["email"]
        assert data["name"] == alice_user["name"]
        assert "password_hash" not in data
    
    def test_get_user_profile_not_found(self, client, mock_auth_manager, auth_headers):
        """Test user profile retrieval when user not found."""
        mock_auth_manager.get_user_by_id.return_value = None
        
        response = client.get("/api/users/profile", headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_update_user_profile_success(self, client, mock_auth_manager, auth_headers):
        """Test successful user profile update."""
        update_data = {
            "name": "Updated Name",
            "phone": "+0987654321"
        }
        
        with patch('backend.routes_users.database') as mock_db:
            mock_db.update_user.return_value = True
            mock_auth_manager.get_user_by_id.return_value = {
                "_id": "user123",
                "email": "test@example.com",
                "name": "Updated Name",
                "phone": "+0987654321"
            }
            
            response = client.put("/api/users/profile", headers=auth_headers, json=update_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == update_data["name"]
            assert data["phone"] == update_data["phone"]
    
    def test_update_user_profile_failure(self, client, mock_auth_manager, auth_headers):
        """Test user profile update failure."""
        update_data = {
            "name": "Updated Name"
        }
        
        with patch('backend.routes_users.database') as mock_db:
            mock_db.update_user.return_value = False
            
            response = client.put("/api/users/profile", headers=auth_headers, json=update_data)
            
            assert response.status_code == 500


class TestChatRoutes:
    """Test suite for chat-related routes."""
    
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
    def auth_headers(self, mock_auth_manager):
        """Create authorization headers for authenticated requests."""
        mock_auth_manager.verify_jwt_token.return_value = "user123"
        return {"Authorization": "Bearer fake_jwt_token"}
    
    def test_get_messages_success(self, client, mock_auth_manager, auth_headers, test_message):
        """Test successful message retrieval."""
        with patch('backend.routes_chat.database') as mock_db:
            mock_db.get_messages_between_users.return_value = [test_message]
            
            response = client.get("/api/chat/messages/bob456", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["content"] == test_message["content"]
    
    def test_get_messages_unauthorized(self, client):
        """Test message retrieval without authentication."""
        response = client.get("/api/chat/messages/bob456")
        
        assert response.status_code == 401
    
    def test_send_message_success(self, client, mock_auth_manager, auth_headers):
        """Test successful message sending."""
        message_data = {
            "recipient_id": "bob456",
            "content": "Hello Bob!"
        }
        
        with patch('backend.routes_chat.database') as mock_db:
            mock_db.create_message.return_value = "msg123"
            mock_db.get_chat_room_by_participants.return_value = None
            mock_db.create_chat_room.return_value = "room123"
            mock_db.update_chat_room_last_message.return_value = True
            
            response = client.post("/api/chat/messages", headers=auth_headers, json=message_data)
            
            assert response.status_code == 201
            data = response.json()
            assert "message_id" in data
            assert data["message_id"] == "msg123"
    
    def test_send_message_missing_content(self, client, mock_auth_manager, auth_headers):
        """Test sending message with missing content."""
        message_data = {
            "recipient_id": "bob456"
            # Missing content
        }
        
        response = client.post("/api/chat/messages", headers=auth_headers, json=message_data)
        
        assert response.status_code == 422
    
    def test_send_message_to_self(self, client, mock_auth_manager, auth_headers):
        """Test sending message to self."""
        message_data = {
            "recipient_id": "user123",  # Same as sender
            "content": "Hello myself!"
        }
        
        response = client.post("/api/chat/messages", headers=auth_headers, json=message_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "yourself" in data["detail"].lower()
    
    def test_mark_message_read_success(self, client, mock_auth_manager, auth_headers):
        """Test successful message read marking."""
        with patch('backend.routes_chat.database') as mock_db:
            mock_db.mark_message_as_read.return_value = True
            
            response = client.put("/api/chat/messages/msg123/read", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
    
    def test_mark_message_read_failure(self, client, mock_auth_manager, auth_headers):
        """Test message read marking failure."""
        with patch('backend.routes_chat.database') as mock_db:
            mock_db.mark_message_as_read.return_value = False
            
            response = client.put("/api/chat/messages/msg123/read", headers=auth_headers)
            
            assert response.status_code == 404


class TestServerConfiguration:
    """Test suite for server configuration and middleware."""
    
    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app."""
        return TestClient(app)
    
    def test_cors_headers(self, client):
        """Test CORS headers are properly set."""
        response = client.options("/api/auth/login", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST"
        })
        
        # Should allow CORS
        assert response.status_code in [200, 204]
    
    def test_health_check_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "ChatApp" in data["message"]
    
    def test_invalid_endpoint(self, client):
        """Test accessing invalid endpoint."""
        response = client.get("/api/nonexistent")
        
        assert response.status_code == 404


class TestAuthenticationMiddleware:
    """Test suite for authentication middleware and token validation."""
    
    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_auth_manager(self):
        """Mock AuthManager for testing."""
        with patch('backend.routes_users.auth_manager') as mock:
            yield mock
    
    def test_missing_authorization_header(self, client, mock_auth_manager):
        """Test request without authorization header."""
        response = client.get("/api/users/contacts")
        
        assert response.status_code == 401
        data = response.json()
        assert "authorization" in data["detail"].lower()
    
    def test_invalid_authorization_format(self, client, mock_auth_manager):
        """Test request with invalid authorization header format."""
        invalid_headers = [
            {"Authorization": "InvalidFormat token"},
            {"Authorization": "Bearer"},
            {"Authorization": "Bearer "},
            {"Authorization": "Token fake_token"},
        ]
        
        for headers in invalid_headers:
            response = client.get("/api/users/contacts", headers=headers)
            assert response.status_code == 401
    
    def test_expired_token(self, client, mock_auth_manager):
        """Test request with expired token."""
        mock_auth_manager.verify_jwt_token.return_value = None
        
        headers = {"Authorization": "Bearer expired_token"}
        response = client.get("/api/users/contacts", headers=headers)
        
        assert response.status_code == 401
    
    def test_valid_token(self, client, mock_auth_manager, alice_user):
        """Test request with valid token."""
        mock_auth_manager.verify_jwt_token.return_value = "user123"
        mock_auth_manager.get_all_users.return_value = [alice_user]
        
        headers = {"Authorization": "Bearer valid_token"}
        response = client.get("/api/users/contacts", headers=headers)
        
        assert response.status_code == 200


class TestErrorHandling:
    """Test suite for error handling across all routes."""
    
    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app."""
        return TestClient(app)
    
    def test_server_error_handling(self, client):
        """Test handling of internal server errors."""
        with patch('backend.routes_auth.auth_manager') as mock:
            mock.login_user.side_effect = Exception("Database connection failed")
            
            login_data = {
                "email": "test@example.com",
                "password": "password123"
            }
            
            response = client.post("/api/auth/login", json=login_data)
            
            # Should handle the error gracefully
            assert response.status_code == 500
    
    def test_validation_error_details(self, client):
        """Test that validation errors provide helpful details."""
        # Send invalid email format
        invalid_data = {
            "email": "not_an_email",
            "password": "short",  # Too short
            "name": "",  # Empty
            "phone": "invalid_phone"
        }
        
        response = client.post("/api/auth/register", json=invalid_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        # Should contain validation error details
        assert isinstance(data["detail"], list)