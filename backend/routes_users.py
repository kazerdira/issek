from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List
import logging

from models import UserResponse
from auth import get_current_user
from database import Database, get_user_by_id, update_user

router = APIRouter(prefix="/users", tags=["Users"])
logger = logging.getLogger(__name__)

@router.get("/search", response_model=List[UserResponse])
async def search_users(
    q: str = Query(..., min_length=1),
    current_user: dict = Depends(get_current_user)
):
    """Search users by username, display name, or phone number"""
    db = Database.get_db()
    
    # Search by username or display name
    users = await db.users.find({
        '$or': [
            {'username': {'$regex': q, '$options': 'i'}},
            {'display_name': {'$regex': q, '$options': 'i'}},
            {'phone_number': {'$regex': q}}
        ],
        'id': {'$ne': current_user['id']}  # Exclude current user
    }).limit(20).to_list(20)
    
    result = []
    for user in users:
        result.append(UserResponse(
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
    
    return result

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get user by ID"""
    user = await get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
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

@router.post("/contacts/{user_id}")
async def add_contact(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Add user to contacts"""
    user = await get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    contacts = current_user.get('contacts', [])
    if user_id not in contacts:
        contacts.append(user_id)
        await update_user(current_user['id'], {'contacts': contacts})
    
    return {"message": "Contact added"}

@router.delete("/contacts/{user_id}")
async def remove_contact(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove user from contacts"""
    contacts = current_user.get('contacts', [])
    if user_id in contacts:
        contacts.remove(user_id)
        await update_user(current_user['id'], {'contacts': contacts})
    
    return {"message": "Contact removed"}

@router.get("/contacts", response_model=List[UserResponse])
async def get_contacts(current_user: dict = Depends(get_current_user)):
    """Get user's contacts"""
    contacts = current_user.get('contacts', [])
    
    result = []
    for contact_id in contacts:
        user = await get_user_by_id(contact_id)
        if user:
            result.append(UserResponse(
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
    
    return result
