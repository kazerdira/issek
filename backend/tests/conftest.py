# Simple test configuration for running basic tests
import os
import asyncio
import pytest
import pytest_asyncio
from typing import Dict, Any
from httpx import AsyncClient
import socketio
from faker import Faker

# Test configuration - simplified for independent testing
TEST_BASE_URL = "http://localhost:8000"

# Configure pytest for async testing
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture
async def client():
    """Create HTTP client for testing REST API endpoints."""
    async with AsyncClient(base_url=TEST_BASE_URL, timeout=30.0) as ac:
        yield ac

@pytest_asyncio.fixture
async def websocket_client():
    """Create WebSocket client for testing real-time functionality."""
    client = socketio.AsyncClient(logger=False, engineio_logger=False)
    yield client
    if client.connected:
        await client.disconnect()

# Test data factory for generating consistent test data
class TestDataFactory:
    """Factory for generating test data."""
    
    fake = Faker()
    
    @classmethod
    def create_user_data(cls) -> Dict[str, Any]:
        """Generate user registration data."""
        username = cls.fake.user_name() + str(cls.fake.random_number(digits=4))
        return {
            "username": username,
            "email": f"{username}@testmail.com",
            "password": "testpass123",
            "display_name": cls.fake.name()
        }
    
    @classmethod
    def create_chat_data(cls) -> Dict[str, Any]:
        """Generate chat creation data."""
        return {
            "name": f"Test Chat {cls.fake.random_number(digits=4)}",
            "description": cls.fake.text(max_nb_chars=100),
            "chat_type": "group",
            "is_public": cls.fake.boolean()
        }
    
    @classmethod
    def create_message_data(cls) -> Dict[str, Any]:
        """Generate message data."""
        return {
            "content": cls.fake.text(max_nb_chars=200),
            "message_type": "text"
        }
    
    @classmethod
    def random_username(cls) -> str:
        """Generate a random username."""
        return cls.fake.user_name() + str(cls.fake.random_number(digits=4))
    
    @classmethod
    def random_email(cls) -> str:
        """Generate a random email."""
        return cls.fake.email()

# Fixture for creating test users through API calls
@pytest.fixture
async def test_user(client: AsyncClient) -> Dict[str, Any]:
    """Create a test user and return user data with tokens."""
    user_data = TestDataFactory.create_user_data()
    
    # Register user
    response = await client.post("/api/auth/register", json=user_data)
    if response.status_code != 201:
        # If registration fails, try to login instead
        login_data = {
            "login": user_data["username"],
            "password": user_data["password"]
        }
        response = await client.post("/api/auth/login", json=login_data)
        if response.status_code != 200:
            pytest.fail(f"Failed to create or login test user: {response.text}")
    
    result = response.json()
    
    # Merge the original user data with the response
    user_data.update(result)
    return user_data

@pytest.fixture
async def test_user2(client: AsyncClient) -> Dict[str, Any]:
    """Create a second test user."""
    user_data = TestDataFactory.create_user_data()
    
    # Register user
    response = await client.post("/api/auth/register", json=user_data)
    if response.status_code != 201:
        # If registration fails, try to login instead
        login_data = {
            "login": user_data["username"], 
            "password": user_data["password"]
        }
        response = await client.post("/api/auth/login", json=login_data)
        if response.status_code != 200:
            pytest.fail(f"Failed to create or login second test user: {response.text}")
    
    result = response.json()
    
    # Merge the original user data with the response
    user_data.update(result)
    return user_data

@pytest.fixture
async def authenticated_client(client: AsyncClient, test_user: Dict[str, Any]) -> AsyncClient:
    """HTTP client with authentication headers."""
    client.headers.update({"Authorization": f"Bearer {test_user['access_token']}"})
    return client

@pytest.fixture
async def test_chat(client: AsyncClient, test_user: Dict[str, Any]) -> Dict[str, Any]:
    """Create a test chat."""
    chat_data = TestDataFactory.create_chat_data()
    headers = {"Authorization": f"Bearer {test_user['access_token']}"}
    
    response = await client.post("/api/chats", json=chat_data, headers=headers)
    if response.status_code != 201:
        pytest.fail(f"Failed to create test chat: {response.text}")
    
    chat = response.json()
    return chat


# Additional fixtures for test_main.py
faker = Faker()

@pytest_asyncio.fixture
async def authenticated_user(client):
    """Create authenticated user with proper data structure."""
    username = f"testuser_{faker.uuid4()[:8]}"
    phone = f"+1{faker.random_number(digits=10, fix_len=True)}"
    register_data = {
        "username": username,
        "display_name": faker.name(),
        "phone_number": phone,
        "password": "TestPassword123!@#"
    }
    response = await client.post("/api/auth/register", json=register_data)
    if response.status_code != 200:
        raise Exception(f"Failed to create test user: {response.text}")
    result = response.json()
    return {
        "user": result.get("user"),
        "access_token": result.get("access_token"),
        "refresh_token": result.get("refresh_token"),
        "username": username,
        "password": register_data["password"]
    }


@pytest_asyncio.fixture
async def two_users(client):
    """Create two users for interaction tests."""
    async def create_user():
        username = f"testuser_{faker.uuid4()[:8]}"
        phone = f"+1{faker.random_number(digits=10, fix_len=True)}"
        register_data = {
            "username": username,
            "display_name": faker.name(),
            "phone_number": phone,
            "password": "TestPassword123!@#"
        }
        response = await client.post("/api/auth/register", json=register_data)
        if response.status_code != 200:
            raise Exception(f"Failed to create test user: {response.text}")
        result = response.json()
        return {
            "user": result.get("user"),
            "access_token": result.get("access_token"),
            "refresh_token": result.get("refresh_token"),
            "username": username,
            "password": register_data["password"]
        }
    user1 = await create_user()
    user2 = await create_user()
    return user1, user2
