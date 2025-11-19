from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional
import uuid
from datetime import datetime, timedelta, timezone
import logging

from models import (
    ChatCreate, ChatResponse, MessageCreate, MessageResponse,
    MessageType, ChatType, UserResponse, ReactionCreate, ReactionRemove
)
from auth import get_current_user
from database import (
    Database, get_chat_by_id, get_user_chats, create_chat,
    get_chat_messages, create_message, get_message_by_id,
    update_message, get_user_by_id
)
from socket_manager import socket_manager
from utils import utc_now

router = APIRouter(prefix="/chats", tags=["Chats"])
logger = logging.getLogger(__name__)

@router.post("/", response_model=ChatResponse)
async def create_new_chat(
    chat_data: ChatCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new chat (direct or group)"""
    
    # Validate participants
    if current_user['id'] not in chat_data.participants:
        chat_data.participants.append(current_user['id'])
    
    if chat_data.chat_type == ChatType.DIRECT and len(chat_data.participants) != 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Direct chat must have exactly 2 participants"
        )
    
    # Check if direct chat already exists
    if chat_data.chat_type == ChatType.DIRECT:
        db = Database.get_db()
        existing_chat = await db.chats.find_one({
            'chat_type': 'direct',
            'participants': {'$all': chat_data.participants}
        })
        
        if existing_chat:
            # Return existing chat
            return ChatResponse(**existing_chat)
    
    # Create new chat
    chat_id = str(uuid.uuid4())
    chat_dict = chat_data.dict()
    chat_dict.update({
        'id': chat_id,
        'created_by': current_user['id'],
        'admins': [current_user['id']],
        'created_at': utc_now(),
        'updated_at': utc_now(),
        'pinned_messages': [],
        'muted_by': []
    })
    
    await create_chat(chat_dict)
    
    # Get participant details
    participants_details = []
    for participant_id in chat_data.participants:
        user = await get_user_by_id(participant_id)
        if user:
            participants_details.append(UserResponse(
                id=user['id'],
                username=user['username'],
                display_name=user['display_name'],
                avatar=user.get('avatar'),
                bio=user.get('bio'),
                phone_number=user.get('phone_number'),
                email=user.get('email'),
                role=user.get('role', 'regular'),
                is_online=user.get('is_online', False),
                last_seen=user.get('last_seen'),
                created_at=user['created_at']
            ))
    
    response = ChatResponse(**chat_dict)
    response.participant_details = participants_details
    
    # Notify all participants (except creator) via socket
    if chat_data.chat_type in [ChatType.GROUP, ChatType.CHANNEL]:
        response_dict = response.model_dump(mode='json')
        for participant_id in chat_data.participants:
            if participant_id != current_user['id']:
                await socket_manager.send_message_to_user(
                    participant_id,
                    'chat_created',
                    {
                        'chat': response_dict
                    }
                )
    
    return response

@router.get("/", response_model=List[ChatResponse])
async def get_chats(current_user: dict = Depends(get_current_user)):
    """Get all chats for current user"""
    chats = await get_user_chats(current_user['id'])
    
    # Collect all unique participant IDs
    all_participant_ids = set()
    for chat in chats:
        all_participant_ids.update(chat['participants'])
    
    # Batch fetch all users
    db = Database.get_db()
    users_list = await db.users.find({"id": {"$in": list(all_participant_ids)}}).to_list(None)
    users_map = {user['id']: user for user in users_list}
    
    result = []
    for chat in chats:
        # Get participant details from the map
        participants_details = []
        for participant_id in chat['participants']:
            user = users_map.get(participant_id)
            if user:
                participants_details.append(UserResponse(
                    id=user['id'],
                    username=user['username'],
                    display_name=user['display_name'],
                    avatar=user.get('avatar'),
                    bio=user.get('bio'),
                    phone_number=user.get('phone_number'),
                    email=user.get('email'),
                    role=user.get('role', 'regular'),
                    is_online=user.get('is_online', False),
                    last_seen=user.get('last_seen'),
                    created_at=user['created_at']
                ))
        
        # Count unread messages
        db = Database.get_db()
        unread_count = await db.messages.count_documents({
            'chat_id': chat['id'],
            'sender_id': {'$ne': current_user['id']},
            'read_by': {'$ne': current_user['id']},
            'deleted': False
        })
        
        chat_response = ChatResponse(**chat)
        chat_response.participant_details = participants_details
        chat_response.unread_count = unread_count
        result.append(chat_response)
    
    return result

@router.get("/{chat_id}", response_model=ChatResponse)
async def get_chat(
    chat_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get chat by ID"""
    chat = await get_chat_by_id(chat_id)
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    if current_user['id'] not in chat['participants']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a participant of this chat"
        )
    
    # Get participant details
    participants_details = []
    for participant_id in chat['participants']:
        user = await get_user_by_id(participant_id)
        if user:
            participants_details.append(UserResponse(
                id=user['id'],
                username=user['username'],
                display_name=user['display_name'],
                avatar=user.get('avatar'),
                bio=user.get('bio'),
                phone_number=user.get('phone_number'),
                email=user.get('email'),
                role=user.get('role', 'regular'),
                is_online=user.get('is_online', False),
                last_seen=user.get('last_seen'),
                created_at=user['created_at']
            ))
    
    chat_response = ChatResponse(**chat)
    chat_response.participant_details = participants_details
    
    return chat_response

@router.get("/{chat_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    chat_id: str,
    limit: int = Query(default=50, le=100),
    skip: int = Query(default=0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """Get messages for a chat"""
    chat = await get_chat_by_id(chat_id)
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    if current_user['id'] not in chat['participants']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a participant of this chat"
        )
    
    messages = await get_chat_messages(chat_id, limit, skip)
    
    # Filter out messages that current user has deleted for themselves
    messages = [msg for msg in messages if current_user['id'] not in msg.get('deleted_for', [])]
    
    # Batch fetch all unique senders
    sender_ids = list(set(msg['sender_id'] for msg in messages))
    db = Database.get_db()
    senders_list = await db.users.find({"id": {"$in": sender_ids}}).to_list(None)
    senders_map = {user['id']: user for user in senders_list}
    
    # Batch fetch replied messages (for reply previews)
    reply_ids = [msg.get('reply_to') for msg in messages if msg.get('reply_to')]
    replied_messages_map = {}
    if reply_ids:
        replied_messages = await db.messages.find({"id": {"$in": reply_ids}}).to_list(None)
        replied_messages_map = {msg['id']: msg for msg in replied_messages}
    
    # Add sender details and replied message to each message
    result = []
    for msg in messages:
        sender = senders_map.get(msg['sender_id'])
        sender_response = None
        if sender:
            sender_response = UserResponse(
                id=sender['id'],
                username=sender['username'],
                display_name=sender['display_name'],
                avatar=sender.get('avatar'),
                bio=sender.get('bio'),
                phone_number=sender.get('phone_number'),
                email=sender.get('email'),
                role=sender.get('role', 'regular'),
                is_online=sender.get('is_online', False),
                last_seen=sender.get('last_seen'),
                created_at=sender['created_at']
            )
        
        msg_response = MessageResponse(**msg)
        msg_response.sender = sender_response
        
        # Add replied message data if this is a reply
        if msg.get('reply_to') and msg['reply_to'] in replied_messages_map:
            replied_msg = replied_messages_map[msg['reply_to']]
            replied_sender = senders_map.get(replied_msg['sender_id'])
            replied_sender_response = None
            if replied_sender:
                replied_sender_response = UserResponse(
                    id=replied_sender['id'],
                    username=replied_sender['username'],
                    display_name=replied_sender['display_name'],
                    avatar=replied_sender.get('avatar'),
                    bio=replied_sender.get('bio'),
                    phone_number=replied_sender.get('phone_number'),
                    email=replied_sender.get('email'),
                    role=replied_sender.get('role', 'regular'),
                    is_online=replied_sender.get('is_online', False),
                    last_seen=replied_sender.get('last_seen'),
                    created_at=replied_sender['created_at']
                )
            
            replied_msg_response = MessageResponse(**replied_msg)
            replied_msg_response.sender = replied_sender_response
            msg_response.reply_to_message = replied_msg_response
        
        result.append(msg_response)
    
    return result

@router.post("/{chat_id}/messages", response_model=MessageResponse)
async def send_message(
    chat_id: str,
    message_data: MessageCreate,
    current_user: dict = Depends(get_current_user)
):
    """Send a message to a chat"""
    chat = await get_chat_by_id(chat_id)
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    if current_user['id'] not in chat['participants']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a participant of this chat"
        )
    
    # Check for blocks in direct chats
    if chat['chat_type'] == ChatType.DIRECT:
        other_participant_id = next((p for p in chat['participants'] if p != current_user['id']), None)
        if other_participant_id:
            other_user = await get_user_by_id(other_participant_id)
            if other_user and current_user['id'] in other_user.get('blocked_users', []):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You cannot send messages to this user"
                )
            # Also check if current user blocked the other user (optional, but good for consistency)
            if other_participant_id in current_user.get('blocked_users', []):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You have blocked this user. Unblock to send messages."
                )

    # Check channel permissions
    if chat.get('chat_type') == ChatType.CHANNEL and chat.get('only_admins_can_post', False):
        if current_user['id'] not in chat.get('admins', []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can post in this channel"
            )
    
    # Validate reply_to message exists and belongs to this chat
    if message_data.reply_to:
        reply_msg = await get_message_by_id(message_data.reply_to)
        if not reply_msg or reply_msg['chat_id'] != chat_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reply_to message"
            )
    
    # Create message
    message_id = str(uuid.uuid4())
    message_dict = message_data.dict()
    message_dict.update({
        'id': message_id,
        'sender_id': current_user['id'],
        'chat_id': chat_id,
        'status': 'sent',
        'delivered_to': [],
        'read_by': [current_user['id']],  # Mark as read by sender
        'reactions': {},
        'edited': False,
        'deleted': False,
        'created_at': utc_now(),
        'updated_at': utc_now()
    })
    
    await create_message(message_dict)
    
    # Get sender details
    sender = await get_user_by_id(current_user['id'])
    sender_response = UserResponse(
        id=sender['id'],
        username=sender['username'],
        display_name=sender['display_name'],
        avatar=sender.get('avatar'),
        bio=sender.get('bio'),
        phone_number=sender.get('phone_number'),
        email=sender.get('email'),
        role=sender.get('role', 'regular'),
        is_online=sender.get('is_online', False),
        last_seen=sender.get('last_seen'),
        created_at=sender['created_at']
    )
    
    response = MessageResponse(**message_dict)
    response.sender = sender_response
    
    # Add reply_to_message context if replying
    if message_dict.get('reply_to'):
        reply_msg = await get_message_by_id(message_dict['reply_to'])
        if reply_msg:
            response.reply_to_message = {
                'id': reply_msg['id'],
                'content': reply_msg['content'],
                'sender_id': reply_msg['sender_id'],
                'created_at': reply_msg['created_at'].isoformat() if isinstance(reply_msg['created_at'], datetime) else reply_msg['created_at']
            }
    
    # Update chat's last_message
    db = Database.get_db()
    await db.chats.update_one(
        {'id': chat_id},
        {
            '$set': {
                'last_message': {
                    'id': message_id,
                    'content': message_dict['content'],
                    'message_type': message_dict['message_type'],
                    'sender_id': current_user['id'],
                    'created_at': message_dict['created_at']
                },
                'updated_at': utc_now()
            }
        }
    )
    
    # Broadcast message via Socket.IO - serialize datetime objects to ISO strings
    message_data_json = response.model_dump(mode='json')
    await socket_manager.send_message_to_chat(chat_id, message_data_json)
    
    return response

@router.put("/messages/{message_id}")
async def edit_message(
    message_id: str,
    content: str,
    current_user: dict = Depends(get_current_user)
):
    """Edit a message (within 48 hours)"""
    message = await get_message_by_id(message_id)
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    if message['sender_id'] != current_user['id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only edit your own messages"
        )
    
    # Check if message is not too old (48 hours)
    # Ensure created_at is timezone-aware for comparison
    created_at = message['created_at']
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    message_age = utc_now() - created_at
    if message_age > timedelta(hours=48):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message is too old to edit (48-hour limit)"
        )
    
    await update_message(message_id, {
        'content': content,
        'edited': True,
        'updated_at': utc_now()
    })
    
    # Broadcast update via Socket.IO
    await socket_manager.broadcast_message_edited(message['chat_id'], message_id, content)
    
    return {"message": "Message updated"}

@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: str,
    for_everyone: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """Delete a message"""
    message = await get_message_by_id(message_id)
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    if for_everyone:
        # Only sender can delete for everyone
        if message['sender_id'] != current_user['id']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only delete your own messages for everyone"
            )
        
        # Delete for everyone
        await update_message(message_id, {'deleted': True, 'content': 'This message was deleted'})
        
        # Broadcast deletion
        await socket_manager.broadcast_message_deleted(message['chat_id'], message_id)
    else:
        # Delete for me only - add current user to deleted_for list
        deleted_for = message.get('deleted_for', [])
        if current_user['id'] not in deleted_for:
            deleted_for.append(current_user['id'])
            await update_message(message_id, {'deleted_for': deleted_for})
    
    return {"message": "Message deleted"}

@router.post("/messages/{message_id}/react")
async def add_reaction(
    message_id: str,
    reaction_data: ReactionCreate,
    current_user: dict = Depends(get_current_user)
):
    """Add or update reaction to a message (only one reaction per user)"""
    message = await get_message_by_id(message_id)
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Get current reactions
    reactions = message.get('reactions', {})
    emoji = reaction_data.emoji
    user_id = current_user['id']
    
    # Check if user already has this exact emoji (toggle off)
    user_has_this_emoji = emoji in reactions and user_id in reactions[emoji]
    
    # Remove user's existing reaction if any
    removed_emoji = None
    for existing_emoji, users in list(reactions.items()):
        if user_id in users:
            users.remove(user_id)
            removed_emoji = existing_emoji
            if not users:
                del reactions[existing_emoji]
            
            # Broadcast removal of old reaction
            await socket_manager.broadcast_reaction(message['chat_id'], {
                'message_id': message_id,
                'emoji': existing_emoji,
                'user_id': user_id,
                'action': 'remove',
                'reactions': reactions,
                'chat_id': message['chat_id']
            })
            print(f"🗑️ Removed reaction {existing_emoji} from user {user_id}")
            break
    
    # If user clicked the same emoji they already had, just remove it (toggle off)
    if user_has_this_emoji:
        await update_message(message_id, {'reactions': reactions})
        print(f"✅ Toggled OFF reaction {emoji} for user {user_id}")
        return {"message": "Reaction removed", "reactions": reactions}
    
    # Add new reaction (only if it wasn't a toggle-off)
    if emoji not in reactions:
        reactions[emoji] = []
    
    if user_id not in reactions[emoji]:
        reactions[emoji].append(user_id)
    
    # Update message
    await update_message(message_id, {'reactions': reactions})
    
    print(f"✅ Added reaction {emoji} for user {user_id}")
    
    # Broadcast new reaction
    await socket_manager.broadcast_reaction(message['chat_id'], {
        'message_id': message_id,
        'emoji': emoji,
        'user_id': user_id,
        'action': 'add',
        'reactions': reactions,
        'chat_id': message['chat_id']
    })
    
    return {"message": "Reaction added", "reactions": reactions}

@router.delete("/messages/{message_id}/react")
async def remove_reaction(
    message_id: str,
    emoji: str = Query(...),
    current_user: dict = Depends(get_current_user)
):
    """Remove reaction from a message"""
    message = await get_message_by_id(message_id)
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Update reactions
    reactions = message.get('reactions', {})
    
    if emoji in reactions and current_user['id'] in reactions[emoji]:
        reactions[emoji].remove(current_user['id'])
        if not reactions[emoji]:
            del reactions[emoji]
    
    await update_message(message_id, {'reactions': reactions})
    
    # Broadcast reaction removal
    await socket_manager.broadcast_reaction(message['chat_id'], {
        'message_id': message_id,
        'emoji': emoji,
        'user_id': current_user['id'],
        'action': 'remove',
        'reactions': reactions,
        'chat_id': message['chat_id']
    })
    
    return {"message": "Reaction removed", "reactions": reactions}

@router.post("/messages/{message_id}/read")
async def mark_as_read(
    message_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Mark message as read"""
    message = await get_message_by_id(message_id)
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Update read status
    read_by = message.get('read_by', [])
    if current_user['id'] not in read_by:
        read_by.append(current_user['id'])
        await update_message(message_id, {'read_by': read_by, 'status': 'read'})
        
        # Broadcast read status
        await socket_manager.update_message_status(
            message['chat_id'],
            message_id,
            'read',
            current_user['id']
        )
    
    return {"message": "Marked as read"}

@router.post("/messages/{message_id}/pin")
async def pin_message(
    message_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Pin a message in chat (admin only)"""
    message = await get_message_by_id(message_id)
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    chat = await get_chat_by_id(message['chat_id'])
    
    # Check if user is admin
    if current_user['id'] not in chat.get('admins', []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can pin messages"
        )
    
    # Add message to pinned list
    pinned = chat.get('pinned_messages', [])
    if message_id not in pinned:
        pinned.append(message_id)
        
        db = Database.get_db()
        await db.chats.update_one(
            {"id": message['chat_id']},
            {"$set": {"pinned_messages": pinned, "updated_at": utc_now()}}
        )
        
        # Broadcast pin event
        await socket_manager.broadcast_message_pinned(
            message['chat_id'], 
            message_id, 
            current_user['id']
        )
    
    return {"message": "Message pinned"}

@router.delete("/messages/{message_id}/pin")
async def unpin_message(
    message_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Unpin a message from chat (admin only)"""
    message = await get_message_by_id(message_id)
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    chat = await get_chat_by_id(message['chat_id'])
    
    # Check if user is admin
    if current_user['id'] not in chat.get('admins', []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can unpin messages"
        )
    
    # Remove message from pinned list
    pinned = chat.get('pinned_messages', [])
    if message_id in pinned:
        pinned.remove(message_id)
        
        db = Database.get_db()
        await db.chats.update_one(
            {"id": message['chat_id']},
            {"$set": {"pinned_messages": pinned, "updated_at": utc_now()}}
        )
        
        # Broadcast unpin event
        await socket_manager.broadcast_message_unpinned(
            message['chat_id'], 
            message_id, 
            current_user['id']
        )
    
    return {"message": "Message unpinned"}

@router.post("/{chat_id}/forward")
async def forward_messages(
    chat_id: str,
    message_ids: List[str] = Query(...),
    from_chat_id: str = Query(...),
    current_user: dict = Depends(get_current_user)
):
    """Forward one or more messages to another chat"""
    # Verify target chat
    target_chat = await get_chat_by_id(chat_id)
    if not target_chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target chat not found"
        )
    
    if current_user['id'] not in target_chat['participants']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a participant of target chat"
        )
    
    # Verify source chat
    source_chat = await get_chat_by_id(from_chat_id)
    if not source_chat or current_user['id'] not in source_chat['participants']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot forward from this chat"
        )
    
    # Forward each message
    forwarded_messages = []
    
    for msg_id in message_ids:
        original_msg = await get_message_by_id(msg_id)
        if not original_msg or original_msg['chat_id'] != from_chat_id:
            continue
        
        # Create forwarded message
        new_msg_id = str(uuid.uuid4())
        message_dict = {
            'id': new_msg_id,
            'chat_id': chat_id,
            'sender_id': current_user['id'],
            'content': original_msg['content'],
            'message_type': original_msg['message_type'],
            'forwarded_from': msg_id,
            'media_url': original_msg.get('media_url'),
            'file_name': original_msg.get('file_name'),
            'file_size': original_msg.get('file_size'),
            'status': 'sent',
            'delivered_to': [],
            'read_by': [current_user['id']],
            'reactions': {},
            'edited': False,
            'deleted': False,
            'created_at': utc_now(),
            'updated_at': utc_now()
        }
        
        await create_message(message_dict)
        forwarded_messages.append(new_msg_id)
        
        # Get sender info for response
        sender = await get_user_by_id(current_user['id'])
        sender_response = UserResponse(
            id=sender['id'],
            username=sender['username'],
            display_name=sender['display_name'],
            avatar=sender.get('avatar'),
            bio=sender.get('bio'),
            phone_number=sender.get('phone_number'),
            email=sender.get('email'),
            role=sender.get('role', 'regular'),
            is_online=sender.get('is_online', False),
            last_seen=sender.get('last_seen'),
            created_at=sender['created_at']
        )
        
        response = MessageResponse(**message_dict)
        response.sender = sender_response
        
        # Broadcast forwarded message - serialize datetime objects to ISO strings
        message_data_json = response.model_dump(mode='json')
        await socket_manager.send_message_to_chat(chat_id, message_data_json)
    
    # Broadcast forward event summary
    if forwarded_messages:
        await socket_manager.broadcast_messages_forwarded(
            chat_id,
            forwarded_messages,
            current_user['id']
        )
    
    return {
        "message": f"Forwarded {len(forwarded_messages)} messages",
        "forwarded_ids": forwarded_messages
    }

@router.put("/{chat_id}", response_model=ChatResponse)
async def update_chat(
    chat_id: str,
    chat_update: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update chat info (name, description, avatar, settings)"""
    chat = await get_chat_by_id(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
        
    if chat['chat_type'] == ChatType.DIRECT:
        raise HTTPException(status_code=400, detail="Cannot update direct chat info")
        
    if current_user['id'] not in chat.get('admins', []):
        raise HTTPException(status_code=403, detail="Only admins can update chat info")
        
    db = Database.get_db()
    
    # Filter allowed fields
    allowed_fields = ['name', 'description', 'avatar', 'is_public', 'only_admins_can_post']
    update_data = {k: v for k, v in chat_update.items() if k in allowed_fields}
    update_data['updated_at'] = utc_now()
    
    await db.chats.update_one(
        {'id': chat_id},
        {'$set': update_data}
    )
    
    updated_chat = await get_chat_by_id(chat_id)
    return ChatResponse(**updated_chat)

@router.post("/{chat_id}/participants", response_model=ChatResponse)
async def add_participants(
    chat_id: str,
    user_ids: List[str],
    current_user: dict = Depends(get_current_user)
):
    """Add participants to a group/channel"""
    chat = await get_chat_by_id(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
        
    if chat['chat_type'] == ChatType.DIRECT:
        raise HTTPException(status_code=400, detail="Cannot add participants to direct chat")
        
    # Check permissions (admins only for private groups/channels usually, but let's say admins for now)
    if current_user['id'] not in chat.get('admins', []):
        # If public group, maybe anyone can add? Let's stick to admins for now for safety
        raise HTTPException(status_code=403, detail="Only admins can add participants")
        
    db = Database.get_db()
    
    # Filter valid users
    users = await db.users.find({'id': {'$in': user_ids}}).to_list(None)
    valid_user_ids = [u['id'] for u in users]
    
    await db.chats.update_one(
        {'id': chat_id},
        {'$addToSet': {'participants': {'$each': valid_user_ids}}}
    )
    
    updated_chat = await get_chat_by_id(chat_id)
    updated_chat_response = ChatResponse(**updated_chat)
    
    # Notify new participants via socket
    response_dict = updated_chat_response.model_dump(mode='json')
    for user_id in valid_user_ids:
        await socket_manager.send_message_to_user(
            user_id,
            'added_to_chat',
            {
                'chat': response_dict
            }
        )
    
    # Notify existing members via socket
    for participant_id in chat['participants']:
        if participant_id not in valid_user_ids:
            await socket_manager.send_message_to_user(
                participant_id,
                'participants_added',
                {
                    'chat_id': chat_id,
                    'new_participants': valid_user_ids
                }
            )
    
    return updated_chat_response

@router.delete("/{chat_id}/participants/{user_id}", response_model=ChatResponse)
async def remove_participant(
    chat_id: str,
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove participant from group/channel"""
    chat = await get_chat_by_id(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
        
    if chat['chat_type'] == ChatType.DIRECT:
        raise HTTPException(status_code=400, detail="Cannot remove participants from direct chat")
        
    # Admins can remove anyone, users can remove themselves (leave)
    if current_user['id'] != user_id and current_user['id'] not in chat.get('admins', []):
        raise HTTPException(status_code=403, detail="Not authorized to remove this participant")
        
    db = Database.get_db()
    
    await db.chats.update_one(
        {'id': chat_id},
        {'$pull': {'participants': user_id, 'admins': user_id}}
    )
    
    updated_chat = await get_chat_by_id(chat_id)
    
    # Notify removed user via socket
    await socket_manager.send_message_to_user(user_id, 'removed_from_chat', {
        'chat_id': chat_id
    })
    
    # Notify remaining participants via socket
    response_dict = ChatResponse(**updated_chat).dict()
    for participant_id in updated_chat['participants']:
        await socket_manager.send_message_to_user(participant_id, 'participant_removed', {
            'chat': response_dict,
            'removed_user_id': user_id
        })
    
    return ChatResponse(**updated_chat)

@router.post("/{chat_id}/admins/{user_id}", response_model=ChatResponse)
async def promote_admin(
    chat_id: str,
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Promote participant to admin"""
    chat = await get_chat_by_id(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
        
    if chat['chat_type'] == ChatType.DIRECT:
        raise HTTPException(status_code=400, detail="Not applicable for direct chats")
        
    if current_user['id'] not in chat.get('admins', []):
        raise HTTPException(status_code=403, detail="Only admins can promote others")
        
    if user_id not in chat['participants']:
        raise HTTPException(status_code=400, detail="User is not a participant")
        
    db = Database.get_db()
    
    await db.chats.update_one(
        {'id': chat_id},
        {'$addToSet': {'admins': user_id}}
    )
    
    updated_chat = await get_chat_by_id(chat_id)
    
    # Notify promoted user via socket
    await socket_manager.send_message_to_user(user_id, 'promoted_to_admin', {
        'chat_id': chat_id
    })
    
    # Notify all other participants via socket
    response_dict = ChatResponse(**updated_chat).dict()
    for participant_id in updated_chat['participants']:
        if participant_id != user_id:
            await socket_manager.send_message_to_user(participant_id, 'participant_promoted', {
                'chat': response_dict,
                'promoted_user_id': user_id
            })
    
    return ChatResponse(**updated_chat)

@router.delete("/{chat_id}/admins/{user_id}", response_model=ChatResponse)
async def demote_admin(
    chat_id: str,
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Demote admin to regular participant"""
    chat = await get_chat_by_id(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
        
    if chat['chat_type'] == ChatType.DIRECT:
        raise HTTPException(status_code=400, detail="Not applicable for direct chats")
        
    if current_user['id'] not in chat.get('admins', []):
        raise HTTPException(status_code=403, detail="Only admins can demote others")
        
    if user_id == current_user['id']:
        # Prevent removing self if last admin?
        if len(chat.get('admins', [])) == 1:
            raise HTTPException(status_code=400, detail="Cannot remove the last admin")
            
    db = Database.get_db()
    
    await db.chats.update_one(
        {'id': chat_id},
        {'$pull': {'admins': user_id}}
    )
    
    updated_chat = await get_chat_by_id(chat_id)
    
    # Notify demoted user via socket
    await socket_manager.send_message_to_user(user_id, 'demoted_from_admin', {
        'chat_id': chat_id
    })
    
    # Notify all other participants via socket
    response_dict = ChatResponse(**updated_chat).dict()
    for participant_id in updated_chat['participants']:
        if participant_id != user_id:
            await socket_manager.send_message_to_user(participant_id, 'participant_demoted', {
                'chat': response_dict,
                'demoted_user_id': user_id
            })
    
    return ChatResponse(**updated_chat)
