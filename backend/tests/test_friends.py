"""
🎯 FRIENDS API TEST SUITE
=========================
Professional test suite for Friends functionality

Coverage:
- Send friend requests
- Accept/reject friend requests
- List friend requests (sent/received)
- List friends
- Remove friends
- Block/unblock users
- Check friendship status
"""

import pytest
from httpx import AsyncClient
import logging
from helpers import (
    create_test_user, create_multiple_users, establish_friendship,
    assert_user_in_list, assert_user_not_in_list, BASE_URL
)

logger = logging.getLogger(__name__)


# ============================================================================
# FRIEND REQUEST TESTS
# ============================================================================

class TestFriendRequests:
    """Test friend request functionality"""
    
    @pytest.mark.asyncio
    async def test_send_friend_request(self):
        """Test sending a friend request"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            sender = await create_test_user(client, "sender")
            recipient = await create_test_user(client, "recipient")
            
            # Send friend request
            request_data = {
                "to_user_id": recipient["user"]["id"]
            }
            
            response = await client.post(
                "/api/friends/request",
                json=request_data,
                headers=sender["headers"]
            )
            
            print(f"\n👥 Send Friend Request: {response.status_code}")
            assert response.status_code == 200
            
            result = response.json()
            print(f"✅ Friend request sent")
            print(f"✅ From: {sender['username']}")
            print(f"✅ To: {recipient['username']}")
    
    
    @pytest.mark.asyncio
    async def test_accept_friend_request(self):
        """Test accepting a friend request"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            sender = await create_test_user(client, "req_sender")
            recipient = await create_test_user(client, "req_recipient")
            
            # Send friend request
            await client.post(
                "/api/friends/request",
                json={"to_user_id": recipient["user"]["id"]},
                headers=sender["headers"]
            )
            
            # Get received requests to find the request ID
            requests_response = await client.get(
                "/api/friends/requests/received",
                headers=recipient["headers"]
            )
            
            requests = requests_response.json()
            assert len(requests) > 0
            
            request_id = requests[0]["id"]
            
            # Accept the request
            response = await client.post(
                f"/api/friends/accept/{request_id}",
                headers=recipient["headers"]
            )
            
            print(f"\n✅ Accept Friend Request: {response.status_code}")
            assert response.status_code == 200
            
            print(f"✅ Friend request accepted")
            print(f"✅ Request ID: {request_id}")
    
    
    @pytest.mark.asyncio
    async def test_reject_friend_request(self):
        """Test rejecting a friend request"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            sender = await create_test_user(client, "reject_sender")
            recipient = await create_test_user(client, "reject_recipient")
            
            # Send friend request
            await client.post(
                "/api/friends/request",
                json={"to_user_id": recipient["user"]["id"]},
                headers=sender["headers"]
            )
            
            # Get received requests
            requests_response = await client.get(
                "/api/friends/requests/received",
                headers=recipient["headers"]
            )
            
            requests = requests_response.json()
            request_id = requests[0]["id"]
            
            # Reject the request
            response = await client.post(
                f"/api/friends/reject/{request_id}",
                headers=recipient["headers"]
            )
            
            print(f"\n❌ Reject Friend Request: {response.status_code}")
            assert response.status_code == 200
            
            print(f"✅ Friend request rejected")
    
    
    @pytest.mark.asyncio
    async def test_get_received_friend_requests(self):
        """Test getting received friend requests"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            recipient = await create_test_user(client, "requests_recipient")
            sender1 = await create_test_user(client, "sender1")
            sender2 = await create_test_user(client, "sender2")
            
            # Send multiple friend requests
            await client.post(
                "/api/friends/request",
                json={"to_user_id": recipient["user"]["id"]},
                headers=sender1["headers"]
            )
            
            await client.post(
                "/api/friends/request",
                json={"to_user_id": recipient["user"]["id"]},
                headers=sender2["headers"]
            )
            
            # Get received requests
            response = await client.get(
                "/api/friends/requests/received",
                headers=recipient["headers"]
            )
            
            print(f"\n📥 Get Received Requests: {response.status_code}")
            assert response.status_code == 200
            
            requests = response.json()
            assert len(requests) >= 2
            
            print(f"✅ Retrieved {len(requests)} friend requests")
            for req in requests:
                print(f"  - From: {req['from_user']['username']}")


# ============================================================================
# FRIENDS LIST TESTS
# ============================================================================

class TestFriendsList:
    """Test friends list management"""
    
    @pytest.mark.asyncio
    async def test_get_friends_list(self):
        """Test getting user's friends list"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            user = await create_test_user(client, "friends_user")
            friend1 = await create_test_user(client, "friend1")
            friend2 = await create_test_user(client, "friend2")
            
            # Establish friendships using helper
            await establish_friendship(client, user, friend1)
            await establish_friendship(client, user, friend2)
            
            # Get friends list
            response = await client.get(
                f"{BASE_URL}/api/friends/list",
                headers=user["headers"]
            )
            
            print(f"\n👥 Get Friends List: {response.status_code}")
            assert response.status_code == 200
            
            friends = response.json()
            assert len(friends) >= 2
            
            # Use assertion helpers
            assert_user_in_list(friend1["user"]["id"], friends)
            assert_user_in_list(friend2["user"]["id"], friends)
            
            print(f"✅ Retrieved {len(friends)} friends")
            for friend in friends:
                print(f"  - {friend['username']} ({friend['display_name']})")
    
    
    @pytest.mark.asyncio
    async def test_remove_friend(self):
        """Test removing a friend"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            user = await create_test_user(client, "remove_user")
            friend = await create_test_user(client, "remove_friend")
            
            # Establish friendship using helper
            await establish_friendship(client, user, friend)
            
            # Remove friend
            response = await client.delete(
                f"{BASE_URL}/api/friends/remove/{friend['user']['id']}",
                headers=user["headers"]
            )
            
            print(f"\n💔 Remove Friend: {response.status_code}")
            assert response.status_code == 200
            
            # Verify friend is removed
            friends_response = await client.get(
                f"{BASE_URL}/api/friends/list",
                headers=user["headers"]
            )
            
            friends = friends_response.json()
            assert_user_not_in_list(friend["user"]["id"], friends)
            
            print(f"✅ Friend removed")


# ============================================================================
# BLOCKING TESTS
# ============================================================================

class TestBlocking:
    """Test user blocking functionality"""
    
    @pytest.mark.asyncio
    async def test_block_user(self):
        """Test blocking a user"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            blocker = await create_test_user(client, "blocker")
            blocked = await create_test_user(client, "blocked")
            
            # Block user
            response = await client.post(
                f"/api/friends/block/{blocked['user']['id']}",
                headers=blocker["headers"]
            )
            
            print(f"\n🚫 Block User: {response.status_code}")
            assert response.status_code == 200
            
            print(f"✅ User blocked")
            print(f"✅ Blocker: {blocker['username']}")
            print(f"✅ Blocked: {blocked['username']}")
    
    
    @pytest.mark.asyncio
    async def test_unblock_user(self):
        """Test unblocking a user"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            blocker = await create_test_user(client, "unblocker")
            blocked = await create_test_user(client, "unblocked")
            
            # Block user first
            await client.post(
                f"/api/friends/block/{blocked['user']['id']}",
                headers=blocker["headers"]
            )
            
            # Unblock user
            response = await client.delete(
                f"/api/friends/unblock/{blocked['user']['id']}",
                headers=blocker["headers"]
            )
            
            print(f"\n✅ Unblock User: {response.status_code}")
            assert response.status_code == 200
            
            print(f"✅ User unblocked")
    
    
    @pytest.mark.asyncio
    async def test_get_blocked_users(self):
        """Test getting list of blocked users"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            blocker = await create_test_user(client, "list_blocker")
            blocked1 = await create_test_user(client, "list_blocked1")
            blocked2 = await create_test_user(client, "list_blocked2")
            
            # Block multiple users
            await client.post(
                f"/api/friends/block/{blocked1['user']['id']}",
                headers=blocker["headers"]
            )
            
            await client.post(
                f"/api/friends/block/{blocked2['user']['id']}",
                headers=blocker["headers"]
            )
            
            # Get blocked users list
            response = await client.get(
                "/api/friends/blocked",
                headers=blocker["headers"]
            )
            
            print(f"\n📋 Get Blocked Users: {response.status_code}")
            assert response.status_code == 200
            
            blocked_users = response.json()
            assert len(blocked_users) >= 2
            
            blocked_usernames = [u["username"] for u in blocked_users]
            assert blocked1["username"] in blocked_usernames
            assert blocked2["username"] in blocked_usernames
            
            print(f"✅ Retrieved {len(blocked_users)} blocked users")
            for user in blocked_users:
                print(f"  - {user['username']}")


# ============================================================================
# COMPLETE FRIENDSHIP WORKFLOW TEST
# ============================================================================

class TestFriendshipWorkflow:
    """Test complete friendship workflows"""
    
    @pytest.mark.asyncio
    async def test_complete_friendship_workflow(self):
        """Test complete friendship workflow from request to removal"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            alice = await create_test_user(client, "alice_flow")
            bob = await create_test_user(client, "bob_flow")
            
            print(f"\n🎭 COMPLETE FRIENDSHIP WORKFLOW TEST")
            print(f"👤 Alice: {alice['username']}")
            print(f"👤 Bob: {bob['username']}")
            
            # Step 1: Establish friendship using helper
            request_id = await establish_friendship(client, alice, bob)
            print(f"✅ Step 1: Alice & Bob are now friends (request_id: {request_id})")
            
            # Step 2: Verify both users see each other as friends
            alice_friends = await client.get(
                f"{BASE_URL}/api/friends/list",
                headers=alice["headers"]
            )
            bob_friends = await client.get(
                f"{BASE_URL}/api/friends/list", 
                headers=bob["headers"]
            )
            
            assert_user_in_list(bob["user"]["id"], alice_friends.json())
            assert_user_in_list(alice["user"]["id"], bob_friends.json())
            print(f"✅ Step 2: Both users verified in each other's friends list")
            
            # Step 3: Alice removes Bob as friend
            response = await client.delete(
                f"{BASE_URL}/api/friends/remove/{bob['user']['id']}",
                headers=alice["headers"]
            )
            assert response.status_code == 200
            print(f"✅ Step 3: Alice removed Bob as friend")
            
            # Step 4: Verify friendship is removed
            alice_friends_after = await client.get(
                f"{BASE_URL}/api/friends/list",
                headers=alice["headers"]
            )
            
            assert_user_not_in_list(bob["user"]["id"], alice_friends_after.json())
            print(f"✅ Step 4: Friendship successfully removed")
            
            print(f"🎉 COMPLETE WORKFLOW TEST PASSED!")


# ============================================================================
# RUN ALL TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])