"""
Test suite for message features.
Tests reply, edit, delete, reactions, pin/unpin, and forward functionality.
"""

import pytest
from datetime import timedelta
import uuid
from backend.utils import utc_now
from backend.auth import SECRET_KEY, ALGORITHM
from jose import jwt


def decode_token(token: str):
    """Helper function to decode JWT token"""
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return payload


@pytest.mark.asyncio
async def test_send_message_with_reply(test_client, test_user, auth_headers, real_test_db):
    """Test sending a message that replies to another message"""
    from backend.database import create_chat, create_message
    
    # Get current user from fixture
    user_id = test_user['user_id']
    
    # Create a chat
    chat_id = str(uuid.uuid4())
    chat_dict = {
        'id': chat_id,
        'chat_type': 'private',
        'participants': [user_id],
        'admins': [user_id],
        'created_at': utc_now(),
        'updated_at': utc_now(),
        'pinned_messages': []
    }
    await create_chat(chat_dict)
    
    # Create original message to reply to
    original_msg_id = str(uuid.uuid4())
    original_msg = {
        'id': original_msg_id,
        'chat_id': chat_id,
        'sender_id': user_id,
        'content': 'Original message',
        'message_type': 'text',
        'status': 'sent',
        'delivered_to': [],
        'read_by': [user_id],
        'reactions': {},
        'edited': False,
        'deleted': False,
        'created_at': utc_now(),
        'updated_at': utc_now()
    }
    await create_message(original_msg)
    
    # Send reply message
    response = await test_client.post(
        f"/api/chats/{chat_id}/messages",
        json={
            "content": "This is a reply",
            "message_type": "text",
            "reply_to": original_msg_id
        },
        headers=auth_headers
    )
    
    assert response.status_code in [200, 201]  # API might return 200 or 201
    data = response.json()
    assert data["content"] == "This is a reply"
    assert "reply_to_message" in data
    assert data["reply_to_message"]["id"] == original_msg_id
    assert data["reply_to_message"]["content"] == "Original message"


@pytest.mark.asyncio
async def test_send_message_with_invalid_reply_to(test_client, test_user, auth_headers, real_test_db):
    """Test sending a message with invalid reply_to reference"""
    from backend.database import create_chat
    
    # Get current user from fixture
    user_id = test_user['user_id']
    
    # Create a chat
    chat_id = str(uuid.uuid4())
    chat_dict = {
        'id': chat_id,
        'chat_type': 'private',
        'participants': [user_id],
        'admins': [user_id],
        'created_at': utc_now(),
        'updated_at': utc_now(),
        'pinned_messages': []
    }
    await create_chat(chat_dict)
    
    # Try to reply to non-existent message
    response = await test_client.post(
        f"/api/chats/{chat_id}/messages",
        json={
            "content": "Reply to nothing",
            "message_type": "text",
            "reply_to": "non-existent-message-id"
        },
        headers=auth_headers
    )
    
    assert response.status_code == 400
    assert "Invalid reply_to message" in response.json()["detail"]


@pytest.mark.asyncio
async def test_edit_message_within_48_hours(test_client, test_user, auth_headers, real_test_db):
    """Test editing a message within the 48-hour window"""
    from backend.database import create_chat, create_message
    
    # Get current user from fixture
    user_id = test_user['user_id']
    
    # Create chat and message
    chat_id = str(uuid.uuid4())
    chat_dict = {
        'id': chat_id,
        'chat_type': 'private',
        'participants': [user_id],
        'admins': [user_id],
        'created_at': utc_now(),
        'updated_at': utc_now(),
        'pinned_messages': []
    }
    await create_chat(chat_dict)
    
    message_id = str(uuid.uuid4())
    message = {
        'id': message_id,
        'chat_id': chat_id,
        'sender_id': user_id,
        'content': 'Original content',
        'message_type': 'text',
        'status': 'sent',
        'delivered_to': [],
        'read_by': [user_id],
        'reactions': {},
        'edited': False,
        'deleted': False,
        'created_at': utc_now(),  # Recent message
        'updated_at': utc_now()
    }
    await create_message(message)
    
    # Edit the message
    response = await test_client.put(
        f"/api/chats/messages/{message_id}?content=Edited content",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    assert response.json()["message"] == "Message updated"


@pytest.mark.asyncio
async def test_edit_message_after_48_hours(test_client, test_user, auth_headers, real_test_db):
    """Test that editing fails after 48 hours"""
    from backend.database import create_chat, create_message
    
    # Get current user from fixture
    user_id = test_user['user_id']
    
    # Create chat
    chat_id = str(uuid.uuid4())
    chat_dict = {
        'id': chat_id,
        'chat_type': 'private',
        'participants': [user_id],
        'admins': [user_id],
        'created_at': utc_now(),
        'updated_at': utc_now(),
        'pinned_messages': []
    }
    await create_chat(chat_dict)
    
    # Create old message (49 hours old)
    message_id = str(uuid.uuid4())
    old_time = utc_now() - timedelta(hours=49)
    message = {
        'id': message_id,
        'chat_id': chat_id,
        'sender_id': user_id,
        'content': 'Old content',
        'message_type': 'text',
        'status': 'sent',
        'delivered_to': [],
        'read_by': [user_id],
        'reactions': {},
        'edited': False,
        'deleted': False,
        'created_at': old_time,
        'updated_at': old_time
    }
    await create_message(message)
    
    # Try to edit old message
    response = await test_client.put(
        f"/api/chats/messages/{message_id}?content=New content",
        headers=auth_headers
    )
    
    assert response.status_code == 400
    assert "too old to edit" in response.json()["detail"]


@pytest.mark.asyncio
async def test_add_reaction_to_message(test_client, test_user, auth_headers, real_test_db):
    """Test adding a reaction to a message"""
    from backend.database import create_chat, create_message
    
    # Get current user from fixture
    user_id = test_user['user_id']
    
    # Create chat and message
    chat_id = str(uuid.uuid4())
    chat_dict = {
        'id': chat_id,
        'chat_type': 'private',
        'participants': [user_id],
        'admins': [user_id],
        'created_at': utc_now(),
        'updated_at': utc_now(),
        'pinned_messages': []
    }
    await create_chat(chat_dict)
    
    message_id = str(uuid.uuid4())
    message = {
        'id': message_id,
        'chat_id': chat_id,
        'sender_id': user_id,
        'content': 'React to this',
        'message_type': 'text',
        'status': 'sent',
        'delivered_to': [],
        'read_by': [user_id],
        'reactions': {},
        'edited': False,
        'deleted': False,
        'created_at': utc_now(),
        'updated_at': utc_now()
    }
    await create_message(message)
    
    # Add reaction
    response = await test_client.post(
        f"/api/chats/messages/{message_id}/react",
        json={"emoji": "👍"},
        headers=auth_headers
    )
    
    assert response.status_code == 200
    assert response.json()["message"] == "Reaction added"


@pytest.mark.asyncio
async def test_remove_reaction_from_message(test_client, test_user, auth_headers, real_test_db):
    """Test removing a reaction from a message"""
    from backend.database import create_chat, create_message
    
    # Get current user from fixture
    user_id = test_user['user_id']
    
    # Create chat and message with existing reaction
    chat_id = str(uuid.uuid4())
    chat_dict = {
        'id': chat_id,
        'chat_type': 'private',
        'participants': [user_id],
        'admins': [user_id],
        'created_at': utc_now(),
        'updated_at': utc_now(),
        'pinned_messages': []
    }
    await create_chat(chat_dict)
    
    message_id = str(uuid.uuid4())
    message = {
        'id': message_id,
        'chat_id': chat_id,
        'sender_id': user_id,
        'content': 'Message with reaction',
        'message_type': 'text',
        'status': 'sent',
        'delivered_to': [],
        'read_by': [user_id],
        'reactions': {"👍": [user_id]},  # Pre-existing reaction
        'edited': False,
        'deleted': False,
        'created_at': utc_now(),
        'updated_at': utc_now()
    }
    await create_message(message)
    
    # Remove reaction (using params since httpx delete doesn't support json)
    response = await test_client.delete(
        f"/api/chats/messages/{message_id}/react?emoji=👍",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    assert response.json()["message"] == "Reaction removed"


@pytest.mark.asyncio
async def test_pin_message_as_admin(test_client, test_user, auth_headers, real_test_db):
    """Test pinning a message as chat admin"""
    from backend.database import create_chat, create_message
    
    # Get current user from fixture
    user_id = test_user['user_id']
    
    # Create chat with user as admin
    chat_id = str(uuid.uuid4())
    chat_dict = {
        'id': chat_id,
        'chat_type': 'group',
        'name': 'Test Group',
        'participants': [user_id],
        'admins': [user_id],  # User is admin
        'created_at': utc_now(),
        'updated_at': utc_now(),
        'pinned_messages': []
    }
    await create_chat(chat_dict)
    
    # Create message
    message_id = str(uuid.uuid4())
    message = {
        'id': message_id,
        'chat_id': chat_id,
        'sender_id': user_id,
        'content': 'Important message',
        'message_type': 'text',
        'status': 'sent',
        'delivered_to': [],
        'read_by': [user_id],
        'reactions': {},
        'edited': False,
        'deleted': False,
        'created_at': utc_now(),
        'updated_at': utc_now()
    }
    await create_message(message)
    
    # Pin message
    response = await test_client.post(
        f"/api/chats/messages/{message_id}/pin",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    assert response.json()["message"] == "Message pinned"


@pytest.mark.asyncio
async def test_pin_message_as_non_admin(test_client, test_user, test_user_2, auth_headers, auth_headers_2, real_test_db):
    """Test that non-admin cannot pin messages"""
    from backend.database import create_chat, create_message
    
    # Get both users from fixtures
    user_id_1 = test_user['user_id']
    user_id_2 = test_user_2['user_id']
    
    # Create chat with user1 as admin, user2 as regular participant
    chat_id = str(uuid.uuid4())
    chat_dict = {
        'id': chat_id,
        'chat_type': 'group',
        'name': 'Test Group',
        'participants': [user_id_1, user_id_2],
        'admins': [user_id_1],  # Only user1 is admin
        'created_at': utc_now(),
        'updated_at': utc_now(),
        'pinned_messages': []
    }
    await create_chat(chat_dict)
    
    # Create message
    message_id = str(uuid.uuid4())
    message = {
        'id': message_id,
        'chat_id': chat_id,
        'sender_id': user_id_1,
        'content': 'Try to pin this',
        'message_type': 'text',
        'status': 'sent',
        'delivered_to': [],
        'read_by': [user_id_1],
        'reactions': {},
        'edited': False,
        'deleted': False,
        'created_at': utc_now(),
        'updated_at': utc_now()
    }
    await create_message(message)
    
    # Try to pin as non-admin (user2)
    response = await test_client.post(
        f"/api/chats/messages/{message_id}/pin",
        headers=auth_headers_2
    )
    
    assert response.status_code == 403
    assert "Only admins can pin messages" in response.json()["detail"]


@pytest.mark.asyncio
async def test_unpin_message(test_client, test_user, auth_headers, real_test_db):
    """Test unpinning a message"""
    from backend.database import create_chat, create_message
    
    # Get current user from fixture
    user_id = test_user['user_id']
    
    # Create message
    message_id = str(uuid.uuid4())
    
    # Create chat with pinned message
    chat_id = str(uuid.uuid4())
    chat_dict = {
        'id': chat_id,
        'chat_type': 'group',
        'name': 'Test Group',
        'participants': [user_id],
        'admins': [user_id],
        'created_at': utc_now(),
        'updated_at': utc_now(),
        'pinned_messages': [message_id]  # Already pinned
    }
    await create_chat(chat_dict)
    
    message = {
        'id': message_id,
        'chat_id': chat_id,
        'sender_id': user_id,
        'content': 'Pinned message',
        'message_type': 'text',
        'status': 'sent',
        'delivered_to': [],
        'read_by': [user_id],
        'reactions': {},
        'edited': False,
        'deleted': False,
        'created_at': utc_now(),
        'updated_at': utc_now()
    }
    await create_message(message)
    
    # Unpin message
    response = await test_client.delete(
        f"/api/chats/messages/{message_id}/pin",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    assert response.json()["message"] == "Message unpinned"


@pytest.mark.asyncio
async def test_forward_messages(test_client, test_user, auth_headers, real_test_db):
    """Test forwarding messages to another chat"""
    from backend.database import create_chat, create_message
    
    # Get current user from fixture
    user_id = test_user['user_id']
    
    # Create source chat
    source_chat_id = str(uuid.uuid4())
    source_chat = {
        'id': source_chat_id,
        'chat_type': 'private',
        'participants': [user_id],
        'admins': [user_id],
        'created_at': utc_now(),
        'updated_at': utc_now(),
        'pinned_messages': []
    }
    await create_chat(source_chat)
    
    # Create target chat
    target_chat_id = str(uuid.uuid4())
    target_chat = {
        'id': target_chat_id,
        'chat_type': 'private',
        'participants': [user_id],
        'admins': [user_id],
        'created_at': utc_now(),
        'updated_at': utc_now(),
        'pinned_messages': []
    }
    await create_chat(target_chat)
    
    # Create messages to forward
    msg_id_1 = str(uuid.uuid4())
    msg_id_2 = str(uuid.uuid4())
    
    for msg_id in [msg_id_1, msg_id_2]:
        message = {
            'id': msg_id,
            'chat_id': source_chat_id,
            'sender_id': user_id,
            'content': f'Message {msg_id}',
            'message_type': 'text',
            'status': 'sent',
            'delivered_to': [],
            'read_by': [user_id],
            'reactions': {},
            'edited': False,
            'deleted': False,
            'created_at': utc_now(),
            'updated_at': utc_now()
        }
        await create_message(message)
    
    # Forward messages (using query params)
    response = await test_client.post(
        f"/api/chats/{target_chat_id}/forward?from_chat_id={source_chat_id}&message_ids={msg_id_1}&message_ids={msg_id_2}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "Forwarded 2 messages" in data["message"]
    assert len(data["forwarded_ids"]) == 2


@pytest.mark.asyncio
async def test_forward_to_non_participant_chat(test_client, test_user, test_user_2, auth_headers, auth_headers_2, real_test_db):
    """Test that forwarding fails when not a participant of target chat"""
    from backend.database import create_chat, create_message
    
    # Get both users from fixtures
    user_id_1 = test_user['user_id']
    user_id_2 = test_user_2['user_id']
    
    # Create source chat (user1 is participant)
    source_chat_id = str(uuid.uuid4())
    source_chat = {
        'id': source_chat_id,
        'chat_type': 'private',
        'participants': [user_id_1],
        'admins': [user_id_1],
        'created_at': utc_now(),
        'updated_at': utc_now(),
        'pinned_messages': []
    }
    await create_chat(source_chat)
    
    # Create target chat (only user2 is participant)
    target_chat_id = str(uuid.uuid4())
    target_chat = {
        'id': target_chat_id,
        'chat_type': 'private',
        'participants': [user_id_2],  # User1 not a participant
        'admins': [user_id_2],
        'created_at': utc_now(),
        'updated_at': utc_now(),
        'pinned_messages': []
    }
    await create_chat(target_chat)
    
    # Create message
    msg_id = str(uuid.uuid4())
    message = {
        'id': msg_id,
        'chat_id': source_chat_id,
        'sender_id': user_id_1,
        'content': 'Forward this',
        'message_type': 'text',
        'status': 'sent',
        'delivered_to': [],
        'read_by': [user_id_1],
        'reactions': {},
        'edited': False,
        'deleted': False,
        'created_at': utc_now(),
        'updated_at': utc_now()
    }
    await create_message(message)
    
    # Try to forward (should fail - user1 not in target chat)
    response = await test_client.post(
        f"/api/chats/{target_chat_id}/forward?from_chat_id={source_chat_id}&message_ids={msg_id}",
        headers=auth_headers  # user1's token
    )
    
    assert response.status_code == 403
    assert "Not a participant of target chat" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_message(test_client, test_user, auth_headers, real_test_db):
    """Test deleting a message for everyone"""
    from backend.database import create_chat, create_message
    
    # Get current user from fixture
    user_id = test_user['user_id']
    
    # Create chat and message
    chat_id = str(uuid.uuid4())
    chat_dict = {
        'id': chat_id,
        'chat_type': 'private',
        'participants': [user_id],
        'admins': [user_id],
        'created_at': utc_now(),
        'updated_at': utc_now(),
        'pinned_messages': []
    }
    await create_chat(chat_dict)
    
    message_id = str(uuid.uuid4())
    message = {
        'id': message_id,
        'chat_id': chat_id,
        'sender_id': user_id,
        'content': 'Delete this message',
        'message_type': 'text',
        'status': 'sent',
        'delivered_to': [],
        'read_by': [user_id],
        'reactions': {},
        'edited': False,
        'deleted': False,
        'created_at': utc_now(),
        'updated_at': utc_now()
    }
    await create_message(message)
    
    # Delete message
    response = await test_client.delete(
        f"/api/chats/messages/{message_id}?for_everyone=true",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    assert response.json()["message"] == "Message deleted"
