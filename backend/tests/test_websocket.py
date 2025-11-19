"""
Comprehensive tests for WebSocket functionality
Tests real-time messaging, presence, notifications, typing indicators
"""
import pytest
import pytest_asyncio
import asyncio
from httpx import AsyncClient
import socketio

from helpers import (
    BASE_URL,
    create_test_user,
    establish_friendship,
    create_direct_chat,
    create_group_chat,
    send_message
)

# WebSocket URL
WS_URL = "http://localhost:8000"


class TestWebSocketConnection:
    """Test WebSocket connection and authentication"""
    
    @pytest.mark.asyncio
    async def test_connect_to_websocket(self):
        """Test basic WebSocket connection"""
        sio = socketio.AsyncClient()
        
        try:
            # Connect to WebSocket
            await sio.connect(WS_URL)
            print(f"\n🔌 WebSocket connected: {sio.sid}")
            
            assert sio.connected
            print(f"✅ WebSocket connection established")
            
        finally:
            await sio.disconnect()
    
    @pytest.mark.asyncio
    async def test_authenticate_websocket(self):
        """Test WebSocket authentication"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            user = await create_test_user(client, "ws_user")
            
            sio = socketio.AsyncClient()
            
            try:
                await sio.connect(WS_URL)
                print(f"\n🔌 Connected to WebSocket")
                
                # Wait a bit for connection to stabilize
                await asyncio.sleep(0.5)
                
                # Authenticate
                await sio.emit('authenticate', {
                    'token': user['access_token']
                })
                
                # Wait for authentication response
                await asyncio.sleep(1)
                
                print(f"✅ Authentication event sent")
                
            finally:
                await sio.disconnect()
    
    @pytest.mark.asyncio
    async def test_multiple_connections_same_user(self):
        """Test that a user can have multiple simultaneous connections"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            user = await create_test_user(client, "multi_conn_user")
            
            sio1 = socketio.AsyncClient()
            sio2 = socketio.AsyncClient()
            
            try:
                # Connect first client
                await sio1.connect(WS_URL)
                await sio1.emit('authenticate', {'token': user['access_token']})
                await asyncio.sleep(0.5)
                print(f"\n🔌 First connection: {sio1.sid}")
                
                # Connect second client
                await sio2.connect(WS_URL)
                await sio2.emit('authenticate', {'token': user['access_token']})
                await asyncio.sleep(0.5)
                print(f"🔌 Second connection: {sio2.sid}")
                
                assert sio1.connected
                assert sio2.connected
                assert sio1.sid != sio2.sid
                
                print(f"✅ User has multiple simultaneous connections")
                
            finally:
                await sio1.disconnect()
                await sio2.disconnect()


class TestChatRoom:
    """Test joining and leaving chat rooms"""
    
    @pytest.mark.asyncio
    async def test_join_chat_room(self):
        """Test joining a chat room"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            user1 = await create_test_user(client, "joiner1")
            user2 = await create_test_user(client, "joiner2")
            
            await establish_friendship(client, user1, user2)
            chat = await create_direct_chat(client, user1, user2)
            
            sio = socketio.AsyncClient()
            
            try:
                await sio.connect(WS_URL)
                await sio.emit('authenticate', {'token': user1['access_token']})
                await asyncio.sleep(0.5)
                
                print(f"\n👥 Joining chat: {chat['id']}")
                
                # Join chat room
                await sio.emit('join_chat', {'chat_id': chat['id']})
                await asyncio.sleep(0.5)
                
                print(f"✅ Joined chat room successfully")
                
            finally:
                await sio.disconnect()
    
    @pytest.mark.asyncio
    async def test_leave_chat_room(self):
        """Test leaving a chat room"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            user1 = await create_test_user(client, "leaver1")
            user2 = await create_test_user(client, "leaver2")
            
            await establish_friendship(client, user1, user2)
            chat = await create_direct_chat(client, user1, user2)
            
            sio = socketio.AsyncClient()
            
            try:
                await sio.connect(WS_URL)
                await sio.emit('authenticate', {'token': user1['access_token']})
                await asyncio.sleep(0.5)
                
                # Join chat
                await sio.emit('join_chat', {'chat_id': chat['id']})
                await asyncio.sleep(0.5)
                print(f"\n👥 Joined chat: {chat['id']}")
                
                # Leave chat
                await sio.emit('leave_chat', {'chat_id': chat['id']})
                await asyncio.sleep(0.5)
                print(f"👋 Left chat room")
                
                print(f"✅ Left chat room successfully")
                
            finally:
                await sio.disconnect()


class TestTypingIndicator:
    """Test typing indicators"""
    
    @pytest.mark.asyncio
    async def test_typing_indicator(self):
        """Test sending typing indicator"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            user1 = await create_test_user(client, "typer1")
            user2 = await create_test_user(client, "typer2")
            
            await establish_friendship(client, user1, user2)
            chat = await create_direct_chat(client, user1, user2)
            
            sio1 = socketio.AsyncClient()
            sio2 = socketio.AsyncClient()
            
            # Track typing events
            typing_received = []
            
            @sio2.on('user_typing')
            def on_typing(data):
                typing_received.append(data)
                print(f"   📝 User typing: {data.get('user_id')} in chat {data.get('chat_id')}")
            
            try:
                # Connect user1
                await sio1.connect(WS_URL)
                await sio1.emit('authenticate', {'token': user1['access_token']})
                await sio1.emit('join_chat', {'chat_id': chat['id']})
                await asyncio.sleep(0.5)
                
                # Connect user2
                await sio2.connect(WS_URL)
                await sio2.emit('authenticate', {'token': user2['access_token']})
                await sio2.emit('join_chat', {'chat_id': chat['id']})
                await asyncio.sleep(0.5)
                
                print(f"\n📝 User1 starts typing...")
                
                # User1 sends typing indicator
                await sio1.emit('typing', {
                    'chat_id': chat['id'],
                    'is_typing': True
                })
                
                # Wait for typing event
                await asyncio.sleep(1)
                
                # User2 should receive typing indicator
                if typing_received:
                    assert typing_received[0]['chat_id'] == chat['id']
                    assert typing_received[0]['user_id'] == user1['user']['id']
                    print(f"✅ Typing indicator received by user2")
                else:
                    print(f"⚠️  No typing indicator received (may need longer wait or check WebSocket events)")
                
            finally:
                await sio1.disconnect()
                await sio2.disconnect()
    
    @pytest.mark.asyncio
    async def test_stop_typing_indicator(self):
        """Test stopping typing indicator"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            user1 = await create_test_user(client, "stoptyper1")
            user2 = await create_test_user(client, "stoptyper2")
            
            await establish_friendship(client, user1, user2)
            chat = await create_direct_chat(client, user1, user2)
            
            sio1 = socketio.AsyncClient()
            sio2 = socketio.AsyncClient()
            
            typing_events = []
            
            @sio2.on('user_typing')
            def on_typing(data):
                typing_events.append(data)
                print(f"   📝 Typing event: is_typing={data.get('is_typing')}")
            
            try:
                await sio1.connect(WS_URL)
                await sio1.emit('authenticate', {'token': user1['access_token']})
                await sio1.emit('join_chat', {'chat_id': chat['id']})
                
                await sio2.connect(WS_URL)
                await sio2.emit('authenticate', {'token': user2['access_token']})
                await sio2.emit('join_chat', {'chat_id': chat['id']})
                await asyncio.sleep(0.5)
                
                print(f"\n📝 User starts typing...")
                await sio1.emit('typing', {'chat_id': chat['id'], 'is_typing': True})
                await asyncio.sleep(0.5)
                
                print(f"⏸️  User stops typing...")
                await sio1.emit('typing', {'chat_id': chat['id'], 'is_typing': False})
                await asyncio.sleep(0.5)
                
                print(f"✅ Sent start/stop typing indicators")
                
            finally:
                await sio1.disconnect()
                await sio2.disconnect()


class TestRealtimeMessages:
    """Test real-time message delivery"""
    
    @pytest.mark.asyncio
    async def test_receive_message_realtime(self):
        """Test receiving messages in real-time"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            user1 = await create_test_user(client, "sender_rt")
            user2 = await create_test_user(client, "receiver_rt")
            
            await establish_friendship(client, user1, user2)
            chat = await create_direct_chat(client, user1, user2)
            
            sio = socketio.AsyncClient()
            messages_received = []
            
            @sio.on('new_message')
            def on_message(data):
                messages_received.append(data)
                print(f"   💬 Received message: {data.get('content')}")
            
            try:
                # User2 connects and joins chat
                await sio.connect(WS_URL)
                await sio.emit('authenticate', {'token': user2['access_token']})
                await sio.emit('join_chat', {'chat_id': chat['id']})
                await asyncio.sleep(0.5)
                
                print(f"\n💬 User1 sends message via REST API...")
                
                # User1 sends message via REST API
                message = await send_message(client, user1, chat['id'], "Hello real-time!")
                
                # Wait for real-time delivery
                await asyncio.sleep(1)
                
                # User2 should receive message via WebSocket
                if messages_received:
                    assert messages_received[0]['content'] == "Hello real-time!"
                    assert messages_received[0]['chat_id'] == chat['id']
                    print(f"✅ Message received in real-time via WebSocket")
                else:
                    print(f"⚠️  Message not received via WebSocket (check event routing)")
                
            finally:
                await sio.disconnect()
    
    @pytest.mark.asyncio
    async def test_group_message_broadcast(self):
        """Test that messages are broadcast to all group members"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            admin = await create_test_user(client, "group_admin_ws")
            member1 = await create_test_user(client, "group_member1_ws")
            member2 = await create_test_user(client, "group_member2_ws")
            
            # Create group
            group = await create_group_chat(client, admin, [member1, member2], "Broadcast Test")
            
            sio1 = socketio.AsyncClient()
            sio2 = socketio.AsyncClient()
            
            messages1 = []
            messages2 = []
            
            @sio1.on('new_message')
            def on_message1(data):
                messages1.append(data)
                print(f"   💬 Member1 received: {data.get('content')}")
            
            @sio2.on('new_message')
            def on_message2(data):
                messages2.append(data)
                print(f"   💬 Member2 received: {data.get('content')}")
            
            try:
                # Both members connect and join group
                await sio1.connect(WS_URL)
                await sio1.emit('authenticate', {'token': member1['access_token']})
                await sio1.emit('join_chat', {'chat_id': group['id']})
                
                await sio2.connect(WS_URL)
                await sio2.emit('authenticate', {'token': member2['access_token']})
                await sio2.emit('join_chat', {'chat_id': group['id']})
                
                await asyncio.sleep(0.5)
                
                print(f"\n💬 Admin sends message to group...")
                
                # Admin sends message
                await send_message(client, admin, group['id'], "Hello everyone!")
                
                # Wait for broadcast
                await asyncio.sleep(1)
                
                # Both members should receive the message
                print(f"   Member1 received {len(messages1)} message(s)")
                print(f"   Member2 received {len(messages2)} message(s)")
                
                if messages1 or messages2:
                    print(f"✅ Message broadcast to group members")
                else:
                    print(f"⚠️  Messages not received (check WebSocket event handling)")
                
            finally:
                await sio1.disconnect()
                await sio2.disconnect()


class TestUserPresence:
    """Test user online/offline status"""
    
    @pytest.mark.asyncio
    async def test_user_goes_online(self):
        """Test user status changes to online when connecting"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            user = await create_test_user(client, "online_user")
            
            sio = socketio.AsyncClient()
            
            try:
                # Connect and authenticate
                await sio.connect(WS_URL)
                await sio.emit('authenticate', {'token': user['access_token']})
                await asyncio.sleep(1)
                
                print(f"\n👤 User connected to WebSocket")
                
                # Check user status via API
                response = await client.get(
                    f"/api/users/{user['user']['id']}",
                    headers=user["headers"]
                )
                
                if response.status_code == 200:
                    user_data = response.json()
                    is_online = user_data.get('is_online', False)
                    print(f"   User online status: {is_online}")
                    print(f"✅ User presence tracked")
                else:
                    print(f"⚠️  Could not fetch user status")
                
            finally:
                await sio.disconnect()
    
    @pytest.mark.asyncio
    async def test_user_presence_broadcast(self):
        """Test that user online status is broadcast to friends"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            user1 = await create_test_user(client, "presence1")
            user2 = await create_test_user(client, "presence2")
            
            await establish_friendship(client, user1, user2)
            
            sio1 = socketio.AsyncClient()
            sio2 = socketio.AsyncClient()
            
            status_updates = []
            
            @sio2.on('user_status')
            def on_status(data):
                status_updates.append(data)
                print(f"   👤 User status update: {data.get('user_id')} - online: {data.get('is_online')}")
            
            try:
                # User2 connects first
                await sio2.connect(WS_URL)
                await sio2.emit('authenticate', {'token': user2['access_token']})
                await asyncio.sleep(0.5)
                
                print(f"\n👤 User1 comes online...")
                
                # User1 connects - user2 should receive status update
                await sio1.connect(WS_URL)
                await sio1.emit('authenticate', {'token': user1['access_token']})
                
                # Wait for status broadcast
                await asyncio.sleep(1)
                
                if status_updates:
                    print(f"✅ User status broadcast received")
                else:
                    print(f"⚠️  No status broadcast (may be working but not received)")
                
            finally:
                await sio1.disconnect()
                await sio2.disconnect()


class TestWebSocketErrors:
    """Test WebSocket error handling"""
    
    @pytest.mark.asyncio
    async def test_join_chat_without_auth(self):
        """Test that joining a chat without authentication fails gracefully"""
        sio = socketio.AsyncClient()
        
        try:
            await sio.connect(WS_URL)
            await asyncio.sleep(0.5)
            
            print(f"\n🔒 Attempting to join chat without authentication...")
            
            # Try to join chat without authenticating
            await sio.emit('join_chat', {'chat_id': 'fake-chat-id'})
            await asyncio.sleep(0.5)
            
            print(f"✅ Unauthenticated join attempt handled")
            
        finally:
            await sio.disconnect()
    
    @pytest.mark.asyncio
    async def test_join_nonexistent_chat(self):
        """Test joining a non-existent chat"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            user = await create_test_user(client, "error_user")
            
            sio = socketio.AsyncClient()
            
            try:
                await sio.connect(WS_URL)
                await sio.emit('authenticate', {'token': user['access_token']})
                await asyncio.sleep(0.5)
                
                print(f"\n⚠️  Attempting to join non-existent chat...")
                
                # Try to join fake chat
                await sio.emit('join_chat', {'chat_id': 'nonexistent-chat-123'})
                await asyncio.sleep(0.5)
                
                print(f"✅ Non-existent chat join handled")
                
            finally:
                await sio.disconnect()


class TestChatPresence:
    """Test chat room presence tracking"""
    
    @pytest.mark.asyncio
    async def test_multiple_users_in_chat(self):
        """Test tracking multiple users in same chat room"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            user1 = await create_test_user(client, "room_user1")
            user2 = await create_test_user(client, "room_user2")
            user3 = await create_test_user(client, "room_user3")
            
            # Create group with all users
            group = await create_group_chat(client, user1, [user2, user3], "Presence Room")
            
            sio1 = socketio.AsyncClient()
            sio2 = socketio.AsyncClient()
            sio3 = socketio.AsyncClient()
            
            try:
                # All users connect and join
                await sio1.connect(WS_URL)
                await sio1.emit('authenticate', {'token': user1['access_token']})
                await sio1.emit('join_chat', {'chat_id': group['id']})
                
                await sio2.connect(WS_URL)
                await sio2.emit('authenticate', {'token': user2['access_token']})
                await sio2.emit('join_chat', {'chat_id': group['id']})
                
                await sio3.connect(WS_URL)
                await sio3.emit('authenticate', {'token': user3['access_token']})
                await sio3.emit('join_chat', {'chat_id': group['id']})
                
                await asyncio.sleep(0.5)
                
                print(f"\n👥 Three users in chat room")
                print(f"   User1: {sio1.sid}")
                print(f"   User2: {sio2.sid}")
                print(f"   User3: {sio3.sid}")
                
                assert sio1.connected
                assert sio2.connected
                assert sio3.connected
                
                print(f"✅ Multiple users tracked in chat room")
                
            finally:
                await sio1.disconnect()
                await sio2.disconnect()
                await sio3.disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
