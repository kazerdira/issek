"""
Permission checking system for chat application.
Implements Telegram-like permission logic.
"""

from typing import Optional, List
from fastapi import HTTPException, status
from database import (
    get_chat_by_id, get_member_role, is_user_banned,
    is_blocked_by_any, get_user_by_id
)

class PermissionError(HTTPException):
    """Custom exception for permission errors"""
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )

# ============ Permission Constants ============
ALL_ADMIN_PERMISSIONS = [
    "can_change_info",
    "can_delete_messages",
    "can_ban_users",
    "can_invite_users",
    "can_pin_messages",
    "can_add_admins",
    "can_post",
    "can_edit_messages",
    "can_restrict_members"
]

# ============ User-Level Permission Checks ============

async def check_are_friends(user1_id: str, user2_id: str) -> bool:
    """Check if two users are friends"""
    user1 = await get_user_by_id(user1_id)
    if not user1:
        return False
    return user2_id in user1.get('friends', [])

async def check_can_message_user(from_user_id: str, to_user_id: str):
    """Check if user can send direct message to another user"""
    # Check if blocked
    if await is_blocked_by_any(from_user_id, to_user_id):
        raise PermissionError("You cannot message this user")
    
    # Check if friends
    if not await check_are_friends(from_user_id, to_user_id):
        raise PermissionError("You can only message friends. Send a friend request first.")
    
    return True

async def check_can_send_friend_request(from_user_id: str, to_user_id: str):
    """Check if user can send friend request"""
    # Check if blocked
    if await is_blocked_by_any(from_user_id, to_user_id):
        raise PermissionError("You cannot send a friend request to this user")
    
    # Check if already friends
    if await check_are_friends(from_user_id, to_user_id):
        raise PermissionError("You are already friends with this user")
    
    return True

# ============ Chat-Level Permission Checks ============

async def check_chat_exists(chat_id: str):
    """Check if chat exists"""
    chat = await get_chat_by_id(chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    return chat

async def check_user_in_chat(chat_id: str, user_id: str):
    """Check if user is a member/subscriber of chat"""
    chat = await check_chat_exists(chat_id)
    
    if chat['chat_type'] == 'channel':
        if user_id not in chat.get('subscribers', []):
            raise PermissionError("You are not subscribed to this channel")
    else:
        # Group or direct chat
        member_ids = [m['user_id'] for m in chat.get('members', [])]
        if user_id not in member_ids:
            raise PermissionError("You are not a member of this chat")
    
    return chat

async def check_not_banned(chat_id: str, user_id: str):
    """Check if user is not banned from chat"""
    if await is_user_banned(chat_id, user_id):
        raise PermissionError("You are banned from this chat")
    return True

async def check_is_owner(chat_id: str, user_id: str):
    """Check if user is the owner of chat"""
    chat = await check_chat_exists(chat_id)
    if chat['owner_id'] != user_id:
        raise PermissionError("Only the owner can perform this action")
    return chat

async def check_is_admin(chat_id: str, user_id: str):
    """Check if user is admin or owner"""
    chat = await check_chat_exists(chat_id)
    
    # Owner has all permissions
    if chat['owner_id'] == user_id:
        return chat, "owner"
    
    # Check if in admins list
    if user_id in chat.get('admins', []):
        role_data = await get_member_role(chat_id, user_id)
        return chat, role_data['role']
    
    raise PermissionError("You need to be an admin to perform this action")

async def check_has_permission(chat_id: str, user_id: str, permission: str):
    """Check if user has specific permission"""
    chat = await check_chat_exists(chat_id)
    
    # Owner has all permissions
    if chat['owner_id'] == user_id:
        return chat
    
    # Get user's role and permissions
    role_data = await get_member_role(chat_id, user_id)
    
    if not role_data or role_data['role'] != 'admin':
        raise PermissionError(f"You need '{permission}' permission to perform this action")
    
    # Check if admin has this permission
    admin_rights = role_data.get('permissions')
    if not admin_rights:
        raise PermissionError(f"You don't have '{permission}' permission")
    
    if isinstance(admin_rights, dict):
        permissions_list = admin_rights.get('permissions', [])
        if permission not in permissions_list:
            raise PermissionError(f"You don't have '{permission}' permission")
    
    return chat

# ============ Message-Level Permission Checks ============

async def check_can_send_message(chat_id: str, user_id: str):
    """Check if user can send message in chat"""
    chat = await check_user_in_chat(chat_id, user_id)
    await check_not_banned(chat_id, user_id)
    
    chat_type = chat['chat_type']
    
    # Direct chats - always allowed if member and not blocked
    if chat_type == 'direct':
        return chat
    
    # Channels - only admins and owner can post
    if chat_type == 'channel':
        try:
            await check_is_admin(chat_id, user_id)
        except PermissionError:
            raise PermissionError("Only admins can post in this channel")
        return chat
    
    # Groups - check default permissions
    if chat_type == 'group':
        default_perms = chat.get('default_permissions', {})
        
        # Check if user has restricted permissions
        role_data = await get_member_role(chat_id, user_id)
        if role_data and role_data.get('permissions'):
            restrictions = role_data['permissions']
            if isinstance(restrictions, dict) and 'can_send_messages' in restrictions:
                if not restrictions['can_send_messages']:
                    raise PermissionError("You are restricted from sending messages")
        elif not default_perms.get('can_send_messages', True):
            # If no specific restrictions, check default
            raise PermissionError("Sending messages is disabled in this group")
    
    return chat

async def check_can_send_media(chat_id: str, user_id: str):
    """Check if user can send media in chat"""
    chat = await check_can_send_message(chat_id, user_id)
    
    if chat['chat_type'] == 'group':
        default_perms = chat.get('default_permissions', {})
        
        role_data = await get_member_role(chat_id, user_id)
        if role_data and role_data.get('permissions'):
            restrictions = role_data['permissions']
            if isinstance(restrictions, dict) and 'can_send_media' in restrictions:
                if not restrictions['can_send_media']:
                    raise PermissionError("You are restricted from sending media")
        elif not default_perms.get('can_send_media', True):
            raise PermissionError("Sending media is disabled in this group")
    
    return chat

async def check_can_edit_message(message, user_id: str):
    """Check if user can edit this message"""
    # Can only edit own messages
    if message['sender_id'] != user_id:
        # Unless they're admin with edit permission in channels
        chat = await get_chat_by_id(message['chat_id'])
        if chat['chat_type'] == 'channel':
            try:
                await check_has_permission(message['chat_id'], user_id, 'can_edit_messages')
            except PermissionError:
                raise PermissionError("You can only edit your own messages")
        else:
            raise PermissionError("You can only edit your own messages")
    
    return True

async def check_can_delete_message(message, user_id: str):
    """Check if user can delete this message"""
    chat_id = message['chat_id']
    
    # Can delete own messages
    if message['sender_id'] == user_id:
        return True
    
    # Admins with permission can delete any message
    try:
        await check_has_permission(chat_id, user_id, 'can_delete_messages')
        return True
    except PermissionError:
        raise PermissionError("You can only delete your own messages")

# ============ Group/Channel Management Permission Checks ============

async def check_can_add_members(chat_id: str, user_id: str):
    """Check if user can add members to chat"""
    chat = await check_user_in_chat(chat_id, user_id)
    
    if chat['chat_type'] == 'direct':
        raise PermissionError("Cannot add members to direct chats")
    
    # Channels - only admins
    if chat['chat_type'] == 'channel':
        await check_has_permission(chat_id, user_id, 'can_invite_users')
        return chat
    
    # Groups - check permission
    default_perms = chat.get('default_permissions', {})
    
    role_data = await get_member_role(chat_id, user_id)
    if role_data and role_data['role'] == 'admin':
        await check_has_permission(chat_id, user_id, 'can_invite_users')
        return chat
    
    if not default_perms.get('can_invite_users', False):
        raise PermissionError("Only admins can add members")
    
    return chat

async def check_can_remove_member(chat_id: str, remover_id: str, target_id: str):
    """Check if user can remove another member"""
    chat = await check_chat_exists(chat_id)
    
    # Can't remove owner
    if target_id == chat['owner_id']:
        raise PermissionError("Cannot remove the owner")
    
    # Owner can remove anyone
    if remover_id == chat['owner_id']:
        return chat
    
    # Admin can remove non-admins
    remover_role = await get_member_role(chat_id, remover_id)
    target_role = await get_member_role(chat_id, target_id)
    
    if not remover_role or remover_role['role'] != 'admin':
        raise PermissionError("Only admins can remove members")
    
    if target_role and target_role['role'] == 'admin':
        raise PermissionError("Admins cannot remove other admins")
    
    await check_has_permission(chat_id, remover_id, 'can_ban_users')
    return chat

async def check_can_change_info(chat_id: str, user_id: str):
    """Check if user can change chat info"""
    await check_has_permission(chat_id, user_id, 'can_change_info')

async def check_can_pin_messages(chat_id: str, user_id: str):
    """Check if user can pin messages"""
    await check_has_permission(chat_id, user_id, 'can_pin_messages')

async def check_can_ban_users(chat_id: str, banner_id: str, target_id: str):
    """Check if user can ban another user"""
    chat = await check_chat_exists(chat_id)
    
    # Can't ban owner
    if target_id == chat['owner_id']:
        raise PermissionError("Cannot ban the owner")
    
    # Owner can ban anyone
    if banner_id == chat['owner_id']:
        return chat
    
    # Admin can ban non-admins
    banner_role = await get_member_role(chat_id, banner_id)
    target_role = await get_member_role(chat_id, target_id)
    
    if not banner_role or banner_role['role'] != 'admin':
        raise PermissionError("Only admins can ban users")
    
    if target_role and target_role['role'] == 'admin':
        raise PermissionError("Admins cannot ban other admins")
    
    await check_has_permission(chat_id, banner_id, 'can_ban_users')
    return chat

async def check_can_promote_to_admin(chat_id: str, promoter_id: str):
    """Check if user can promote others to admin"""
    chat = await check_is_owner(chat_id, promoter_id)
    return chat

# ============ Utility Functions ============

def get_default_admin_permissions() -> List[str]:
    """Get default permissions for new admins"""
    return [
        "can_delete_messages",
        "can_ban_users",
        "can_invite_users",
        "can_pin_messages"
    ]

def get_channel_default_permissions() -> List[str]:
    """Get default permissions for channel admins"""
    return [
        "can_post",
        "can_edit_messages",
        "can_delete_messages"
    ]

async def get_user_effective_permissions(chat_id: str, user_id: str) -> dict:
    """Get user's effective permissions in a chat"""
    chat = await get_chat_by_id(chat_id)
    
    if not chat:
        return {}
    
    # Owner has all permissions
    if chat['owner_id'] == user_id:
        return {
            "role": "owner",
            "can_send_messages": True,
            "can_send_media": True,
            "can_edit_info": True,
            "can_delete_messages": True,
            "can_ban_users": True,
            "can_invite_users": True,
            "can_pin_messages": True,
            "can_add_admins": True,
            "can_post": True,
            "can_edit_messages": True
        }
    
    role_data = await get_member_role(chat_id, user_id)
    
    if not role_data:
        # Not a member
        return {}
    
    if role_data['role'] == 'admin':
        # Build permissions from admin_rights
        perms = role_data.get('permissions', {})
        if isinstance(perms, dict):
            permissions_list = perms.get('permissions', [])
            return {
                "role": "admin",
                "can_send_messages": True,
                "can_send_media": True,
                "can_change_info": "can_change_info" in permissions_list,
                "can_delete_messages": "can_delete_messages" in permissions_list,
                "can_ban_users": "can_ban_users" in permissions_list,
                "can_invite_users": "can_invite_users" in permissions_list,
                "can_pin_messages": "can_pin_messages" in permissions_list,
                "can_add_admins": "can_add_admins" in permissions_list,
                "can_post": "can_post" in permissions_list,
                "can_edit_messages": "can_edit_messages" in permissions_list
            }
    
    # Regular member
    default_perms = chat.get('default_permissions', {})
    return {
        "role": "member",
        "can_send_messages": default_perms.get('can_send_messages', True),
        "can_send_media": default_perms.get('can_send_media', True),
        "can_invite_users": default_perms.get('can_invite_users', False),
        "can_pin_messages": False,
        "can_delete_messages": False,
        "can_ban_users": False,
        "can_add_admins": False
    }
