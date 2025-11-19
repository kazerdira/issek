import pytest
from httpx import AsyncClient
from typing import Dict, Any

from tests.conftest import TestDataFactory


@pytest.mark.api
class TestFriendEndpoints:
    """Test friend-related endpoints."""

    async def test_send_friend_request(self, authenticated_client: AsyncClient, test_user2: Dict[str, Any]):
        """Test sending a friend request."""
        request_data = {"user_id": test_user2["id"]}
        
        response = await authenticated_client.post("/api/friends/request", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    async def test_send_friend_request_to_self(self, authenticated_client: AsyncClient, test_user: Dict[str, Any]):
        """Test sending friend request to self (should fail)."""
        request_data = {"user_id": test_user["id"]}
        
        response = await authenticated_client.post("/api/friends/request", json=request_data)
        
        assert response.status_code == 400

    async def test_send_duplicate_friend_request(self, authenticated_client: AsyncClient, test_user2: Dict[str, Any]):
        """Test sending duplicate friend request."""
        request_data = {"user_id": test_user2["id"]}
        
        # Send first request
        response1 = await authenticated_client.post("/api/friends/request", json=request_data)
        assert response1.status_code == 200
        
        # Send duplicate request
        response2 = await authenticated_client.post("/api/friends/request", json=request_data)
        assert response2.status_code == 400  # Should reject duplicate

    async def test_get_friend_requests_received(self, client: AsyncClient, test_user: Dict[str, Any], test_user2: Dict[str, Any]):
        """Test getting received friend requests."""
        # Send request from user1 to user2
        client.headers.update({"Authorization": f"Bearer {test_user['access_token']}"})
        request_data = {"user_id": test_user2["id"]}
        await client.post("/api/friends/request", json=request_data)
        
        # Get received requests for user2
        client.headers.update({"Authorization": f"Bearer {test_user2['access_token']}"})
        response = await client.get("/api/friends/requests/received")
        
        assert response.status_code == 200
        requests = response.json()
        assert isinstance(requests, list)
        assert len(requests) > 0
        
        # Check request structure
        for req in requests:
            assert "id" in req
            assert "sender" in req
            assert "created_at" in req

    async def test_get_friend_requests_sent(self, authenticated_client: AsyncClient, test_user2: Dict[str, Any]):
        """Test getting sent friend requests."""
        # Send a friend request
        request_data = {"user_id": test_user2["id"]}
        await authenticated_client.post("/api/friends/request", json=request_data)
        
        # Get sent requests
        response = await authenticated_client.get("/api/friends/requests/sent")
        
        assert response.status_code == 200
        requests = response.json()
        assert isinstance(requests, list)
        assert len(requests) > 0

    async def test_accept_friend_request(self, client: AsyncClient, test_user: Dict[str, Any], test_user2: Dict[str, Any]):
        """Test accepting a friend request."""
        # Send request from user1 to user2
        client.headers.update({"Authorization": f"Bearer {test_user['access_token']}"})
        request_data = {"user_id": test_user2["id"]}
        await client.post("/api/friends/request", json=request_data)
        
        # Get the request ID (would need to implement this properly)
        client.headers.update({"Authorization": f"Bearer {test_user2['access_token']}"})
        requests_response = await client.get("/api/friends/requests/received")
        requests = requests_response.json()
        request_id = requests[0]["id"]
        
        # Accept the request
        response = await client.post(f"/api/friends/requests/{request_id}/accept")
        
        assert response.status_code == 200

    async def test_reject_friend_request(self, client: AsyncClient, test_user: Dict[str, Any], test_user2: Dict[str, Any]):
        """Test rejecting a friend request."""
        # Send request from user1 to user2
        client.headers.update({"Authorization": f"Bearer {test_user['access_token']}"})
        request_data = {"user_id": test_user2["id"]}
        await client.post("/api/friends/request", json=request_data)
        
        # Get the request ID
        client.headers.update({"Authorization": f"Bearer {test_user2['access_token']}"})
        requests_response = await client.get("/api/friends/requests/received")
        requests = requests_response.json()
        request_id = requests[0]["id"]
        
        # Reject the request
        response = await client.post(f"/api/friends/requests/{request_id}/reject")
        
        assert response.status_code == 200

    async def test_get_friends_list(self, client: AsyncClient, test_user: Dict[str, Any], test_user2: Dict[str, Any]):
        """Test getting friends list."""
        # First become friends (send and accept request)
        client.headers.update({"Authorization": f"Bearer {test_user['access_token']}"})
        request_data = {"user_id": test_user2["id"]}
        await client.post("/api/friends/request", json=request_data)
        
        client.headers.update({"Authorization": f"Bearer {test_user2['access_token']}"})
        requests_response = await client.get("/api/friends/requests/received")
        requests = requests_response.json()
        request_id = requests[0]["id"]
        await client.post(f"/api/friends/requests/{request_id}/accept")
        
        # Get friends list
        response = await client.get("/api/friends/list")
        
        assert response.status_code == 200
        friends = response.json()
        assert isinstance(friends, list)
        assert len(friends) > 0
        
        # Check friend structure
        for friend in friends:
            assert "id" in friend
            assert "username" in friend
            assert "display_name" in friend

    async def test_remove_friend(self, client: AsyncClient, test_user: Dict[str, Any], test_user2: Dict[str, Any]):
        """Test removing a friend."""
        # First become friends
        client.headers.update({"Authorization": f"Bearer {test_user['access_token']}"})
        request_data = {"user_id": test_user2["id"]}
        await client.post("/api/friends/request", json=request_data)
        
        client.headers.update({"Authorization": f"Bearer {test_user2['access_token']}"})
        requests_response = await client.get("/api/friends/requests/received")
        requests = requests_response.json()
        request_id = requests[0]["id"]
        await client.post(f"/api/friends/requests/{request_id}/accept")
        
        # Remove friend
        client.headers.update({"Authorization": f"Bearer {test_user['access_token']}"})
        response = await client.delete(f"/api/friends/{test_user2['id']}")
        
        assert response.status_code == 200


@pytest.mark.api
class TestBlockEndpoints:
    """Test user blocking functionality."""

    async def test_block_user(self, authenticated_client: AsyncClient, test_user2: Dict[str, Any]):
        """Test blocking a user."""
        block_data = {"user_id": test_user2["id"]}
        
        response = await authenticated_client.post("/api/friends/block", json=block_data)
        
        assert response.status_code == 200

    async def test_block_self(self, authenticated_client: AsyncClient, test_user: Dict[str, Any]):
        """Test blocking self (should fail)."""
        block_data = {"user_id": test_user["id"]}
        
        response = await authenticated_client.post("/api/friends/block", json=block_data)
        
        assert response.status_code == 400

    async def test_get_blocked_users(self, authenticated_client: AsyncClient, test_user2: Dict[str, Any]):
        """Test getting list of blocked users."""
        # First block a user
        block_data = {"user_id": test_user2["id"]}
        await authenticated_client.post("/api/friends/block", json=block_data)
        
        # Get blocked users
        response = await authenticated_client.get("/api/friends/blocked")
        
        assert response.status_code == 200
        blocked_users = response.json()
        assert isinstance(blocked_users, list)
        assert len(blocked_users) > 0

    async def test_unblock_user(self, authenticated_client: AsyncClient, test_user2: Dict[str, Any]):
        """Test unblocking a user."""
        # First block a user
        block_data = {"user_id": test_user2["id"]}
        await authenticated_client.post("/api/friends/block", json=block_data)
        
        # Unblock the user
        response = await authenticated_client.delete(f"/api/friends/block/{test_user2['id']}")
        
        assert response.status_code == 200

    async def test_send_friend_request_to_blocked_user(self, authenticated_client: AsyncClient, test_user2: Dict[str, Any]):
        """Test sending friend request to blocked user (should fail)."""
        # First block the user
        block_data = {"user_id": test_user2["id"]}
        await authenticated_client.post("/api/friends/block", json=block_data)
        
        # Try to send friend request
        request_data = {"user_id": test_user2["id"]}
        response = await authenticated_client.post("/api/friends/request", json=request_data)
        
        assert response.status_code == 400  # Should be rejected

    async def test_blocked_user_cannot_send_request(self, client: AsyncClient, test_user: Dict[str, Any], test_user2: Dict[str, Any]):
        """Test that blocked user cannot send friend request."""
        # User1 blocks user2
        client.headers.update({"Authorization": f"Bearer {test_user['access_token']}"})
        block_data = {"user_id": test_user2["id"]}
        await client.post("/api/friends/block", json=block_data)
        
        # User2 tries to send request to user1 (should fail)
        client.headers.update({"Authorization": f"Bearer {test_user2['access_token']}"})
        request_data = {"user_id": test_user["id"]}
        response = await client.post("/api/friends/request", json=request_data)
        
        assert response.status_code == 400  # Should be rejected