"""Quick test to verify ChatApp backend"""
import pytest
from httpx import AsyncClient
import random

BASE_URL = "http://localhost:8000"


@pytest.mark.asyncio
async def test_api_root():
    """Test API root endpoint"""
    async with AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        response = await client.get("/api/")
        assert response.status_code == 200
        data = response.json()
        print(f"\n✅ API: {data}")
        assert "ChatApp API" in data["message"]


@pytest.mark.asyncio
async def test_health():
    """Test health endpoint"""
    async with AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        print(f"\n✅ Health: {response.json()}")


@pytest.mark.asyncio
async def test_register_user():
    """Test user registration"""
    async with AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        phone = f"+1555{random.randint(1000000, 9999999)}"
        username = f"testuser_{random.randint(1000, 9999)}"
        
        register_data = {
            "username": username,
            "display_name": "Test User",
            "phone_number": phone,
            "password": "TestPass123!@#"
        }
        
        response = await client.post("/api/auth/register", json=register_data)
        print(f"\n📝 Registration: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ User: {data['user']['username']}")
            print(f"✅ Has token: {'access_token' in data}")
            assert "access_token" in data
            assert "user" in data
        else:
            print(f"❌ Error: {response.json()}")
            assert False, f"Registration failed: {response.json()}"


@pytest.mark.asyncio
async def test_login():
    """Test user login"""
    async with AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # First register
        phone = f"+1555{random.randint(1000000, 9999999)}"
        username = f"testuser_{random.randint(1000, 9999)}"
        password = "TestPass123!@#"
        
        await client.post("/api/auth/register", json={
            "username": username,
            "display_name": "Test User",
            "phone_number": phone,
            "password": password
        })
        
        # Now login
        login_data = {
            "phone_number": phone,
            "password": password
        }
        
        response = await client.post("/api/auth/login", json=login_data)
        print(f"\n🔐 Login: {response.status_code}")
        
        assert response.status_code == 200
        data = response.json()
        print(f"✅ Logged in as: {data['user']['username']}")
        print(f"✅ Access token received")
        assert "access_token" in data


@pytest.mark.asyncio
async def test_user_profile():
    """Test getting user profile"""
    async with AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # Register and get token
        phone = f"+1555{random.randint(1000000, 9999999)}"
        username = f"testuser_{random.randint(1000, 9999)}"
        
        reg_response = await client.post("/api/auth/register", json={
            "username": username,
            "display_name": "Test User",
            "phone_number": phone,
            "password": "TestPass123!@#"
        })
        
        token = reg_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get profile
        response = await client.get("/api/users/me", headers=headers)
        print(f"\n👤 Profile: {response.status_code}")
        
        assert response.status_code == 200
        profile = response.json()
        print(f"✅ Username: {profile['username']}")
        print(f"✅ Display name: {profile['display_name']}")
        assert profile["username"] == username


@pytest.mark.asyncio
async def test_search_users():
    """Test user search"""
    async with AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # Create two users
        user1_phone = f"+1555{random.randint(1000000, 9999999)}"
        user1_username = f"alice_{random.randint(1000, 9999)}"
        
        reg1 = await client.post("/api/auth/register", json={
            "username": user1_username,
            "display_name": "Alice",
            "phone_number": user1_phone,
            "password": "TestPass123!@#"
        })
        
        user2_phone = f"+1555{random.randint(1000000, 9999999)}"
        user2_username = f"bob_{random.randint(1000, 9999)}"
        
        await client.post("/api/auth/register", json={
            "username": user2_username,
            "display_name": "Bob",
            "phone_number": user2_phone,
            "password": "TestPass123!@#"
        })
        
        # User1 searches for user2
        token = reg1.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        response = await client.get(
            f"/api/users/search?q={user2_username[:5]}",
            headers=headers
        )
        
        print(f"\n🔍 Search: {response.status_code}")
        assert response.status_code == 200
        
        results = response.json()
        print(f"✅ Found {len(results)} users")
        usernames = [u["username"] for u in results]
        assert user2_username in usernames
        print(f"✅ Found user: {user2_username}")


@pytest.mark.asyncio
async def test_create_chat_and_send_message():
    """Test creating a chat and sending a message"""
    async with AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # Create two users
        user1_phone = f"+1555{random.randint(1000000, 9999999)}"
        user1 = await client.post("/api/auth/register", json={
            "username": f"user1_{random.randint(1000, 9999)}",
            "display_name": "User One",
            "phone_number": user1_phone,
            "password": "TestPass123!@#"
        })
        
        user2_phone = f"+1555{random.randint(1000000, 9999999)}"
        user2 = await client.post("/api/auth/register", json={
            "username": f"user2_{random.randint(1000, 9999)}",
            "display_name": "User Two",
            "phone_number": user2_phone,
            "password": "TestPass123!@#"
        })
        
        user1_token = user1.json()["access_token"]
        user2_id = user2.json()["user"]["id"]
        headers = {"Authorization": f"Bearer {user1_token}"}
        
        # Create private chat
        chat_response = await client.post(
            "/api/chats",
            json={"type": "private", "recipient_id": user2_id},
            headers=headers
        )
        
        print(f"\n💬 Create Chat: {chat_response.status_code}")
        assert chat_response.status_code == 200
        
        chat = chat_response.json()
        chat_id = chat["id"]
        print(f"✅ Chat created: {chat_id}")
        
        # Send message
        msg_response = await client.post(
            f"/api/chats/{chat_id}/messages",
            json={"text": "Hello! This is a test message.", "type": "text"},
            headers=headers
        )
        
        print(f"💬 Send Message: {msg_response.status_code}")
        assert msg_response.status_code == 200
        
        message = msg_response.json()
        print(f"✅ Message sent: {message['text']}")
        assert message["text"] == "Hello! This is a test message."


@pytest.mark.asyncio
async def test_friend_request_flow():
    """Test complete friend request flow"""
    async with AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # Create two users
        user1_phone = f"+1555{random.randint(1000000, 9999999)}"
        user1 = await client.post("/api/auth/register", json={
            "username": f"friend1_{random.randint(1000, 9999)}",
            "display_name": "Friend One",
            "phone_number": user1_phone,
            "password": "TestPass123!@#"
        })
        
        user2_phone = f"+1555{random.randint(1000000, 9999999)}"
        user2 = await client.post("/api/auth/register", json={
            "username": f"friend2_{random.randint(1000, 9999)}",
            "display_name": "Friend Two",
            "phone_number": user2_phone,
            "password": "TestPass123!@#"
        })
        
        user1_token = user1.json()["access_token"]
        user1_id = user1.json()["user"]["id"]
        user2_token = user2.json()["access_token"]
        user2_id = user2.json()["user"]["id"]
        
        # User1 sends friend request to User2
        req_response = await client.post(
            "/api/friends/requests",
            json={"recipient_id": user2_id},
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        
        print(f"\n👥 Send Friend Request: {req_response.status_code}")
        assert req_response.status_code == 200
        print(f"✅ Friend request sent")
        
        # User2 accepts the request
        accept_response = await client.post(
            f"/api/friends/requests/{user1_id}/accept",
            headers={"Authorization": f"Bearer {user2_token}"}
        )
        
        print(f"👥 Accept Request: {accept_response.status_code}")
        assert accept_response.status_code == 200
        print(f"✅ Friend request accepted")
        
        # Check friends list
        friends_response = await client.get(
            "/api/friends",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        
        print(f"👥 Get Friends: {friends_response.status_code}")
        assert friends_response.status_code == 200
        
        friends = friends_response.json()
        print(f"✅ User1 has {len(friends)} friend(s)")
        friend_ids = [f["id"] for f in friends]
        assert user2_id in friend_ids
        print(f"✅ Friendship confirmed!")
