# pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --strict-markers
    --cov=backend
    --cov-report=html
    --cov-report=term-missing
    -p no:warnings

markers =
    asyncio: marks tests as async (deselect with '-m "not asyncio"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    slow: marks tests as slow running

# tests/conftest.py - Shared test fixtures
import pytest
import asyncio
from typing import Generator
from fastapi.testclient import TestClient
from httpx import AsyncClient
import os

# Set test environment
os.environ['DEV_MODE'] = 'true'
os.environ['SECRET_KEY'] = 'test-secret-key-for-testing-only'
os.environ['MONGO_URL'] = 'mongodb://localhost:27017/'
os.environ['DB_NAME'] = 'chatapp_test'

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def test_db():
    """Setup and teardown test database"""
    from database import Database
    db = Database.get_db()
    
    # Clear test collections
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
    """Create test client"""
    from server import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
def auth_headers(test_user_token):
    """Get auth headers with test token"""
    return {"Authorization": f"Bearer {test_user_token}"}

@pytest.fixture
async def test_user_token(test_db):
    """Create a test user and return auth token"""
    from auth import create_access_token, get_password_hash
    from database import create_user
    import uuid
    from utils import utc_now
    
    user_id = str(uuid.uuid4())
    user_dict = {
        'id': user_id,
        'username': 'testuser',
        'display_name': 'Test User',
        'email': 'test@example.com',
        'hashed_password': get_password_hash('password123'),
        'created_at': utc_now(),
        'updated_at': utc_now(),
        'is_online': True,
        'contacts': [],
        'blocked_users': []
    }
    
    await create_user(user_dict)
    token = create_access_token(data={"sub": user_id})
    
    return token

# requirements-test.txt
pytest==8.4.2
pytest-asyncio==0.25.2
pytest-cov==6.0.0
pytest-mock==3.14.0
httpx==0.28.1
faker==34.2.0
factory-boy==3.3.1
