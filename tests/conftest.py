"""
Test configuration and fixtures for ChatApp test suite.
Provides common test setup, database fixtures, and utility functions.
"""

import pytest
import asyncio
import sys
import os
from unittest.mock import AsyncMock, MagicMock

# Add the parent directory and backend to Python path to import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_database():
    """Mock database for testing without actual MongoDB connection."""
    db = MagicMock()
    db.users = MagicMock()
    db.messages = MagicMock()
    db.chat_rooms = MagicMock()
    
    # Mock common database operations
    db.users.find_one = AsyncMock()
    db.users.insert_one = AsyncMock()
    db.users.update_one = AsyncMock()
    db.users.delete_one = AsyncMock()
    
    db.messages.find = AsyncMock()
    db.messages.insert_one = AsyncMock()
    db.messages.update_one = AsyncMock()
    
    db.chat_rooms.find = AsyncMock()
    db.chat_rooms.insert_one = AsyncMock()
    db.chat_rooms.update_one = AsyncMock()
    
    return db


# Legacy fixture - deprecated
# @pytest.fixture
# def auth_manager(mock_database):
#     """Create AuthManager instance with mocked database."""
#     auth = AuthManager()
#     auth.db = mock_database
#     return auth


@pytest.fixture
def test_user_data():
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "password": "testpassword123",
        "name": "Test User",
        "phone": "+1234567890"
    }


@pytest.fixture
def test_user_hashed():
    """Sample user with hashed password for testing."""
    return {
        "_id": "64a1b2c3d4e5f6789012345",
        "email": "test@example.com",
        "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBFkOD1.yzOnL6",  # "testpassword123"
        "name": "Test User",
        "phone": "+1234567890",
        "is_active": True,
        "created_at": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def alice_user():
    """Alice test user data."""
    return {
        "_id": "alice123",
        "email": "alice@example.com",
        "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBFkOD1.yzOnL6",
        "name": "Alice Johnson",
        "phone": "+1234567801",
        "is_active": True,
        "created_at": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def bob_user():
    """Bob test user data."""
    return {
        "_id": "bob456",
        "email": "bob@example.com",
        "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBFkOD1.yzOnL6",
        "name": "Bob Smith",
        "phone": "+1234567802",
        "is_active": True,
        "created_at": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def test_message():
    """Sample message data for testing."""
    return {
        "_id": "msg123",
        "sender_id": "alice123",
        "recipient_id": "bob456",
        "content": "Hello Bob!",
        "timestamp": "2024-01-01T12:00:00Z",
        "is_read": False
    }


@pytest.fixture
def test_chat_room():
    """Sample chat room data for testing."""
    return {
        "_id": "room123",
        "participants": ["alice123", "bob456"],
        "created_at": "2024-01-01T00:00:00Z",
        "last_message": {
            "content": "Hello Bob!",
            "sender_id": "alice123",
            "timestamp": "2024-01-01T12:00:00Z"
        }
    }


@pytest.fixture
def valid_jwt_token(auth_manager, alice_user):
    """Generate a valid JWT token for testing."""
    return auth_manager.create_jwt_token(alice_user["_id"])


@pytest.fixture
def expired_jwt_token():
    """Generate an expired JWT token for testing."""
    # This would be a token that's already expired
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZTEyMyIsImV4cCI6MTAwMDAwMDAwMH0.invalid"


@pytest.fixture
def invalid_jwt_token():
    """Generate an invalid JWT token for testing."""
    return "invalid.jwt.token"


class MockSocketIOClient:
    """Mock SocketIO client for testing."""
    
    def __init__(self):
        self.connected = False
        self.events = {}
        self.emitted_events = []
    
    async def connect(self, url, auth=None):
        self.connected = True
        self.auth = auth
    
    async def disconnect(self):
        self.connected = False
    
    async def emit(self, event, data=None):
        self.emitted_events.append({"event": event, "data": data})
    
    def on(self, event, handler):
        self.events[event] = handler
    
    def trigger_event(self, event, data=None):
        if event in self.events:
            return self.events[event](data)


@pytest.fixture
def mock_socketio_client():
    """Create a mock SocketIO client for testing."""
    return MockSocketIOClient()


# Test database utilities
class TestDatabase:
    """Test database utility class."""
    
    def __init__(self):
        self.users = []
        self.messages = []
        self.chat_rooms = []
    
    def add_user(self, user):
        """Add a user to test database."""
        self.users.append(user)
    
    def add_message(self, message):
        """Add a message to test database."""
        self.messages.append(message)
    
    def add_chat_room(self, room):
        """Add a chat room to test database."""
        self.chat_rooms.append(room)
    
    def find_user(self, query):
        """Find user by query."""
        for user in self.users:
            if all(user.get(k) == v for k, v in query.items()):
                return user
        return None
    
    def clear(self):
        """Clear all test data."""
        self.users.clear()
        self.messages.clear()
        self.chat_rooms.clear()


@pytest.fixture
def test_db():
    """Create test database instance."""
    db = TestDatabase()
    yield db
    db.clear()


# Test utilities
def assert_user_fields(user, expected_fields):
    """Assert that user contains expected fields."""
    for field, value in expected_fields.items():
        assert user.get(field) == value, f"Expected {field}={value}, got {user.get(field)}"


def assert_valid_jwt_structure(token):
    """Assert that token has valid JWT structure."""
    parts = token.split('.')
    assert len(parts) == 3, f"JWT should have 3 parts, got {len(parts)}"
    assert all(part for part in parts), "JWT parts should not be empty"


def assert_api_response(response, expected_status, expected_keys=None):
    """Assert API response structure."""
    assert response.status_code == expected_status
    if expected_keys:
        json_data = response.json()
        for key in expected_keys:
            assert key in json_data, f"Expected key '{key}' in response"


# ============= Additional test fixtures =============

# Set test environment variables
os.environ['DEV_MODE'] = 'true'
os.environ['SECRET_KEY'] = 'test-secret-key-for-testing-only'
os.environ['MONGO_URL'] = os.environ.get('MONGO_URL', 'mongodb://localhost:27017/')
os.environ['DB_NAME'] = 'chatapp_test'


@pytest.fixture
async def real_test_db():
    """Setup and teardown real test database for integration tests"""
    from backend.database import Database
    
    db = Database.get_db()
    
    # Clear test collections before test
    await db.users.delete_many({})
    await db.chats.delete_many({})
    await db.messages.delete_many({})
    await db.otps.delete_many({})
    
    yield db
    
    # Cleanup after tests
    await db.users.delete_many({})
    await db.chats.delete_many({})
    await db.messages.delete_many({})
    await db.otps.delete_many({})


@pytest.fixture
async def test_client():
    """Create async test client for API testing"""
    from httpx import AsyncClient
    from backend.server import app
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def test_user(real_test_db):
    """Create a test user and return user data with token"""
    from backend.auth import create_access_token, get_password_hash
    from backend.database import create_user
    from backend.utils import utc_now
    import uuid
    
    user_id = str(uuid.uuid4())
    user_dict = {
        'id': user_id,
        'username': 'testuser',
        'display_name': 'Test User',
        'email': 'test@example.com',
        'phone_number': '+1234567890',
        'hashed_password': get_password_hash('password123'),
        'created_at': utc_now(),
        'updated_at': utc_now(),
        'is_online': True,
        'contacts': [],
        'blocked_users': [],
        'role': 'regular'
    }
    
    await create_user(user_dict)
    token = create_access_token(data={"sub": user_id})
    
    return {
        'user_id': user_id,
        'token': token,
        'user_dict': user_dict
    }


@pytest.fixture
async def auth_headers(test_user):
    """Get auth headers with test token"""
    return {"Authorization": f"Bearer {test_user['token']}"}


@pytest.fixture
async def test_user_2(real_test_db):
    """Create a second test user and return user data with token"""
    from backend.auth import create_access_token, get_password_hash
    from backend.database import create_user
    from backend.utils import utc_now
    import uuid
    
    user_id = str(uuid.uuid4())
    user_dict = {
        'id': user_id,
        'username': 'testuser2',
        'display_name': 'Test User 2',
        'email': 'test2@example.com',
        'phone_number': '+1234567891',
        'hashed_password': get_password_hash('password123'),
        'created_at': utc_now(),
        'updated_at': utc_now(),
        'is_online': True,
        'contacts': [],
        'blocked_users': [],
        'role': 'regular'
    }
    
    await create_user(user_dict)
    token = create_access_token(data={"sub": user_id})
    
    return {
        'user_id': user_id,
        'token': token,
        'user_dict': user_dict
    }


@pytest.fixture
async def auth_headers_2(test_user_2):
    """Get auth headers for second test user"""
    return {"Authorization": f"Bearer {test_user_2['token']}"}