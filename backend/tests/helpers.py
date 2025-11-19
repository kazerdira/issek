"""
🔧 SHARED TEST HELPERS & FIXTURES
==================================
Reusable functions for ALL test files to avoid duplication

This module provides:
- User creation with authentication
- Friendship establishment
- Chat creation helpers
- Common assertions
"""

import random
from httpx import AsyncClient
from typing import Dict, List, Tuple

BASE_URL = "http://localhost:8000"


# ============================================================================
# USER HELPERS
# ============================================================================

async def create_test_user(client: AsyncClient, suffix: str = None) -> Dict:
    """
    Create a test user and return complete user data with tokens
    
    Returns:
        {
            'user': {...},  # User object
            'access_token': 'xxx',
            'refresh_token': 'xxx',
            'username': 'testuser_xxx',
            'headers': {'Authorization': 'Bearer xxx'}
        }
    """
    import time
    import asyncio
    
    suffix = suffix or str(random.randint(10000, 99999))
    timestamp = str(int(time.time() * 1000))  # Add millisecond timestamp
    phone = f"+1555{random.randint(1000000, 9999999)}"
    username = f"testuser_{suffix}_{timestamp}"
    
    register_data = {
        "username": username,
        "display_name": f"Test User {suffix}",
        "phone_number": phone,
        "password": "TestPass123!@#"
    }
    
    response = await client.post(f"{BASE_URL}/api/auth/register", json=register_data)
    if response.status_code != 200:
        raise Exception(f"Failed to create user: {response.text}")
    
    result = response.json()
    
    return {
        "user": result["user"],
        "access_token": result["access_token"],
        "refresh_token": result["refresh_token"],
        "username": username,
        "headers": {"Authorization": f"Bearer {result['access_token']}"}
    }


async def create_multiple_users(client: AsyncClient, count: int, prefix: str = "user") -> List[Dict]:
    """
    Create multiple test users at once
    
    Args:
        count: Number of users to create
        prefix: Prefix for usernames
        
    Returns:
        List of user dicts
    """
    users = []
    for i in range(count):
        user = await create_test_user(client, f"{prefix}_{i}_{random.randint(1000, 9999)}")
        users.append(user)
    return users


# ============================================================================
# FRIENDSHIP HELPERS
# ============================================================================

async def establish_friendship(client: AsyncClient, user1: Dict, user2: Dict) -> str:
    """
    Make two users friends (send request + accept)
    
    Args:
        user1: First user dict (will send request)
        user2: Second user dict (will accept request)
        
    Returns:
        request_id: The friend request ID
    """
    # User1 sends friend request to User2
    request_data = {"to_user_id": user2["user"]["id"]}
    send_response = await client.post(
        f"{BASE_URL}/api/friends/request",
        json=request_data,
        headers=user1["headers"]
    )
    
    if send_response.status_code != 200:
        raise Exception(f"Failed to send friend request: {send_response.text}")
    
    # User2 gets received requests
    requests_response = await client.get(
        f"{BASE_URL}/api/friends/requests/received",
        headers=user2["headers"]
    )
    
    if requests_response.status_code != 200:
        raise Exception(f"Failed to get friend requests: {requests_response.text}")
    
    requests = requests_response.json()
    if not requests:
        raise Exception("No friend requests found")
    
    request_id = requests[0]["id"]
    
    # User2 accepts the request
    accept_response = await client.post(
        f"{BASE_URL}/api/friends/accept/{request_id}",
        headers=user2["headers"]
    )
    
    if accept_response.status_code != 200:
        raise Exception(f"Failed to accept friend request: {accept_response.text}")
    
    return request_id


async def make_friends_bidirectional(client: AsyncClient, user1: Dict, user2: Dict) -> Tuple[str, str]:
    """
    Make two users friends (both directions verified)
    
    Returns:
        Tuple of (request_id, friendship verified)
    """
    request_id = await establish_friendship(client, user1, user2)
    
    # Verify both users see each other as friends
    user1_friends = await client.get(
        f"{BASE_URL}/api/friends/list",
        headers=user1["headers"]
    )
    user2_friends = await client.get(
        f"{BASE_URL}/api/friends/list",
        headers=user2["headers"]
    )
    
    user1_friend_ids = [f["id"] for f in user1_friends.json()]
    user2_friend_ids = [f["id"] for f in user2_friends.json()]
    
    if user2["user"]["id"] not in user1_friend_ids:
        raise Exception("User2 not in User1's friends list")
    if user1["user"]["id"] not in user2_friend_ids:
        raise Exception("User1 not in User2's friends list")
    
    return request_id, True


async def create_friend_group(client: AsyncClient, count: int) -> List[Dict]:
    """
    Create a group of users who are all friends with each other
    
    Args:
        count: Number of users in the group
        
    Returns:
        List of user dicts, all mutually friends
    """
    users = await create_multiple_users(client, count, "friend_group")
    
    # Make everyone friends with everyone else
    for i, user1 in enumerate(users):
        for user2 in users[i+1:]:
            await establish_friendship(client, user1, user2)
    
    return users


# ============================================================================
# CHAT HELPERS
# ============================================================================

async def create_direct_chat(client: AsyncClient, user1: Dict, user2: Dict) -> Dict:
    """
    Create a direct chat between two users (requires friendship)
    
    Returns:
        Chat object
    """
    chat_data = {
        "chat_type": "direct",
        "participant_ids": [user2["user"]["id"]]
    }
    
    response = await client.post(
        f"{BASE_URL}/api/chats/",
        json=chat_data,
        headers=user1["headers"]
    )
    
    if response.status_code != 200:
        raise Exception(f"Failed to create direct chat: {response.text}")
    
    return response.json()


async def create_group_chat(client: AsyncClient, creator: Dict, members: List[Dict], name: str = None) -> Dict:
    """
    Create a group chat with specified members
    
    Args:
        creator: User creating the group
        members: List of user dicts to add as members
        name: Optional group name
        
    Returns:
        Chat object
    """
    chat_data = {
        "chat_type": "group",
        "name": name or f"Test Group {random.randint(1000, 9999)}",
        "description": "Test group chat",
        "participant_ids": [m["user"]["id"] for m in members]
    }
    
    response = await client.post(
        f"{BASE_URL}/api/chats/",
        json=chat_data,
        headers=creator["headers"]
    )
    
    if response.status_code != 200:
        raise Exception(f"Failed to create group chat: {response.text}")
    
    return response.json()


async def create_channel(client: AsyncClient, creator: Dict, name: str = None, is_public: bool = False) -> Dict:
    """
    Create a channel
    
    Args:
        creator: User creating the channel
        name: Optional channel name
        is_public: Whether channel is public
        
    Returns:
        Chat object
    """
    chat_data = {
        "chat_type": "channel",
        "name": name or f"Test Channel {random.randint(1000, 9999)}",
        "description": "Test channel",
        "is_public": is_public
    }
    
    response = await client.post(
        f"{BASE_URL}/api/chats/",
        json=chat_data,
        headers=creator["headers"]
    )
    
    if response.status_code != 200:
        raise Exception(f"Failed to create channel: {response.text}")
    
    return response.json()


async def send_message(client: AsyncClient, user: Dict, chat_id: str, content: str, message_type: str = "text") -> Dict:
    """
    Send a message to a chat
    
    Args:
        user: User sending the message
        chat_id: Target chat ID
        content: Message content
        message_type: Type of message (text, image, file, etc.)
        
    Returns:
        Message object
    """
    message_data = {
        "chat_id": chat_id,
        "sender_id": user["user"]["id"],
        "content": content,
        "message_type": message_type
    }
    
    response = await client.post(
        f"{BASE_URL}/api/chats/{chat_id}/messages",
        json=message_data,
        headers=user["headers"]
    )
    
    if response.status_code != 200:
        raise Exception(f"Failed to send message: {response.text}")
    
    return response.json()


# ============================================================================
# ASSERTION HELPERS
# ============================================================================

def assert_user_in_list(user_id: str, user_list: List[Dict], message: str = None):
    """Assert that a user ID is in a list of user objects"""
    user_ids = [u["id"] for u in user_list]
    assert user_id in user_ids, message or f"User {user_id} not found in list"


def assert_user_not_in_list(user_id: str, user_list: List[Dict], message: str = None):
    """Assert that a user ID is NOT in a list of user objects"""
    user_ids = [u["id"] for u in user_list]
    assert user_id not in user_ids, message or f"User {user_id} should not be in list"


def assert_chat_has_members(chat: Dict, expected_member_ids: List[str]):
    """Assert that a chat has the expected members"""
    if chat["chat_type"] == "channel":
        actual_ids = chat.get("subscribers", [])
    else:
        actual_ids = [m["user_id"] for m in chat.get("members", [])]
    
    for expected_id in expected_member_ids:
        assert expected_id in actual_ids, f"Member {expected_id} not found in chat"


# ============================================================================
# CLEANUP HELPERS
# ============================================================================

async def cleanup_test_data(client: AsyncClient, users: List[Dict]):
    """
    Clean up test data (optional, for tests that need cleanup)
    Note: Most tests can rely on database being reset between test runs
    """
    # This is a placeholder - implement if needed
    pass
