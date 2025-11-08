"""
Unit tests for authentication module (auth.py).
Tests login, registration, JWT token generation/validation, and password hashing.
"""

import pytest
import bcrypt
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta

from backend.auth import AuthManager


class TestAuthManager:
    """Test suite for AuthManager class."""
    
    @pytest.mark.asyncio
    async def test_hash_password(self, auth_manager):
        """Test password hashing functionality."""
        password = "testpassword123"
        hashed = auth_manager.hash_password(password)
        
        # Test hash format
        assert hashed.startswith("$2b$"), "Hash should start with bcrypt identifier"
        assert len(hashed) == 60, f"Bcrypt hash should be 60 chars, got {len(hashed)}"
        
        # Test password verification
        assert bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        assert not bcrypt.checkpw("wrongpassword".encode('utf-8'), hashed.encode('utf-8'))
    
    @pytest.mark.asyncio
    async def test_verify_password_success(self, auth_manager):
        """Test successful password verification."""
        password = "testpassword123"
        hashed = auth_manager.hash_password(password)
        
        result = auth_manager.verify_password(password, hashed)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_verify_password_failure(self, auth_manager):
        """Test failed password verification."""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = auth_manager.hash_password(password)
        
        result = auth_manager.verify_password(wrong_password, hashed)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_create_jwt_token(self, auth_manager):
        """Test JWT token creation."""
        user_id = "test_user_123"
        token = auth_manager.create_jwt_token(user_id)
        
        # Test token structure
        assert isinstance(token, str)
        parts = token.split('.')
        assert len(parts) == 3, "JWT should have 3 parts (header.payload.signature)"
        
        # Test token validation
        decoded_user_id = auth_manager.verify_jwt_token(token)
        assert decoded_user_id == user_id
    
    @pytest.mark.asyncio
    async def test_verify_jwt_token_valid(self, auth_manager):
        """Test JWT token verification with valid token."""
        user_id = "test_user_123"
        token = auth_manager.create_jwt_token(user_id)
        
        result = auth_manager.verify_jwt_token(token)
        assert result == user_id
    
    @pytest.mark.asyncio
    async def test_verify_jwt_token_invalid_format(self, auth_manager):
        """Test JWT token verification with invalid format."""
        invalid_tokens = [
            "invalid.token",
            "invalid_token_format",
            "",
            "too.many.parts.here.invalid",
            None
        ]
        
        for token in invalid_tokens:
            result = auth_manager.verify_jwt_token(token)
            assert result is None, f"Invalid token {token} should return None"
    
    @pytest.mark.asyncio
    async def test_verify_jwt_token_expired(self, auth_manager):
        """Test JWT token verification with expired token."""
        # Create token with very short expiration
        with patch('backend.auth.datetime') as mock_datetime:
            # Set time to past for token creation
            past_time = datetime.utcnow() - timedelta(hours=2)
            mock_datetime.utcnow.return_value = past_time
            
            user_id = "test_user_123"
            expired_token = auth_manager.create_jwt_token(user_id, expires_in_hours=1)
        
        # Verify token (current time should make it expired)
        result = auth_manager.verify_jwt_token(expired_token)
        assert result is None, "Expired token should return None"
    
    @pytest.mark.asyncio
    async def test_register_user_success(self, auth_manager, mock_database, test_user_data):
        """Test successful user registration."""
        # Mock database to return no existing user
        mock_database.users.find_one.return_value = None
        mock_database.users.insert_one.return_value = AsyncMock(inserted_id="new_user_id")
        
        result = await auth_manager.register_user(
            test_user_data["email"],
            test_user_data["password"],
            test_user_data["name"],
            test_user_data["phone"]
        )
        
        assert result is not None
        assert "token" in result
        assert "user" in result
        
        # Verify database calls
        mock_database.users.find_one.assert_called_once()
        mock_database.users.insert_one.assert_called_once()
        
        # Verify user data structure
        user_data = result["user"]
        assert user_data["email"] == test_user_data["email"]
        assert user_data["name"] == test_user_data["name"]
        assert user_data["phone"] == test_user_data["phone"]
        assert "password_hash" not in user_data, "Password hash should not be in response"
    
    @pytest.mark.asyncio
    async def test_register_user_duplicate_email(self, auth_manager, mock_database, test_user_data, test_user_hashed):
        """Test user registration with duplicate email."""
        # Mock database to return existing user
        mock_database.users.find_one.return_value = test_user_hashed
        
        result = await auth_manager.register_user(
            test_user_data["email"],
            test_user_data["password"],
            test_user_data["name"],
            test_user_data["phone"]
        )
        
        assert result is None
        # Should not insert new user
        mock_database.users.insert_one.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_login_user_success(self, auth_manager, mock_database, test_user_hashed):
        """Test successful user login."""
        # Mock database to return user
        mock_database.users.find_one.return_value = test_user_hashed
        
        result = await auth_manager.login_user(
            test_user_hashed["email"],
            "testpassword123"  # Original password before hashing
        )
        
        assert result is not None
        assert "token" in result
        assert "user" in result
        
        # Verify token is valid
        token = result["token"]
        decoded_user_id = auth_manager.verify_jwt_token(token)
        assert decoded_user_id == test_user_hashed["_id"]
        
        # Verify user data
        user_data = result["user"]
        assert user_data["email"] == test_user_hashed["email"]
        assert "password_hash" not in user_data
    
    @pytest.mark.asyncio
    async def test_login_user_not_found(self, auth_manager, mock_database):
        """Test login with non-existent user."""
        # Mock database to return no user
        mock_database.users.find_one.return_value = None
        
        result = await auth_manager.login_user("nonexistent@example.com", "password")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_login_user_wrong_password(self, auth_manager, mock_database, test_user_hashed):
        """Test login with wrong password."""
        # Mock database to return user
        mock_database.users.find_one.return_value = test_user_hashed
        
        result = await auth_manager.login_user(
            test_user_hashed["email"],
            "wrongpassword"
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_login_user_inactive_account(self, auth_manager, mock_database, test_user_hashed):
        """Test login with inactive user account."""
        # Mock user as inactive
        inactive_user = test_user_hashed.copy()
        inactive_user["is_active"] = False
        mock_database.users.find_one.return_value = inactive_user
        
        result = await auth_manager.login_user(
            test_user_hashed["email"],
            "testpassword123"
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_success(self, auth_manager, mock_database, test_user_hashed):
        """Test successful user retrieval by ID."""
        mock_database.users.find_one.return_value = test_user_hashed
        
        result = await auth_manager.get_user_by_id(test_user_hashed["_id"])
        
        assert result is not None
        assert result["_id"] == test_user_hashed["_id"]
        assert result["email"] == test_user_hashed["email"]
        assert "password_hash" not in result, "Password hash should not be returned"
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, auth_manager, mock_database):
        """Test user retrieval with non-existent ID."""
        mock_database.users.find_one.return_value = None
        
        result = await auth_manager.get_user_by_id("nonexistent_id")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_all_users(self, auth_manager, mock_database, alice_user, bob_user):
        """Test retrieval of all users."""
        mock_users = [alice_user, bob_user]
        mock_database.users.find.return_value.to_list = AsyncMock(return_value=mock_users)
        
        result = await auth_manager.get_all_users()
        
        assert len(result) == 2
        for user in result:
            assert "password_hash" not in user, "Password hash should not be returned"
        
        # Verify email addresses
        emails = [user["email"] for user in result]
        assert alice_user["email"] in emails
        assert bob_user["email"] in emails


class TestAuthManagerValidation:
    """Test input validation for AuthManager methods."""
    
    @pytest.mark.asyncio
    async def test_register_user_empty_fields(self, auth_manager, mock_database):
        """Test registration with empty required fields."""
        test_cases = [
            ("", "password", "name", "phone"),  # empty email
            ("email@test.com", "", "name", "phone"),  # empty password
            ("email@test.com", "password", "", "phone"),  # empty name
            ("email@test.com", "password", "name", ""),  # empty phone
        ]
        
        for email, password, name, phone in test_cases:
            result = await auth_manager.register_user(email, password, name, phone)
            assert result is None, f"Should reject empty fields: {email}, {password}, {name}, {phone}"
    
    @pytest.mark.asyncio
    async def test_register_user_invalid_email(self, auth_manager, mock_database):
        """Test registration with invalid email formats."""
        invalid_emails = [
            "notanemail",
            "@domain.com",
            "user@",
            "user space@domain.com",
            "user..double@domain.com"
        ]
        
        for email in invalid_emails:
            result = await auth_manager.register_user(email, "password", "name", "phone")
            assert result is None, f"Should reject invalid email: {email}"
    
    @pytest.mark.asyncio
    async def test_login_user_empty_fields(self, auth_manager, mock_database):
        """Test login with empty fields."""
        test_cases = [
            ("", "password"),  # empty email
            ("email@test.com", ""),  # empty password
            ("", ""),  # both empty
        ]
        
        for email, password in test_cases:
            result = await auth_manager.login_user(email, password)
            assert result is None, f"Should reject empty fields: {email}, {password}"


class TestAuthManagerErrorHandling:
    """Test error handling in AuthManager methods."""
    
    @pytest.mark.asyncio
    async def test_database_error_handling(self, auth_manager, mock_database):
        """Test graceful handling of database errors."""
        # Mock database to raise exception
        mock_database.users.find_one.side_effect = Exception("Database connection error")
        
        result = await auth_manager.login_user("test@example.com", "password")
        assert result is None, "Should handle database errors gracefully"
    
    @pytest.mark.asyncio
    async def test_jwt_malformed_token(self, auth_manager):
        """Test handling of malformed JWT tokens."""
        malformed_tokens = [
            "header.payload",  # missing signature
            "header..signature",  # empty payload
            ".payload.signature",  # empty header
        ]
        
        for token in malformed_tokens:
            result = auth_manager.verify_jwt_token(token)
            assert result is None, f"Should reject malformed token: {token}"