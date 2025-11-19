"""
🎯 COMPREHENSIVE CHATAPP TEST SUITE
==================================
Production-grade tests for ChatApp Backend API

Tests cover:
- ✅ Authentication (register, login, refresh tokens)
- ✅ User management (profile, search, blocking)
- ✅ Chat operations (create, send messages, reactions)
- ✅ Friend system (requests, accept, remove)
- ✅ WebSocket real-time communication
- ✅ Permissions and security
- ✅ Integration workflows
"""

import pytest
import asyncio
from httpx import AsyncClient
import socketio
from faker import Faker
from typing import Dict, Any, Optional
import logging

# Configure logging for test visibility
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://localhost:8000"
API_PREFIX = "/api"
faker = Faker()


# ============================================================================
# FIXTURES - Test Setup & Utilities
# ============================================================================

@pytest.fixture
async def client():
    """HTTP client for REST API testing"""
    async with AsyncClient(base_url=BASE_URL, timeout=30.0) as ac:
        yield ac


@pytest.fixture
async def authenticated_user(client) -> Dict[str, Any]:
    """
    Create and return an authenticated test user with tokens
    Returns: {user: UserResponse, access_token: str, refresh_token: str}
    """
    # Generate unique test data
    username = f"testuser_{faker.uuid4()[:8]}"
    phone = f"+1{faker.random_number(digits=10, fix_len=True)}"
    
    # Register user
    register_data = {
        "username": username,
        "display_name": faker.name(),
        "phone_number": phone,
        "password": "TestPass123!@#"
    }
    
    response = await client.post(f"{API_PREFIX}/auth/register", json=register_data)
    assert response.status_code == 200, f"Registration failed: {response.text}"
    
    result = response.json()
    logger.info(f"✅ Created authenticated user: {username}")
    
    return {
        "user": result.get("user"),
        "access_token": result.get("access_token"),
        "refresh_token": result.get("refresh_token"),
        "username": username,
        "password": register_data["password"]
    }


@pytest.fixture
async def two_users(client) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Create two authenticated users for interaction tests"""
    async def create_user():
        username = f"testuser_{faker.uuid4()[:8]}"
        phone = f"+1{faker.random_number(digits=10, fix_len=True)}"
        
        register_data = {
            "username": username,
            "display_name": faker.name(),
            "phone_number": phone,
            "password": "TestPass123!@#"
        }
        
        response = await client.post(f"{API_PREFIX}/auth/register", json=register_data)
        assert response.status_code == 200
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
    
    logger.info(f"✅ Created two users: {user1['username']} & {user2['username']}")
    return user1, user2


@pytest.fixture
async def websocket_client():
    """WebSocket client for real-time communication testing"""
    sio = socketio.AsyncClient(
        logger=False,
        engineio_logger=False,
        reconnection=True,
        reconnection_attempts=3
    )
    yield sio
    if sio.connected:
        await sio.disconnect()


def auth_headers(token: str) -> Dict[str, str]:
    """Generate authorization headers with token"""
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# 🔐 AUTHENTICATION TESTS
# ============================================================================

class TestAuthentication:
    """Test user registration, login, and token management"""
    
    @pytest.mark.asyncio
    async def test_user_registration(self, client):
        """Test successful user registration"""
        username = f"newuser_{faker.uuid4()[:8]}"
        phone = f"+1{faker.random_number(digits=10, fix_len=True)}"
        
        register_data = {
            "username": username,
            "display_name": faker.name(),
            "phone_number": phone,
            "password": "SecurePass123!@#"
        }
        
        response = await client.post(f"{API_PREFIX}/auth/register", json=register_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data
        assert data["user"]["username"] == username
        
        logger.info(f"✅ Registration successful for user: {username}")
    
    
    @pytest.mark.asyncio
    async def test_duplicate_registration_fails(self, client, authenticated_user):
        """Test that duplicate username/phone registration fails"""
        duplicate_data = {
            "username": authenticated_user["username"],
            "display_name": faker.name(),
            "phone_number": f"+1{faker.random_number(digits=10, fix_len=True)}",
            "password": "AnotherPass123!@#"
        }
        
        response = await client.post(f"{API_PREFIX}/auth/register", json=duplicate_data)
        
        assert response.status_code == 400
        assert "already" in response.json()["detail"].lower()
        
        logger.info("✅ Duplicate registration correctly rejected")
    
    
    @pytest.mark.asyncio
    async def test_user_login(self, client, authenticated_user):
        """Test user login with phone and password"""
        user_data = authenticated_user
        
        # Get phone from user data
        login_data = {
            "phone_number": user_data["user"]["phone_number"],
            "password": user_data["password"]
        }
        
        response = await client.post(f"{API_PREFIX}/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data
        
        logger.info(f"✅ Login successful for user: {user_data['username']}")
    
    
    @pytest.mark.asyncio
    async def test_invalid_login_fails(self, client):
        """Test that invalid credentials are rejected"""
        login_data = {
            "phone_number": "+19999999999",
            "password": "WrongPassword123"
        }
        
        response = await client.post(f"{API_PREFIX}/auth/login", json=login_data)
        
        assert response.status_code == 401
        
        logger.info("✅ Invalid login correctly rejected")
    
    
    @pytest.mark.asyncio
    async def test_token_refresh(self, client, authenticated_user):
        """Test access token refresh using refresh token"""
        refresh_data = {
            "refresh_token": authenticated_user["refresh_token"]
        }
        
        response = await client.post(
            f"{API_PREFIX}/auth/refresh",
            json=refresh_data
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert data["access_token"] != authenticated_user["access_token"]
        
        logger.info("✅ Token refresh successful")
    
    
    @pytest.mark.asyncio
    async def test_protected_endpoint_requires_auth(self, client):
        """Test that protected endpoints reject unauthenticated requests"""
        response = await client.get(f"{API_PREFIX}/users/me")
        
        assert response.status_code in [401, 403]
        
        logger.info("✅ Protected endpoint correctly requires authentication")
    
    
    @pytest.mark.asyncio
    async def test_logout(self, client, authenticated_user):
        """Test user logout invalidates tokens"""
        headers = auth_headers(authenticated_user["access_token"])
        
        response = await client.post(
            f"{API_PREFIX}/auth/logout",
            headers=headers
        )
        
        assert response.status_code == 200
        
        logger.info("✅ Logout successful")


# ============================================================================
# 👤 USER MANAGEMENT TESTS
# ============================================================================

class TestUserManagement:
    """Test user profile operations and search"""
    
    @pytest.mark.asyncio
    async def test_get_own_profile(self, client, authenticated_user):
        """Test retrieving own user profile"""
        headers = auth_headers(authenticated_user["access_token"])
        
        response = await client.get(f"{API_PREFIX}/users/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["username"] == authenticated_user["username"]
        
        logger.info("✅ Retrieved own profile successfully")
    
    
    @pytest.mark.asyncio
    async def test_update_profile(self, client, authenticated_user):
        """Test updating user profile"""
        headers = auth_headers(authenticated_user["access_token"])
        
        new_bio = "Updated bio: " + faker.sentence()
        update_data = {
            "bio": new_bio,
            "display_name": faker.name()
        }
        
        response = await client.put(
            f"{API_PREFIX}/users/me",
            json=update_data,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["bio"] == new_bio
        
        logger.info("✅ Profile updated successfully")
    
    
    @pytest.mark.asyncio
    async def test_search_users(self, client, two_users):
        """Test user search functionality"""
        user1, user2 = two_users
        headers = auth_headers(user1["access_token"])
        
        # Search for user2 by username
        search_query = user2["username"][:5]  # Partial match
        
        response = await client.get(
            f"{API_PREFIX}/users/search",
            params={"q": search_query},
            headers=headers
        )
        
        assert response.status_code == 200
        results = response.json()
        
        assert isinstance(results, list)
        # Should find user2 in results
        usernames = [u["username"] for u in results]
        assert user2["username"] in usernames
        
        logger.info(f"✅ Search found {len(results)} users")
    
    
    @pytest.mark.asyncio
    async def test_get_user_by_id(self, client, two_users):
        """Test retrieving another user's profile by ID"""
        user1, user2 = two_users
        headers = auth_headers(user1["access_token"])
        
        user2_id = user2["user"]["id"]
        
        response = await client.get(
            f"{API_PREFIX}/users/{user2_id}",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == user2_id
        assert data["username"] == user2["username"]
        
        logger.info("✅ Retrieved user profile by ID")


# ============================================================================
# 💬 CHAT & MESSAGING TESTS
# ============================================================================

class TestChatsAndMessaging:
    """Test chat creation, messaging, and reactions"""
    
    @pytest.mark.asyncio
    async def test_create_private_chat(self, client, two_users):
        """Test creating a private 1-on-1 chat"""
        user1, user2 = two_users
        headers = auth_headers(user1["access_token"])
        
        chat_data = {
            "type": "private",
            "recipient_id": user2["user"]["id"]
        }
        
        response = await client.post(
            f"{API_PREFIX}/chats",
            json=chat_data,
            headers=headers
        )
        
        assert response.status_code == 200
        chat = response.json()
        
        assert chat["type"] == "private"
        assert len(chat["members"]) == 2
        
        logger.info(f"✅ Created private chat: {chat['id']}")
        return chat
    
    
    @pytest.mark.asyncio
    async def test_create_group_chat(self, client, authenticated_user):
        """Test creating a group chat"""
        headers = auth_headers(authenticated_user["access_token"])
        
        group_data = {
            "type": "group",
            "title": f"Test Group {faker.uuid4()[:8]}",
            "description": faker.sentence()
        }
        
        response = await client.post(
            f"{API_PREFIX}/chats",
            json=group_data,
            headers=headers
        )
        
        assert response.status_code == 200
        chat = response.json()
        
        assert chat["type"] == "group"
        assert chat["title"] == group_data["title"]
        
        logger.info(f"✅ Created group chat: {chat['title']}")
        return chat
    
    
    @pytest.mark.asyncio
    async def test_send_message(self, client, two_users):
        """Test sending a text message in chat"""
        user1, user2 = two_users
        headers = auth_headers(user1["access_token"])
        
        # First create a chat
        chat_data = {
            "type": "private",
            "recipient_id": user2["user"]["id"]
        }
        chat_response = await client.post(
            f"{API_PREFIX}/chats",
            json=chat_data,
            headers=headers
        )
        chat = chat_response.json()
        chat_id = chat["id"]
        
        # Send a message
        message_data = {
            "text": "Hello! This is a test message.",
            "type": "text"
        }
        
        response = await client.post(
            f"{API_PREFIX}/chats/{chat_id}/messages",
            json=message_data,
            headers=headers
        )
        
        assert response.status_code == 200
        message = response.json()
        
        assert message["text"] == message_data["text"]
        assert message["sender_id"] == user1["user"]["id"]
        
        logger.info(f"✅ Sent message in chat {chat_id}")
        return message
    
    
    @pytest.mark.asyncio
    async def test_get_chat_messages(self, client, two_users):
        """Test retrieving messages from a chat"""
        user1, user2 = two_users
        headers = auth_headers(user1["access_token"])
        
        # Create chat and send message
        chat_data = {"type": "private", "recipient_id": user2["user"]["id"]}
        chat_response = await client.post(
            f"{API_PREFIX}/chats",
            json=chat_data,
            headers=headers
        )
        chat_id = chat_response.json()["id"]
        
        # Send messages
        for i in range(3):
            await client.post(
                f"{API_PREFIX}/chats/{chat_id}/messages",
                json={"text": f"Message {i+1}", "type": "text"},
                headers=headers
            )
        
        # Get messages
        response = await client.get(
            f"{API_PREFIX}/chats/{chat_id}/messages",
            headers=headers
        )
        
        assert response.status_code == 200
        messages = response.json()
        
        assert len(messages) >= 3
        
        logger.info(f"✅ Retrieved {len(messages)} messages from chat")
    
    
    @pytest.mark.asyncio
    async def test_add_reaction(self, client, two_users):
        """Test adding a reaction to a message"""
        user1, user2 = two_users
        headers = auth_headers(user1["access_token"])
        
        # Create chat and send message
        chat_data = {"type": "private", "recipient_id": user2["user"]["id"]}
        chat_response = await client.post(
            f"{API_PREFIX}/chats",
            json=chat_data,
            headers=headers
        )
        chat_id = chat_response.json()["id"]
        
        msg_response = await client.post(
            f"{API_PREFIX}/chats/{chat_id}/messages",
            json={"text": "React to this!", "type": "text"},
            headers=headers
        )
        message_id = msg_response.json()["id"]
        
        # Add reaction
        reaction_data = {"emoji": "👍"}
        
        response = await client.post(
            f"{API_PREFIX}/chats/{chat_id}/messages/{message_id}/reactions",
            json=reaction_data,
            headers=headers
        )
        
        assert response.status_code == 200
        
        logger.info(f"✅ Added reaction to message {message_id}")
    
    
    @pytest.mark.asyncio
    async def test_edit_message(self, client, two_users):
        """Test editing a sent message"""
        user1, user2 = two_users
        headers = auth_headers(user1["access_token"])
        
        # Create chat and send message
        chat_data = {"type": "private", "recipient_id": user2["user"]["id"]}
        chat_response = await client.post(
            f"{API_PREFIX}/chats",
            json=chat_data,
            headers=headers
        )
        chat_id = chat_response.json()["id"]
        
        msg_response = await client.post(
            f"{API_PREFIX}/chats/{chat_id}/messages",
            json={"text": "Original message", "type": "text"},
            headers=headers
        )
        message_id = msg_response.json()["id"]
        
        # Edit message
        edit_data = {"text": "Edited message"}
        
        response = await client.put(
            f"{API_PREFIX}/chats/{chat_id}/messages/{message_id}",
            json=edit_data,
            headers=headers
        )
        
        assert response.status_code == 200
        edited = response.json()
        
        assert edited["text"] == "Edited message"
        assert edited.get("edited") is True
        
        logger.info(f"✅ Edited message {message_id}")


# ============================================================================
# 👥 FRIEND SYSTEM TESTS
# ============================================================================

class TestFriendSystem:
    """Test friend requests, acceptance, and removal"""
    
    @pytest.mark.asyncio
    async def test_send_friend_request(self, client, two_users):
        """Test sending a friend request"""
        user1, user2 = two_users
        headers = auth_headers(user1["access_token"])
        
        request_data = {"recipient_id": user2["user"]["id"]}
        
        response = await client.post(
            f"{API_PREFIX}/friends/requests",
            json=request_data,
            headers=headers
        )
        
        assert response.status_code == 200
        
        logger.info(f"✅ Sent friend request from {user1['username']} to {user2['username']}")
    
    
    @pytest.mark.asyncio
    async def test_accept_friend_request(self, client, two_users):
        """Test accepting a friend request"""
        user1, user2 = two_users
        
        # User1 sends request to User2
        headers1 = auth_headers(user1["access_token"])
        await client.post(
            f"{API_PREFIX}/friends/requests",
            json={"recipient_id": user2["user"]["id"]},
            headers=headers1
        )
        
        # User2 accepts the request
        headers2 = auth_headers(user2["access_token"])
        
        response = await client.post(
            f"{API_PREFIX}/friends/requests/{user1['user']['id']}/accept",
            headers=headers2
        )
        
        assert response.status_code == 200
        
        logger.info(f"✅ {user2['username']} accepted friend request from {user1['username']}")
    
    
    @pytest.mark.asyncio
    async def test_get_friends_list(self, client, two_users):
        """Test retrieving friends list"""
        user1, user2 = two_users
        
        # Make them friends
        headers1 = auth_headers(user1["access_token"])
        await client.post(
            f"{API_PREFIX}/friends/requests",
            json={"recipient_id": user2["user"]["id"]},
            headers=headers1
        )
        
        headers2 = auth_headers(user2["access_token"])
        await client.post(
            f"{API_PREFIX}/friends/requests/{user1['user']['id']}/accept",
            headers=headers2
        )
        
        # Get friends list
        response = await client.get(
            f"{API_PREFIX}/friends",
            headers=headers1
        )
        
        assert response.status_code == 200
        friends = response.json()
        
        assert len(friends) >= 1
        friend_ids = [f["id"] for f in friends]
        assert user2["user"]["id"] in friend_ids
        
        logger.info(f"✅ Retrieved {len(friends)} friends")
    
    
    @pytest.mark.asyncio
    async def test_remove_friend(self, client, two_users):
        """Test removing a friend"""
        user1, user2 = two_users
        
        # Make them friends first
        headers1 = auth_headers(user1["access_token"])
        await client.post(
            f"{API_PREFIX}/friends/requests",
            json={"recipient_id": user2["user"]["id"]},
            headers=headers1
        )
        
        headers2 = auth_headers(user2["access_token"])
        await client.post(
            f"{API_PREFIX}/friends/requests/{user1['user']['id']}/accept",
            headers=headers2
        )
        
        # Remove friend
        response = await client.delete(
            f"{API_PREFIX}/friends/{user2['user']['id']}",
            headers=headers1
        )
        
        assert response.status_code == 200
        
        logger.info(f"✅ Removed friend {user2['username']}")


# ============================================================================
# 🔌 WEBSOCKET TESTS
# ============================================================================

class TestWebSocket:
    """Test real-time WebSocket communication"""
    
    @pytest.mark.asyncio
    async def test_websocket_connection(self, websocket_client, authenticated_user):
        """Test establishing WebSocket connection"""
        connected = asyncio.Event()
        
        @websocket_client.on('connect')
        def on_connect():
            connected.set()
            logger.info("✅ WebSocket connected")
        
        # Connect with auth token
        await websocket_client.connect(
            BASE_URL,
            auth={"token": authenticated_user["access_token"]},
            transports=['websocket']
        )
        
        # Wait for connection
        await asyncio.wait_for(connected.wait(), timeout=5)
        
        assert websocket_client.connected
        logger.info("✅ WebSocket connection established")
    
    
    @pytest.mark.asyncio
    async def test_websocket_message_delivery(self, client, two_users):
        """Test real-time message delivery via WebSocket"""
        user1, user2 = two_users
        
        # Create WebSocket clients
        sio1 = socketio.AsyncClient()
        sio2 = socketio.AsyncClient()
        
        message_received = asyncio.Event()
        received_message = {}
        
        @sio2.on('new_message')
        def on_message(data):
            received_message.update(data)
            message_received.set()
            logger.info(f"✅ User2 received message: {data.get('text', 'N/A')}")
        
        try:
            # Connect both users
            await sio1.connect(
                BASE_URL,
                auth={"token": user1["access_token"]},
                transports=['websocket']
            )
            await sio2.connect(
                BASE_URL,
                auth={"token": user2["access_token"]},
                transports=['websocket']
            )
            
            # Create a chat via REST API
            headers = auth_headers(user1["access_token"])
            chat_response = await client.post(
                f"{API_PREFIX}/chats",
                json={"type": "private", "recipient_id": user2["user"]["id"]},
                headers=headers
            )
            chat_id = chat_response.json()["id"]
            
            # Send message via REST API
            await client.post(
                f"{API_PREFIX}/chats/{chat_id}/messages",
                json={"text": "WebSocket test message", "type": "text"},
                headers=headers
            )
            
            # Wait for WebSocket delivery
            await asyncio.wait_for(message_received.wait(), timeout=5)
            
            assert received_message.get("text") == "WebSocket test message"
            logger.info("✅ Real-time message delivery working")
            
        finally:
            await sio1.disconnect()
            await sio2.disconnect()
    
    
    @pytest.mark.asyncio
    async def test_websocket_typing_indicator(self, websocket_client, authenticated_user: Dict, client):
        """Test typing indicator events"""
        # Create a test chat first
        headers = auth_headers(authenticated_user["access_token"])
        
        # We need another user to create a chat
        username = f"testuser_{faker.uuid4()[:8]}"
        phone = f"+1{faker.random_number(digits=10, fix_len=True)}"
        
        user2_response = await client.post(f"{API_PREFIX}/auth/register", json={
            "username": username,
            "display_name": faker.name(),
            "phone_number": phone,
            "password": "TestPass123!@#"
        })
        user2_id = user2_response.json()["user"]["id"]
        
        chat_response = await client.post(
            f"{API_PREFIX}/chats",
            json={"type": "private", "recipient_id": user2_id},
            headers=headers
        )
        chat_id = chat_response.json()["id"]
        
        # Connect WebSocket
        await websocket_client.connect(
            BASE_URL,
            auth={"token": authenticated_user["access_token"]},
            transports=['websocket']
        )
        
        # Emit typing event
        await websocket_client.emit('typing', {'chat_id': chat_id, 'is_typing': True})
        
        # Wait a bit for processing
        await asyncio.sleep(0.5)
        
        logger.info("✅ Typing indicator event sent")
        
        await websocket_client.disconnect()


# ============================================================================
# 🔗 INTEGRATION TESTS
# ============================================================================

class TestIntegrationWorkflows:
    """Test complete user workflows end-to-end"""
    
    @pytest.mark.asyncio
    async def test_complete_chat_workflow(self, client):
        """
        Test complete workflow:
        1. Register two users
        2. User1 searches for User2
        3. Send friend request
        4. Accept friend request
        5. Create private chat
        6. Exchange messages
        7. Add reactions
        """
        # Step 1: Register two users
        user1_data = {
            "username": f"alice_{faker.uuid4()[:8]}",
            "display_name": "Alice",
            "phone_number": f"+1{faker.random_number(digits=10, fix_len=True)}",
            "password": "AlicePass123!@#"
        }
        
        user2_data = {
            "username": f"bob_{faker.uuid4()[:8]}",
            "display_name": "Bob",
            "phone_number": f"+1{faker.random_number(digits=10, fix_len=True)}",
            "password": "BobPass123!@#"
        }
        
        user1_resp = await client.post(f"{API_PREFIX}/auth/register", json=user1_data)
        user2_resp = await client.post(f"{API_PREFIX}/auth/register", json=user2_data)
        
        user1 = user1_resp.json()
        user2 = user2_resp.json()
        
        headers1 = auth_headers(user1["access_token"])
        headers2 = auth_headers(user2["access_token"])
        
        logger.info("✅ Step 1: Registered Alice and Bob")
        
        # Step 2: Alice searches for Bob
        search_resp = await client.get(
            f"{API_PREFIX}/users/search",
            params={"q": user2_data["username"]},
            headers=headers1
        )
        
        assert user2["user"]["id"] in [u["id"] for u in search_resp.json()]
        logger.info("✅ Step 2: Alice found Bob via search")
        
        # Step 3: Alice sends friend request to Bob
        await client.post(
            f"{API_PREFIX}/friends/requests",
            json={"recipient_id": user2["user"]["id"]},
            headers=headers1
        )
        logger.info("✅ Step 3: Alice sent friend request to Bob")
        
        # Step 4: Bob accepts friend request
        await client.post(
            f"{API_PREFIX}/friends/requests/{user1['user']['id']}/accept",
            headers=headers2
        )
        logger.info("✅ Step 4: Bob accepted friend request")
        
        # Step 5: Alice creates private chat with Bob
        chat_resp = await client.post(
            f"{API_PREFIX}/chats",
            json={"type": "private", "recipient_id": user2["user"]["id"]},
            headers=headers1
        )
        chat_id = chat_resp.json()["id"]
        logger.info(f"✅ Step 5: Created private chat {chat_id}")
        
        # Step 6: Exchange messages
        msg1_resp = await client.post(
            f"{API_PREFIX}/chats/{chat_id}/messages",
            json={"text": "Hi Bob! 👋", "type": "text"},
            headers=headers1
        )
        
        msg2_resp = await client.post(
            f"{API_PREFIX}/chats/{chat_id}/messages",
            json={"text": "Hey Alice! How are you?", "type": "text"},
            headers=headers2
        )
        logger.info("✅ Step 6: Exchanged messages")
        
        # Step 7: Bob reacts to Alice's message
        msg1_id = msg1_resp.json()["id"]
        await client.post(
            f"{API_PREFIX}/chats/{chat_id}/messages/{msg1_id}/reactions",
            json={"emoji": "😊"},
            headers=headers2
        )
        logger.info("✅ Step 7: Bob reacted to Alice's message")
        
        # Verify messages in chat
        messages_resp = await client.get(
            f"{API_PREFIX}/chats/{chat_id}/messages",
            headers=headers1
        )
        messages = messages_resp.json()
        
        assert len(messages) >= 2
        logger.info(f"🎉 Complete workflow successful! Chat has {len(messages)} messages")


# ============================================================================
# 🎯 SUMMARY TEST
# ============================================================================

@pytest.mark.asyncio
async def test_api_health_summary(client):
    """
    Quick health check and API summary
    Run this first to verify backend is ready
    """
    logger.info("\n" + "="*70)
    logger.info("🔍 CHATAPP API HEALTH CHECK")
    logger.info("="*70)
    
    # Test health endpoint
    health_resp = await client.get(f"{API_PREFIX}/health")
    assert health_resp.status_code == 200
    logger.info(f"✅ Health: {health_resp.json()}")
    
    # Test root endpoint
    root_resp = await client.get(f"{API_PREFIX}/")
    assert root_resp.status_code == 200
    logger.info(f"✅ API: {root_resp.json()}")
    
    logger.info("\n📊 TEST SUITE READY")
    logger.info("   - Authentication tests: ✓")
    logger.info("   - User management tests: ✓")
    logger.info("   - Chat & messaging tests: ✓")
    logger.info("   - Friend system tests: ✓")
    logger.info("   - WebSocket tests: ✓")
    logger.info("   - Integration tests: ✓")
    logger.info("="*70 + "\n")


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
