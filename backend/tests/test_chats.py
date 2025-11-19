"""
===========================================
🎯 CHAT API TEST SUITE
===========================================

Professional test suite for Chat functionality

Coverage:
- Direct chats (requires friendship)
- Group chats
- Channels
- Send messages
- Join/leave chats
- Chat moderation (ban/promote)
- Chat listing
===========================================
"""

import pytest
from httpx import AsyncClient
import logging
import random

from helpers import (
    create_test_user, establish_friendship,
    create_direct_chat, create_group_chat, create_channel, send_message,
    BASE_URL
)

logger = logging.getLogger(__name__)


# ============================================================================
# DIRECT CHAT TESTS
# ============================================================================

class TestDirectChats:
    """Test direct/private chat functionality"""
    
    @pytest.mark.asyncio
    async def test_create_direct_chat(self):
        """Test creating a direct chat between friends"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            user1 = await create_test_user(client, "direct1")
            user2 = await create_test_user(client, "direct2")
            
            # Must be friends first
            await establish_friendship(client, user1, user2)
            
            # Create direct chat
            chat = await create_direct_chat(client, user1, user2)
            
            print(f"\n💬 Direct Chat Created: {chat['id']}")
            assert chat["chat_type"] == "direct"
            assert len(chat["members"]) == 2
            print(f"✅ Chat type: {chat['chat_type']}")
            print(f"✅ Members: {len(chat['members'])}")
    
    
    @pytest.mark.asyncio
    async def test_send_message_in_direct_chat(self):
        """Test sending messages in direct chat"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            user1 = await create_test_user(client, "msg_sender")
            user2 = await create_test_user(client, "msg_receiver")
            
            await establish_friendship(client, user1, user2)
            chat = await create_direct_chat(client, user1, user2)
            
            # Send message
            message = await send_message(client, user1, chat["id"], "Hello!")
            
            print(f"\n📨 Message Sent: {message['id']}")
            assert message["content"] == "Hello!"
            print(f"✅ Message content: {message['content']}")
    
    
    @pytest.mark.asyncio
    async def test_get_chat_messages(self):
        """Test retrieving messages from a chat"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            user1 = await create_test_user(client, "get_msg1")
            user2 = await create_test_user(client, "get_msg2")
            
            await establish_friendship(client, user1, user2)
            chat = await create_direct_chat(client, user1, user2)
            
            # Send multiple messages
            await send_message(client, user1, chat["id"], "Message 1")
            await send_message(client, user2, chat["id"], "Message 2")
            await send_message(client, user1, chat["id"], "Message 3")
            
            # Get messages
            response = await client.get(
                f"/api/chats/{chat['id']}/messages",
                headers=user1["headers"]
            )
            
            print(f"\n📬 Get Messages: {response.status_code}")
            assert response.status_code == 200
            
            messages = response.json()
            assert len(messages) >= 3
            print(f"✅ Retrieved {len(messages)} messages")


# ============================================================================
# GROUP CHAT TESTS
# ============================================================================

class TestGroupChats:
    """Test group chat functionality"""
    
    @pytest.mark.asyncio
    async def test_create_group_chat(self):
        """Test creating a group chat"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            creator = await create_test_user(client, "group_creator")
            member1 = await create_test_user(client, "group_member1")
            member2 = await create_test_user(client, "group_member2")
            
            # Create group
            chat = await create_group_chat(client, creator, [member1, member2], "Test Group")
            
            print(f"\n👥 Group Chat Created: {chat['id']}")
            assert chat["chat_type"] == "group"
            assert chat["name"] == "Test Group"
            print(f"✅ Group name: {chat['name']}")
    
    
    @pytest.mark.asyncio
    async def test_join_group_chat(self):
        """Test joining a group chat"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            admin = await create_test_user(client, "group_admin")
            joiner = await create_test_user(client, "joiner")
            
            # Create public group
            group_response = await client.post(
                "/api/chats/",
                json={
                    "chat_type": "group",
                    "name": "Join Test Group",
                    "is_public": True
                },
                headers=admin["headers"]
            )
            group_id = group_response.json()["id"]
            
            # User tries to join
            response = await client.post(
                f"/api/chats/{group_id}/join",
                headers=joiner["headers"]
            )
            
            print(f"\n🚪 Join Group: {response.status_code}")
            assert response.status_code == 200
            print(f"✅ User joined group")
    
    
    @pytest.mark.asyncio
    async def test_leave_group(self):
        """Test leaving a group chat"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            admin = await create_test_user(client, "leave_admin")
            member = await create_test_user(client, "leave_member")
            
            # Create group with member
            group_response = await client.post(
                "/api/chats/",
                json={
                    "chat_type": "group",
                    "name": "Leave Test Group",
                    "participant_ids": [member["user"]["id"]]
                },
                headers=admin["headers"]
            )
            group_id = group_response.json()["id"]
            
            # Member leaves group
            response = await client.post(
                f"/api/chats/{group_id}/leave",
                headers=member["headers"]
            )
            
            print(f"\n🚪 Leave Group: {response.status_code}")
            assert response.status_code == 200
            print(f"✅ User left group")


# ============================================================================
# CHANNEL TESTS
# ============================================================================

class TestChannels:
    """Test channel (broadcast) functionality"""
    
    @pytest.mark.asyncio
    async def test_create_channel(self):
        """Test creating a channel"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            creator = await create_test_user(client, "channel_creator")
            
            # Create channel
            chat = await create_channel(client, creator, "Test Channel", is_public=True)
            
            print(f"\n📢 Channel Created: {chat['id']}")
            assert chat["chat_type"] == "channel"
            assert chat["name"] == "Test Channel"
            print(f"✅ Channel name: {chat['name']}")
    
    
    @pytest.mark.asyncio
    async def test_channel_broadcast_message(self):
        """Test broadcasting a message in a channel"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            admin = await create_test_user(client, "broadcast_admin")
            subscriber = await create_test_user(client, "subscriber")
            
            # Create channel
            channel_response = await client.post(
                "/api/chats/",
                json={
                    "chat_type": "channel",
                    "name": "Broadcast Test Channel",
                    "is_public": True
                },
                headers=admin["headers"]
            )
            channel_id = channel_response.json()["id"]
            
            # Subscriber joins channel
            await client.post(
                f"/api/chats/{channel_id}/join",
                headers=subscriber["headers"]
            )
            
            # Admin broadcasts message
            message = await send_message(
                client, admin, channel_id, 
                "📢 Important announcement to all subscribers!"
            )
            
            print(f"\n📢 Broadcast Message sent")
            assert message["content"] == "📢 Important announcement to all subscribers!"
            print(f"✅ Broadcast sent")


# ============================================================================
# CHAT MODERATION TESTS
# ============================================================================

class TestChatModeration:
    """Test chat moderation features"""
    
    @pytest.mark.asyncio
    async def test_ban_user_from_chat(self):
        """Test banning a user from a chat"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            owner = await create_test_user(client, "ban_owner")
            member = await create_test_user(client, "ban_member")
            
            chat = await create_group_chat(client, owner, [member], "Ban Test")
            
            # Ban user
            response = await client.post(
                f"/api/chats/{chat['id']}/ban",
                json={"chat_id": chat['id'], "user_id": member["user"]["id"], "reason": "Test ban"},
                headers=owner["headers"]
            )
            
            print(f"\n🚫 Ban User: {response.status_code}")
            assert response.status_code == 200
            print(f"✅ User banned from chat")
    
    
    @pytest.mark.asyncio
    async def test_promote_user_to_admin(self):
        """Test promoting a user to admin"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            owner = await create_test_user(client, "promote_owner")
            member = await create_test_user(client, "promote_member")
            
            chat = await create_group_chat(client, owner, [member], "Promote Test")
            
            # Promote to admin
            response = await client.post(
                f"/api/chats/{chat['id']}/promote/{member['user']['id']}",
                headers=owner["headers"]
            )
            
            print(f"\n⬆️ Promote to Admin: {response.status_code}")
            assert response.status_code == 200
            print(f"✅ User promoted to admin")


# ============================================================================
# CHAT LISTING TESTS
# ============================================================================

class TestChatListing:
    """Test chat listing and retrieval"""
    
    @pytest.mark.asyncio
    async def test_get_user_chats(self):
        """Test getting all chats for a user"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            user = await create_test_user(client, "list_user")
            friend = await create_test_user(client, "list_friend")
            
            await establish_friendship(client, user, friend)
            
            # Create multiple chats
            await create_direct_chat(client, user, friend)
            await create_group_chat(client, user, [], "Test Group 1")
            await create_group_chat(client, user, [], "Test Group 2")
            
            # Get user's chats
            response = await client.get(
                "/api/chats/",
                headers=user["headers"]
            )
            
            print(f"\n📋 Get Chats: {response.status_code}")
            assert response.status_code == 200
            
            chats = response.json()
            assert len(chats) >= 3
            print(f"✅ Retrieved {len(chats)} chats")


# ============================================================================
# RUN ALL TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
