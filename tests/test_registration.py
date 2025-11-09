"""
Integration test for user registration/account creation.
Tests the actual registration endpoint with real database operations.
"""

import pytest
from httpx import AsyncClient
import uuid


@pytest.mark.asyncio
async def test_create_account_with_email_and_phone(test_client, real_test_db):
    """Test creating a new account with email and phone number"""
    # Generate unique credentials
    unique_id = str(uuid.uuid4())[:8]
    user_data = {
        "phone_number": f"+1555{unique_id}",
        "email": f"testuser_{unique_id}@example.com",
        "username": f"testuser_{unique_id}",
        "display_name": "Test User",
        "password": "SecurePassword123!",
        "bio": "Test account",
        "role": "regular"
    }
    
    # Register the user
    response = await test_client.post("/api/auth/register", json=user_data)
    
    # Assertions
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert "access_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"
    assert "user" in data
    
    # Verify user data
    user = data["user"]
    assert user["email"] == user_data["email"]
    assert user["phone_number"] == user_data["phone_number"]
    assert user["username"] == user_data["username"]
    assert user["display_name"] == user_data["display_name"]
    assert user["bio"] == user_data["bio"]
    assert user["role"] == user_data["role"]
    assert "id" in user
    assert "created_at" in user
    
    # Verify password is NOT returned
    assert "password" not in user
    assert "hashed_password" not in user


@pytest.mark.asyncio
async def test_create_account_duplicate_email(test_client, test_user, real_test_db):
    """Test that duplicate email registration fails"""
    unique_id = str(uuid.uuid4())[:8]
    user_data = {
        "phone_number": f"+1555{unique_id}",
        "email": test_user["user_dict"]["email"],  # Use existing user's email
        "username": f"different_{unique_id}",
        "display_name": "Another User",
        "password": "SecurePassword123!"
    }
    
    response = await test_client.post("/api/auth/register", json=user_data)
    
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_account_duplicate_phone(test_client, test_user, real_test_db):
    """Test that duplicate phone number registration fails"""
    unique_id = str(uuid.uuid4())[:8]
    user_data = {
        "phone_number": test_user["user_dict"]["phone_number"],  # Use existing user's phone
        "email": f"different_{unique_id}@example.com",
        "username": f"different_{unique_id}",
        "display_name": "Another User",
        "password": "SecurePassword123!"
    }
    
    response = await test_client.post("/api/auth/register", json=user_data)
    
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_account_duplicate_username(test_client, test_user, real_test_db):
    """Test that duplicate username registration fails"""
    unique_id = str(uuid.uuid4())[:8]
    user_data = {
        "phone_number": f"+1555{unique_id}",
        "email": f"different_{unique_id}@example.com",
        "username": test_user["user_dict"]["username"],  # Use existing user's username
        "display_name": "Another User",
        "password": "SecurePassword123!"
    }
    
    response = await test_client.post("/api/auth/register", json=user_data)
    
    assert response.status_code == 400
    assert "already" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_account_missing_required_fields(test_client, real_test_db):
    """Test that registration fails with missing required fields"""
    # Missing username
    user_data = {
        "email": "test@example.com",
        "password": "SecurePassword123!",
        "display_name": "Test User"
    }
    
    response = await test_client.post("/api/auth/register", json=user_data)
    
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_create_account_invalid_email(test_client, real_test_db):
    """Test that registration fails with invalid email format"""
    unique_id = str(uuid.uuid4())[:8]
    user_data = {
        "phone_number": f"+1555{unique_id}",
        "email": "not-a-valid-email",  # Invalid email
        "username": f"testuser_{unique_id}",
        "display_name": "Test User",
        "password": "SecurePassword123!"
    }
    
    response = await test_client.post("/api/auth/register", json=user_data)
    
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_create_account_then_login(test_client, real_test_db):
    """Test complete flow: create account and then login"""
    # Create account
    unique_id = str(uuid.uuid4())[:8]
    user_data = {
        "phone_number": f"+1555{unique_id}",
        "email": f"testuser_{unique_id}@example.com",
        "username": f"testuser_{unique_id}",
        "display_name": "Test User",
        "password": "SecurePassword123!"
    }
    
    register_response = await test_client.post("/api/auth/register", json=user_data)
    assert register_response.status_code == 200
    
    # Login with email
    login_data = {
        "email": user_data["email"],
        "password": user_data["password"]
    }
    
    login_response = await test_client.post("/api/auth/login", json=login_data)
    assert login_response.status_code == 200
    
    login_data_json = login_response.json()
    assert "access_token" in login_data_json
    assert login_data_json["user"]["email"] == user_data["email"]
    
    # Login with phone
    login_data_phone = {
        "phone_number": user_data["phone_number"],
        "password": user_data["password"]
    }
    
    login_response_phone = await test_client.post("/api/auth/login", json=login_data_phone)
    assert login_response_phone.status_code == 200


@pytest.mark.asyncio
async def test_create_account_with_minimal_data(test_client, real_test_db):
    """Test creating account with only required fields"""
    unique_id = str(uuid.uuid4())[:8]
    user_data = {
        "username": f"testuser_{unique_id}",
        "display_name": "Test User",
        "password": "SecurePassword123!"
    }
    
    response = await test_client.post("/api/auth/register", json=user_data)
    
    # Should succeed - email and phone are optional
    assert response.status_code == 200
    
    data = response.json()
    assert "access_token" in data
    assert data["user"]["username"] == user_data["username"]
