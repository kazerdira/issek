from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
import uuid
from datetime import datetime
import logging

from models import (
    UserResponse, FriendRequest, FriendRequestStatus
)
from auth import get_current_user
from database import (
    Database, get_user_by_id, update_user
)
from utils import utc_now

router = APIRouter(prefix="/friends", tags=["Friends"])
logger = logging.getLogger(__name__)

@router.post("/request/{user_id}", response_model=FriendRequest)
async def send_friend_request(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Send a friend request to a user"""
    if user_id == current_user['id']:
        raise HTTPException(status_code=400, detail="Cannot send friend request to yourself")
    
    target_user = await get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if blocked
    if current_user['id'] in target_user.get('blocked_users', []):
        raise HTTPException(status_code=403, detail="You cannot add this user")
    
    if user_id in current_user.get('blocked_users', []):
        raise HTTPException(status_code=400, detail="You have blocked this user. Unblock first.")

    # Check if already friends
    if user_id in current_user.get('friends', []):
        raise HTTPException(status_code=400, detail="Already friends")

    db = Database.get_db()
    
    # Check existing request
    existing_request = await db.friend_requests.find_one({
        '$or': [
            {'sender_id': current_user['id'], 'receiver_id': user_id},
            {'sender_id': user_id, 'receiver_id': current_user['id']}
        ],
        'status': FriendRequestStatus.PENDING
    })
    
    if existing_request:
        if existing_request['sender_id'] == current_user['id']:
            raise HTTPException(status_code=400, detail="Friend request already sent")
        else:
            raise HTTPException(status_code=400, detail="This user already sent you a friend request. Accept it instead.")

    request_id = str(uuid.uuid4())
    new_request = FriendRequest(
        id=request_id,
        sender_id=current_user['id'],
        receiver_id=user_id,
        status=FriendRequestStatus.PENDING
    )
    
    await db.friend_requests.insert_one(new_request.dict())
    
    # Notify receiver via socket
    from socket_manager import socket_manager
    await socket_manager.send_message_to_user(
        user_id, 
        'friend_request_received', 
        {
            'request_id': request_id,
            'sender': {
                'id': current_user['id'],
                'username': current_user['username'],
                'display_name': current_user['display_name'],
                'avatar': current_user.get('avatar')
            }
        }
    )
    
    return new_request

@router.post("/request/{request_id}/accept")
async def accept_friend_request(
    request_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Accept a friend request"""
    db = Database.get_db()
    request = await db.friend_requests.find_one({'id': request_id})
    
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
        
    if request['receiver_id'] != current_user['id']:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    if request['status'] != FriendRequestStatus.PENDING:
        raise HTTPException(status_code=400, detail="Request already processed")
        
    # Update request status
    await db.friend_requests.update_one(
        {'id': request_id},
        {'$set': {'status': FriendRequestStatus.ACCEPTED, 'updated_at': utc_now()}}
    )
    
    # Add to friends lists
    sender_id = request['sender_id']
    
    # Update current user (receiver)
    await db.users.update_one(
        {'id': current_user['id']},
        {'$addToSet': {'friends': sender_id}}
    )
    
    # Update sender
    await db.users.update_one(
        {'id': sender_id},
        {'$addToSet': {'friends': current_user['id']}}
    )
    
    # Notify sender via socket
    from socket_manager import socket_manager
    sender = await get_user_by_id(sender_id)
    await socket_manager.send_message_to_user(
        sender_id,
        'friend_request_accepted',
        {
            'user': {
                'id': current_user['id'],
                'username': current_user['username'],
                'display_name': current_user['display_name'],
                'avatar': current_user.get('avatar')
            }
        }
    )
    
    return {"message": "Friend request accepted"}

@router.post("/request/{request_id}/reject")
async def reject_friend_request(
    request_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Reject a friend request"""
    db = Database.get_db()
    request = await db.friend_requests.find_one({'id': request_id})
    
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
        
    if request['receiver_id'] != current_user['id']:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    if request['status'] != FriendRequestStatus.PENDING:
        raise HTTPException(status_code=400, detail="Request already processed")
        
    await db.friend_requests.update_one(
        {'id': request_id},
        {'$set': {'status': FriendRequestStatus.REJECTED, 'updated_at': utc_now()}}
    )
    
    # Notify sender via socket
    from socket_manager import socket_manager
    await socket_manager.send_message_to_user(
        request['sender_id'],
        'friend_request_rejected',
        {
            'user_id': current_user['id']
        }
    )
    
    return {"message": "Friend request rejected"}

@router.get("/requests/received", response_model=List[FriendRequest])
async def get_received_requests(current_user: dict = Depends(get_current_user)):
    """Get pending received friend requests"""
    db = Database.get_db()
    requests = await db.friend_requests.find({
        'receiver_id': current_user['id'],
        'status': FriendRequestStatus.PENDING
    }).to_list(None)
    return requests

@router.get("/list", response_model=List[UserResponse])
async def get_friends(current_user: dict = Depends(get_current_user)):
    """Get list of friends"""
    db = Database.get_db()
    friend_ids = current_user.get('friends', [])
    
    if not friend_ids:
        return []
        
    friends = await db.users.find({'id': {'$in': friend_ids}}).to_list(None)
    return [UserResponse(**f) for f in friends]

@router.post("/block/{user_id}")
async def block_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Block a user"""
    if user_id == current_user['id']:
        raise HTTPException(status_code=400, detail="Cannot block yourself")
        
    db = Database.get_db()
    
    # Add to blocked list
    await db.users.update_one(
        {'id': current_user['id']},
        {'$addToSet': {'blocked_users': user_id}}
    )
    
    # Remove from friends if exists
    await db.users.update_one(
        {'id': current_user['id']},
        {'$pull': {'friends': user_id}}
    )
    
    # Also remove current user from target's friend list
    await db.users.update_one(
        {'id': user_id},
        {'$pull': {'friends': current_user['id']}}
    )
    
    return {"message": "User blocked"}

@router.post("/unblock/{user_id}")
async def unblock_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Unblock a user"""
    db = Database.get_db()
    
    await db.users.update_one(
        {'id': current_user['id']},
        {'$pull': {'blocked_users': user_id}}
    )
    
    return {"message": "User unblocked"}

@router.get("/blocked", response_model=List[UserResponse])
async def get_blocked_users(current_user: dict = Depends(get_current_user)):
    """Get list of blocked users"""
    db = Database.get_db()
    blocked_ids = current_user.get('blocked_users', [])
    
    if not blocked_ids:
        return []
        
    users = await db.users.find({'id': {'$in': blocked_ids}}).to_list(None)
    return [UserResponse(**u) for u in users]
