from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
import uuid
import logging

from models_enhanced import (
    UserResponse, FriendRequestCreate, FriendRequestResponse,
    FriendRequestStatus
)
from auth import get_current_user
from database_enhanced import (
    Database, get_user_by_id, update_user, create_friend_request,
    get_friend_request, get_pending_friend_requests, get_sent_friend_requests,
    get_friend_request_by_id, update_friend_request, create_block, delete_block,
    is_blocked, is_blocked_by_any, get_users_by_ids
)
from permissions import check_can_send_friend_request, PermissionError
from socket_manager import socket_manager
from utils import utc_now

router = APIRouter(prefix="/friends", tags=["Friends"])
logger = logging.getLogger(__name__)

@router.post("/request")
async def send_friend_request(
    request_data: FriendRequestCreate,
    current_user: dict = Depends(get_current_user)
):
    """Send a friend request to another user"""
    to_user_id = request_data.to_user_id
    from_user_id = current_user['id']
    
    # Check if target user exists
    to_user = await get_user_by_id(to_user_id)
    if not to_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Permission checks
    await check_can_send_friend_request(from_user_id, to_user_id)
    
    # Check if request already exists
    existing = await get_friend_request(from_user_id, to_user_id)
    if existing:
        if existing['status'] == 'pending':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Friend request already sent"
            )
        elif existing['status'] == 'accepted':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You are already friends"
            )
    
    # Check if there's a reverse request (they sent to us)
    reverse_request = await get_friend_request(to_user_id, from_user_id)
    if reverse_request and reverse_request['status'] == 'pending':
        # Automatically accept - mutual friend request
        await update_friend_request(reverse_request['id'], {'status': 'accepted'})
        
        # Add to friends lists
        await update_user(from_user_id, {
            '$addToSet': {'friends': to_user_id},
            '$pull': {'friend_requests_received': to_user_id}
        })
        await update_user(to_user_id, {
            '$addToSet': {'friends': from_user_id},
            '$pull': {'friend_requests_sent': from_user_id}
        })
        
        # Notify via socket
        await socket_manager.send_message_to_user(to_user_id, 'friend_request_accepted', {
            'user_id': from_user_id,
            'user': UserResponse(
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
            ).dict()
        })
        
        return {"message": "Friend request accepted", "status": "accepted"}
    
    # Create new friend request
    request_id = str(uuid.uuid4())
    request_dict = {
        'id': request_id,
        'from_user_id': from_user_id,
        'to_user_id': to_user_id,
        'status': 'pending',
        'created_at': utc_now(),
        'updated_at': utc_now()
    }
    
    await create_friend_request(request_dict)
    
    # Update user records
    await update_user(from_user_id, {'$addToSet': {'friend_requests_sent': to_user_id}})
    await update_user(to_user_id, {'$addToSet': {'friend_requests_received': from_user_id}})
    
    # Notify via socket
    await socket_manager.send_message_to_user(to_user_id, 'friend_request_received', {
        'request_id': request_id,
        'from_user': UserResponse(
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
        ).dict()
    })
    
    return {"message": "Friend request sent", "request_id": request_id}

@router.post("/accept/{request_id}")
async def accept_friend_request(
    request_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Accept a friend request"""
    request = await get_friend_request_by_id(request_id)
    
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Friend request not found"
        )
    
    if request['to_user_id'] != current_user['id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This request is not for you"
        )
    
    if request['status'] != 'pending':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request already processed"
        )
    
    from_user_id = request['from_user_id']
    to_user_id = request['to_user_id']
    
    # Update request status
    await update_friend_request(request_id, {'status': 'accepted'})
    
    # Add to friends lists
    await update_user(from_user_id, {
        '$addToSet': {'friends': to_user_id},
        '$pull': {'friend_requests_sent': to_user_id}
    })
    await update_user(to_user_id, {
        '$addToSet': {'friends': from_user_id},
        '$pull': {'friend_requests_received': from_user_id}
    })
    
    # Notify sender
    await socket_manager.send_message_to_user(from_user_id, 'friend_request_accepted', {
        'user_id': to_user_id,
        'user': UserResponse(
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
        ).dict()
    })
    
    return {"message": "Friend request accepted"}

@router.post("/reject/{request_id}")
async def reject_friend_request(
    request_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Reject a friend request"""
    request = await get_friend_request_by_id(request_id)
    
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Friend request not found"
        )
    
    if request['to_user_id'] != current_user['id']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This request is not for you"
        )
    
    if request['status'] != 'pending':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request already processed"
        )
    
    from_user_id = request['from_user_id']
    to_user_id = request['to_user_id']
    
    # Update request status
    await update_friend_request(request_id, {'status': 'rejected'})
    
    # Remove from pending lists
    await update_user(from_user_id, {'$pull': {'friend_requests_sent': to_user_id}})
    await update_user(to_user_id, {'$pull': {'friend_requests_received': from_user_id}})
    
    return {"message": "Friend request rejected"}

@router.delete("/remove/{user_id}")
async def remove_friend(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove a friend"""
    current_id = current_user['id']
    
    # Check if actually friends
    if user_id not in current_user.get('friends', []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not your friend"
        )
    
    # Remove from both friends lists
    await update_user(current_id, {'$pull': {'friends': user_id}})
    await update_user(user_id, {'$pull': {'friends': current_id}})
    
    # Notify
    await socket_manager.send_message_to_user(user_id, 'friend_removed', {
        'user_id': current_id
    })
    
    return {"message": "Friend removed"}

@router.get("/requests/received", response_model=List[FriendRequestResponse])
async def get_received_requests(current_user: dict = Depends(get_current_user)):
    """Get pending friend requests received"""
    requests = await get_pending_friend_requests(current_user['id'])
    
    # Get sender details
    sender_ids = [r['from_user_id'] for r in requests]
    senders = await get_users_by_ids(sender_ids)
    senders_map = {u['id']: u for u in senders}
    
    result = []
    for req in requests:
        sender = senders_map.get(req['from_user_id'])
        if sender:
            result.append(FriendRequestResponse(
                id=req['id'],
                from_user=UserResponse(
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
                ),
                to_user=UserResponse(
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
                ),
                status=req['status'],
                created_at=req['created_at']
            ))
    
    return result

@router.get("/list", response_model=List[UserResponse])
async def get_friends_list(current_user: dict = Depends(get_current_user)):
    """Get list of friends"""
    friend_ids = current_user.get('friends', [])
    
    if not friend_ids:
        return []
    
    friends = await get_users_by_ids(friend_ids)
    
    return [
        UserResponse(
            id=friend['id'],
            username=friend['username'],
            display_name=friend['display_name'],
            avatar=friend.get('avatar'),
            bio=friend.get('bio'),
            phone_number=friend.get('phone_number'),
            email=friend.get('email'),
            role=friend.get('role', 'regular'),
            is_online=friend.get('is_online', False),
            last_seen=friend.get('last_seen'),
            created_at=friend['created_at']
        )
        for friend in friends
    ]

# ============ Blocking Routes ============

@router.post("/block/{user_id}")
async def block_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Block a user"""
    current_id = current_user['id']
    
    # Check if user exists
    target_user = await get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if already blocked
    if await is_blocked(current_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already blocked"
        )
    
    # Create block
    block_id = str(uuid.uuid4())
    block_data = {
        'id': block_id,
        'blocker_id': current_id,
        'blocked_id': user_id,
        'created_at': utc_now()
    }
    await create_block(block_data)
    
    # Update user's blocked list
    await update_user(current_id, {'$addToSet': {'blocked_users': user_id}})
    
    # Remove from friends if friends
    if user_id in current_user.get('friends', []):
        await update_user(current_id, {'$pull': {'friends': user_id}})
        await update_user(user_id, {'$pull': {'friends': current_id}})
    
    return {"message": "User blocked"}

@router.delete("/unblock/{user_id}")
async def unblock_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Unblock a user"""
    current_id = current_user['id']
    
    # Check if actually blocked
    if not await is_blocked(current_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not blocked"
        )
    
    # Remove block
    await delete_block(current_id, user_id)
    
    # Update user's blocked list
    await update_user(current_id, {'$pull': {'blocked_users': user_id}})
    
    return {"message": "User unblocked"}

@router.get("/blocked", response_model=List[UserResponse])
async def get_blocked_users(current_user: dict = Depends(get_current_user)):
    """Get list of blocked users"""
    blocked_ids = current_user.get('blocked_users', [])
    
    if not blocked_ids:
        return []
    
    blocked_users = await get_users_by_ids(blocked_ids)
    
    return [
        UserResponse(
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
        )
        for user in blocked_users
    ]
