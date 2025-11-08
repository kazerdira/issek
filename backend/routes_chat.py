from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional
import uuid
from datetime import datetime
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
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow(),
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
    
    # Batch fetch all unique senders
    sender_ids = list(set(msg['sender_id'] for msg in messages))
    db = Database.get_db()
    senders_list = await db.users.find({"id": {"$in": sender_ids}}).to_list(None)
    senders_map = {user['id']: user for user in senders_list}
    
    # Add sender details to each message
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
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
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
    
    # Broadcast message via Socket.IO
    await socket_manager.send_message_to_chat(chat_id, response.dict())
    
    return response

@router.put("/messages/{message_id}")
async def edit_message(
    message_id: str,
    content: str,
    current_user: dict = Depends(get_current_user)
):
    """Edit a message"""
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
    
    await update_message(message_id, {
        'content': content,
        'edited': True
    })
    
    # Broadcast update via Socket.IO
    await socket_manager.send_message_to_chat(message['chat_id'], {
        'event': 'message_edited',
        'message_id': message_id,
        'content': content
    })
    
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
    
    if message['sender_id'] != current_user['id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only delete your own messages"
        )
    
    if for_everyone:
        # Delete for everyone
        await update_message(message_id, {'deleted': True, 'content': 'This message was deleted'})
        
        # Broadcast deletion
        await socket_manager.send_message_to_chat(message['chat_id'], {
            'event': 'message_deleted',
            'message_id': message_id
        })
    
    return {"message": "Message deleted"}

@router.post("/messages/{message_id}/react")
async def add_reaction(
    message_id: str,
    reaction_data: ReactionCreate,
    current_user: dict = Depends(get_current_user)
):
    """Add reaction to a message"""
    message = await get_message_by_id(message_id)
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Update reactions
    reactions = message.get('reactions', {})
    emoji = reaction_data.emoji
    
    if emoji not in reactions:
        reactions[emoji] = []
    
    if current_user['id'] not in reactions[emoji]:
        reactions[emoji].append(current_user['id'])
    
    await update_message(message_id, {'reactions': reactions})
    
    # Broadcast reaction
    await socket_manager.broadcast_reaction(message['chat_id'], {
        'message_id': message_id,
        'emoji': emoji,
        'user_id': current_user['id'],
        'action': 'add'
    })
    
    return {"message": "Reaction added"}

@router.delete("/messages/{message_id}/react")
async def remove_reaction(
    message_id: str,
    reaction_data: ReactionRemove,
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
    emoji = reaction_data.emoji
    
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
        'action': 'remove'
    })
    
    return {"message": "Reaction removed"}

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
