from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional
import uuid
from datetime import datetime
import logging
import secrets

from models_enhanced import (
    ChatCreate, ChatResponse, MessageCreate, MessageResponse,
    MessageType, ChatType, UserResponse, ReactionCreate, ReactionRemove,
    SearchResult, JoinRequest, InviteRequest, UpdatePermissionsRequest,
    BanUserRequest, ChatMember, AdminRights, ChatPermissions
)
from auth import get_current_user
from database_enhanced import (
    Database, get_chat_by_id, get_user_chats, create_chat,
    get_chat_messages, create_message, get_message_by_id,
    update_message, get_user_by_id, get_users_by_ids, search_global,
    add_chat_member, remove_chat_member, add_channel_subscriber,
    remove_channel_subscriber, ban_user_from_chat, unban_user_from_chat,
    is_user_banned, get_member_role, update_member_role, get_chat_by_username,
    update_chat
)
from permissions import (
    check_chat_exists, check_user_in_chat, check_can_send_message,
    check_can_send_media, check_can_edit_message, check_can_delete_message,
    check_can_add_members, check_can_remove_member, check_can_change_info,
    check_can_pin_messages, check_can_ban_users, check_can_promote_to_admin,
    check_is_owner, check_is_admin, check_not_banned, get_user_effective_permissions,
    get_default_admin_permissions, get_channel_default_permissions, PermissionError,
    check_can_message_user, check_are_friends
)
from socket_manager import socket_manager
from utils import utc_now

router = APIRouter(prefix="/chats", tags=["Chats & Channels"])
logger = logging.getLogger(__name__)

# ============ Search ============

@router.get("/search", response_model=List[SearchResult])
async def search_everything(
    q: str = Query(..., min_length=2),
    current_user: dict = Depends(get_current_user)
):
    """Search users, groups, and public channels"""
    results = await search_global(q, current_user['id'])
    return results

# ============ Chat Creation ============

@router.post("/", response_model=ChatResponse)
async def create_new_chat(
    chat_data: ChatCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a direct chat, group, or channel"""
    
    chat_id = str(uuid.uuid4())
    created_at = utc_now()
    
    if chat_data.chat_type == ChatType.DIRECT:
        # Direct chat logic
        if len(chat_data.participant_ids) != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Direct chat must have exactly one other participant"
            )
        
        other_user_id = chat_data.participant_ids[0]
        
        # Check if users are friends
        if not await check_are_friends(current_user['id'], other_user_id):
            raise PermissionError("You can only create direct chats with friends")
        
        # Check if direct chat already exists
        db = Database.get_db()
        existing_chat = await db.chats.find_one({
            'chat_type': 'direct',
            'members.user_id': {'$all': [current_user['id'], other_user_id]}
        })
        
        if existing_chat:
            # Return existing chat
            return await get_chat(existing_chat['id'], current_user)
        
        # Create direct chat
        members = [
            {
                "user_id": current_user['id'],
                "role": "member",
                "joined_at": created_at
            },
            {
                "user_id": other_user_id,
                "role": "member",
                "joined_at": created_at
            }
        ]
        
        chat_dict = {
            'id': chat_id,
            'chat_type': 'direct',
            'created_by': current_user['id'],
            'owner_id': current_user['id'],
            'members': members,
            'subscribers': [],
            'admins': [],
            'banned_users': [],
            'member_count': 2,
            'subscriber_count': 0,
            'pinned_messages': [],
            'created_at': created_at,
            'updated_at': created_at
        }
    
    elif chat_data.chat_type == ChatType.GROUP:
        # Group logic
        if not chat_data.name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Group name is required"
            )
        
        # Create members list
        members = [{
            "user_id": current_user['id'],
            "role": "owner",
            "joined_at": created_at
        }]
        
        # Add initial members
        for user_id in chat_data.participant_ids:
            if user_id != current_user['id']:
                members.append({
                    "user_id": user_id,
                    "role": "member",
                    "joined_at": created_at
                })
        
        # Generate invite link
        invite_link = f"https://chatapp.com/join/{secrets.token_urlsafe(16)}"
        
        chat_dict = {
            'id': chat_id,
            'chat_type': 'group',
            'name': chat_data.name,
            'description': chat_data.description,
            'avatar': None,
            'is_public': chat_data.is_public,
            'username': chat_data.username if chat_data.is_public else None,
            'invite_link': invite_link,
            'created_by': current_user['id'],
            'owner_id': current_user['id'],
            'members': members,
            'subscribers': [],
            'admins': [],
            'banned_users': [],
            'member_count': len(members),
            'subscriber_count': 0,
            'max_members': 200000,
            'default_permissions': ChatPermissions().dict(),
            'pinned_messages': [],
            'created_at': created_at,
            'updated_at': created_at
        }
    
    elif chat_data.chat_type == ChatType.CHANNEL:
        # Channel logic
        if not chat_data.name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Channel name is required"
            )
        
        # Generate invite link
        invite_link = f"https://chatapp.com/channel/{secrets.token_urlsafe(16)}"
        
        chat_dict = {
            'id': chat_id,
            'chat_type': 'channel',
            'name': chat_data.name,
            'description': chat_data.description,
            'avatar': None,
            'is_public': chat_data.is_public,
            'username': chat_data.username if chat_data.is_public else None,
            'invite_link': invite_link,
            'created_by': current_user['id'],
            'owner_id': current_user['id'],
            'members': [],  # Channels don't have "members", only subscribers
            'subscribers': [current_user['id']],  # Owner is auto-subscribed
            'admins': [],
            'banned_users': [],
            'member_count': 0,
            'subscriber_count': 1,
            'pinned_messages': [],
            'created_at': created_at,
            'updated_at': created_at
        }
    
    await create_chat(chat_dict)
    
    # Get full response
    return await get_chat(chat_id, current_user)

# ============ Get Chats ============

@router.get("/", response_model=List[ChatResponse])
async def get_chats(current_user: dict = Depends(get_current_user)):
    """Get all chats for current user"""
    chats = await get_user_chats(current_user['id'])
    
    # Collect all unique participant IDs
    all_participant_ids = set()
    for chat in chats:
        all_participant_ids.update([m['user_id'] for m in chat.get('members', [])])
        all_participant_ids.update(chat.get('subscribers', []))
    
    # Batch fetch all users
    users_list = await get_users_by_ids(list(all_participant_ids))
    users_map = {user['id']: user for user in users_list}
    
    result = []
    for chat in chats:
        # Get participant details
        participants_details = []
        
        if chat['chat_type'] == 'channel':
            # For channels, don't expose subscriber list
            pass
        else:
            # For direct chats and groups, show participants
            participant_ids = [m['user_id'] for m in chat.get('members', [])]
            for participant_id in participant_ids:
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
        
        # Get user's permissions
        perms = await get_user_effective_permissions(chat['id'], current_user['id'])
        
        chat_response = ChatResponse(**chat)
        chat_response.participant_details = participants_details
        chat_response.unread_count = unread_count
        chat_response.my_role = perms.get('role')
        chat_response.can_send_messages = perms.get('can_send_messages', False)
        result.append(chat_response)
    
    return result

@router.get("/{chat_id}", response_model=ChatResponse)
async def get_chat(
    chat_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get chat by ID"""
    chat = await check_user_in_chat(chat_id, current_user['id'])
    
    # Get participant details
    participants_details = []
    
    if chat['chat_type'] != 'channel':
        participant_ids = [m['user_id'] for m in chat.get('members', [])]
        users_list = await get_users_by_ids(participant_ids)
        
        for user in users_list:
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
    
    # Get user's permissions
    perms = await get_user_effective_permissions(chat_id, current_user['id'])
    
    chat_response = ChatResponse(**chat)
    chat_response.participant_details = participants_details
    chat_response.my_role = perms.get('role')
    chat_response.can_send_messages = perms.get('can_send_messages', False)
    
    return chat_response

# ============ Join/Leave ============

@router.post("/{chat_id}/join")
async def join_chat(
    chat_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Join a public group or channel"""
    chat = await check_chat_exists(chat_id)
    
    if not chat['is_public']:
        raise PermissionError("This chat is private")
    
    # Check if not banned
    await check_not_banned(chat_id, current_user['id'])
    
    # Check if already member
    if chat['chat_type'] == 'channel':
        if current_user['id'] in chat.get('subscribers', []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already subscribed"
            )
        await add_channel_subscriber(chat_id, current_user['id'])
    else:
        member_ids = [m['user_id'] for m in chat.get('members', [])]
        if current_user['id'] in member_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already a member"
            )
        
        member_data = {
            "user_id": current_user['id'],
            "role": "member",
            "joined_at": utc_now()
        }
        await add_chat_member(chat_id, member_data)
        
        # Send system message
        system_msg = {
            'id': str(uuid.uuid4()),
            'chat_id': chat_id,
            'sender_id': 'system',
            'content': f"{current_user['display_name']} joined the group",
            'message_type': 'system',
            'status': 'sent',
            'delivered_to': [],
            'read_by': [],
            'reactions': {},
            'edited': False,
            'deleted': False,
            'views': 0,
            'created_at': utc_now(),
            'updated_at': utc_now()
        }
        await create_message(system_msg)
    
    return {"message": "Joined successfully"}

@router.post("/{chat_id}/leave")
async def leave_chat(
    chat_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Leave a group or channel"""
    chat = await check_user_in_chat(chat_id, current_user['id'])
    
    if chat['chat_type'] == 'direct':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot leave direct chats"
        )
    
    if chat['owner_id'] == current_user['id']:
        raise PermissionError("Owner cannot leave. Transfer ownership or delete the chat.")
    
    if chat['chat_type'] == 'channel':
        await remove_channel_subscriber(chat_id, current_user['id'])
    else:
        await remove_chat_member(chat_id, current_user['id'])
        
        # Send system message
        system_msg = {
            'id': str(uuid.uuid4()),
            'chat_id': chat_id,
            'sender_id': 'system',
            'content': f"{current_user['display_name']} left the group",
            'message_type': 'system',
            'status': 'sent',
            'delivered_to': [],
            'read_by': [],
            'reactions': {},
            'edited': False,
            'deleted': False,
            'views': 0,
            'created_at': utc_now(),
            'updated_at': utc_now()
        }
        await create_message(system_msg)
    
    return {"message": "Left successfully"}

# ============ Messages ============

@router.get("/{chat_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    chat_id: str,
    limit: int = Query(default=50, le=100),
    skip: int = Query(default=0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """Get messages for a chat"""
    await check_user_in_chat(chat_id, current_user['id'])
    
    messages = await get_chat_messages(chat_id, limit, skip)
    
    # Batch fetch all unique senders
    sender_ids = list(set(msg['sender_id'] for msg in messages if msg['sender_id'] != 'system'))
    senders_list = await get_users_by_ids(sender_ids)
    senders_map = {user['id']: user for user in senders_list}
    
    result = []
    for msg in messages:
        sender_response = None
        if msg['sender_id'] != 'system':
            sender = senders_map.get(msg['sender_id'])
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
    await check_can_send_message(chat_id, current_user['id'])
    
    # Check media permissions if sending media
    if message_data.message_type in ['image', 'video', 'audio', 'file', 'voice']:
        await check_can_send_media(chat_id, current_user['id'])
    
    # Create message
    message_id = str(uuid.uuid4())
    message_dict = message_data.dict()
    message_dict.update({
        'id': message_id,
        'sender_id': current_user['id'],
        'chat_id': chat_id,
        'status': 'sent',
        'delivered_to': [],
        'read_by': [current_user['id']],
        'reactions': {},
        'edited': False,
        'deleted': False,
        'views': 0,
        'created_at': utc_now(),
        'updated_at': utc_now()
    })
    
    await create_message(message_dict)
    
    # Get sender details
    sender_response = UserResponse(
        id=current_user['id'],
        username=current_user['username'],
        display_name=current_user['display_name'],
        avatar=current_user.get('avatar'),
        bio=current_user.get('bio'),
        phone_number=current_user.get('phone_number'),
        email=current_user.get('email'),
        role=current_user.get('role', 'regular'),
        is_online=current_user.get('is_online', False),
        last_seen=current_user.get('last_seen'),
        created_at=current_user['created_at']
    )
    
    response = MessageResponse(**message_dict)
    response.sender = sender_response
    
    # Broadcast via Socket.IO
    await socket_manager.send_message_to_chat(chat_id, response.dict())
    
    return response

# ============ Admin Operations ============

@router.post("/{chat_id}/invite")
async def invite_users(
    chat_id: str,
    invite_data: InviteRequest,
    current_user: dict = Depends(get_current_user)
):
    """Invite users to a group or channel (admin only)"""
    await check_can_add_members(chat_id, current_user['id'])
    chat = await get_chat_by_id(chat_id)
    
    for user_id in invite_data.user_ids:
        # Check if user exists
        user = await get_user_by_id(user_id)
        if not user:
            continue
        
        # Check if not banned
        if await is_user_banned(chat_id, user_id):
            continue
        
        if chat['chat_type'] == 'channel':
            if user_id not in chat.get('subscribers', []):
                await add_channel_subscriber(chat_id, user_id)
        else:
            member_ids = [m['user_id'] for m in chat.get('members', [])]
            if user_id not in member_ids:
                member_data = {
                    "user_id": user_id,
                    "role": "member",
                    "joined_at": utc_now()
                }
                await add_chat_member(chat_id, member_data)
    
    return {"message": "Users invited"}

@router.post("/{chat_id}/ban")
async def ban_user(
    chat_id: str,
    ban_data: BanUserRequest,
    current_user: dict = Depends(get_current_user)
):
    """Ban a user from group/channel"""
    await check_can_ban_users(chat_id, current_user['id'], ban_data.user_id)
    
    banned_user_data = {
        "user_id": ban_data.user_id,
        "banned_by": current_user['id'],
        "banned_at": utc_now(),
        "reason": ban_data.reason,
        "until_date": ban_data.until_date
    }
    
    await ban_user_from_chat(chat_id, banned_user_data)
    
    return {"message": "User banned"}

@router.post("/{chat_id}/unban/{user_id}")
async def unban_user(
    chat_id: str,
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Unban a user"""
    await check_can_ban_users(chat_id, current_user['id'], user_id)
    
    await unban_user_from_chat(chat_id, user_id)
    
    return {"message": "User unbanned"}

@router.post("/{chat_id}/promote/{user_id}")
async def promote_to_admin(
    chat_id: str,
    user_id: str,
    permissions: List[str] = Query(default=None),
    current_user: dict = Depends(get_current_user)
):
    """Promote a member to admin"""
    await check_can_promote_to_admin(chat_id, current_user['id'])
    
    # Get default permissions if none provided
    chat = await get_chat_by_id(chat_id)
    if not permissions:
        if chat['chat_type'] == 'channel':
            permissions = get_channel_default_permissions()
        else:
            permissions = get_default_admin_permissions()
    
    admin_rights = {
        "permissions": permissions,
        "custom_title": None
    }
    
    await update_member_role(chat_id, user_id, 'admin', admin_rights)
    
    return {"message": "User promoted to admin"}

@router.post("/{chat_id}/demote/{user_id}")
async def demote_admin(
    chat_id: str,
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Demote an admin to regular member"""
    await check_can_promote_to_admin(chat_id, current_user['id'])
    
    await update_member_role(chat_id, user_id, 'member', None)
    
    return {"message": "Admin demoted"}

# Keep other message endpoints (edit, delete, reactions) from original file
# ... (previous implementation)
