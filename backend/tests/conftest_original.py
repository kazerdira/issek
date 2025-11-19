# Test configuration and fixtures
import os
import asyncio
import pytest
from typing import AsyncGenerator, Dict, Any
from httpx import AsyncClient
import socketio
from faker import Faker
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

# Import your app components - will be imported dynamically in fixtures
# from server import app
# from database import Database
# from models import User, Chat, Message  
# from auth import create_access_token, create_refresh_token

# Test configuration
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "mongodb://localhost:27017/chatapp_test")
TEST_JWT_SECRET = "test-secret-key-for-testing-only"

fake = Faker()

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """Create a test database instance."""
    client = AsyncIOMotorClient(TEST_DATABASE_URL)
    db = client.get_default_database()
    
    # Clean up before tests
    await db.drop_collection("users")
    await db.drop_collection("chats") 
    await db.drop_collection("messages")
    await db.drop_collection("friend_requests")
    await db.drop_collection("blocks")
    
    yield db
    
    # Clean up after tests
    await db.drop_collection("users")
    await db.drop_collection("chats")
    await db.drop_collection("messages") 
    await db.drop_collection("friend_requests")
    await db.drop_collection("blocks")
    client.close()

@pytest.fixture
async def db(test_db: AsyncIOMotorDatabase) -> AsyncGenerator[Database, None]:
    """Create a Database instance with test database."""
    # Temporarily override the database connection
    original_db = Database._db
    Database._db = test_db
    
    db_instance = Database()
    await db_instance.create_indexes()
    
    yield db_instance
    
    # Clean up after each test
    await test_db.drop_collection("users")
    await test_db.drop_collection("chats")
    await test_db.drop_collection("messages")
    await test_db.drop_collection("friend_requests") 
    await test_db.drop_collection("blocks")
    
    # Restore original database
    Database._db = original_db

@pytest.fixture
async def client(db: Database) -> AsyncGenerator[AsyncClient, None]:
    """Create a test HTTP client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def test_user(db: Database) -> Dict[str, Any]:
    """Create a test user."""
    user_data = {
        "username": fake.user_name(),
        "email": fake.email(),
        "phone_number": fake.phone_number(),
        "display_name": fake.name(),
        "password": "testpass123"
    }
    
    user = await db.create_user(
        username=user_data["username"],
        email=user_data["email"], 
        phone_number=user_data["phone_number"],
        display_name=user_data["display_name"],
        password_hash="hashed_password"  # In real tests, use proper hashing
    )
    
    user_data["id"] = user["id"]
    user_data["access_token"] = create_access_token(user["id"])
    user_data["refresh_token"] = create_refresh_token(user["id"])
    
    return user_data

@pytest.fixture
async def test_user2(db: Database) -> Dict[str, Any]:
    """Create a second test user for interaction tests."""
    user_data = {
        "username": fake.user_name(), 
        "email": fake.email(),
        "phone_number": fake.phone_number(),
        "display_name": fake.name(),
        "password": "testpass123"
    }
    
    user = await db.create_user(
        username=user_data["username"],
        email=user_data["email"],
        phone_number=user_data["phone_number"], 
        display_name=user_data["display_name"],
        password_hash="hashed_password"
    )
    
    user_data["id"] = user["id"]
    user_data["access_token"] = create_access_token(user["id"])
    user_data["refresh_token"] = create_refresh_token(user["id"])
    
    return user_data

@pytest.fixture
async def test_chat(db: Database, test_user: Dict[str, Any], test_user2: Dict[str, Any]) -> Dict[str, Any]:
    """Create a test chat between two users."""
    chat = await db.create_chat(
        chat_type="direct",
        name="Test Chat",
        creator_id=test_user["id"],
        participant_ids=[test_user["id"], test_user2["id"]]
    )
    return chat

@pytest.fixture
async def authenticated_client(client: AsyncClient, test_user: Dict[str, Any]) -> AsyncClient:
    """Create an authenticated HTTP client."""
    client.headers.update({"Authorization": f"Bearer {test_user['access_token']}"})
    return client

@pytest.fixture
async def websocket_client() -> AsyncGenerator[socketio.AsyncClient, None]:
    """Create a WebSocket client for testing."""
    sio = socketio.AsyncClient()
    yield sio
    if sio.connected:
        await sio.disconnect()

class TestDataFactory:
    """Factory for creating test data."""
    
    @staticmethod
    def user_data(**kwargs) -> Dict[str, Any]:
        """Generate user data."""
        data = {
            "username": fake.user_name(),
            "email": fake.email(),
            "phone_number": fake.phone_number(),
            "display_name": fake.name(),
            "password": "testpass123"
        }
        data.update(kwargs)
        return data
    
    @staticmethod
    def chat_data(**kwargs) -> Dict[str, Any]:
        """Generate chat data.""" 
        data = {
            "chat_type": "group",
            "name": fake.text(max_nb_chars=50),
            "description": fake.text(max_nb_chars=200),
            "is_public": False
        }
        data.update(kwargs)
        return data
    
    @staticmethod
    def message_data(**kwargs) -> Dict[str, Any]:
        """Generate message data."""
        data = {
            "content": fake.text(max_nb_chars=300),
            "message_type": "text"
        }
        data.update(kwargs)
        return data

# Utility functions
def assert_user_structure(user: Dict[str, Any]):
    """Assert that user has correct structure."""
    required_fields = ["id", "username", "email", "display_name", "created_at"]
    for field in required_fields:
        assert field in user, f"User missing field: {field}"
    
    # Should not contain sensitive fields
    sensitive_fields = ["password", "password_hash"]
    for field in sensitive_fields:
        assert field not in user, f"User contains sensitive field: {field}"

def assert_chat_structure(chat: Dict[str, Any]):
    """Assert that chat has correct structure.""" 
    required_fields = ["id", "chat_type", "name", "created_at", "owner_id"]
    for field in required_fields:
        assert field in chat, f"Chat missing field: {field}"

def assert_message_structure(message: Dict[str, Any]):
    """Assert that message has correct structure."""
    required_fields = ["id", "chat_id", "sender_id", "content", "created_at"]
    for field in required_fields:
        assert field in message, f"Message missing field: {field}"