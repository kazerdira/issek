from fastapi import APIRouter, HTTPException, status, Depends, File, UploadFile, Form
from typing import Optional
import uuid
import base64
import logging
from pathlib import Path

from auth import get_current_user
from database import get_chat_by_id

router = APIRouter(prefix="/media", tags=["Media"])
logger = logging.getLogger(__name__)

# In production, use cloud storage (S3, Google Cloud Storage, etc.)
# For now, we'll use base64 encoding for simplicity
MAX_VOICE_SIZE = 10 * 1024 * 1024  # 10MB max for voice messages

@router.post("/upload-voice")
async def upload_voice(
    file: UploadFile = File(...),
    chat_id: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload a voice message file"""
    
    # Verify user is in the chat
    chat = await get_chat_by_id(chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    # Check if user is a member (extract user_id from members array)
    member_ids = [m.get('user_id') if isinstance(m, dict) else m for m in chat.get('members', [])]
    if current_user['id'] not in member_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a participant of this chat"
        )
    
    # Validate file type
    if not file.content_type.startswith('audio/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an audio file"
        )
    
    # Read file content
    content = await file.read()
    
    # Check file size
    if len(content) > MAX_VOICE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Voice message too large. Maximum size is 10MB"
        )
    
    # Convert to base64 for storage
    # In production, upload to cloud storage and return URL
    base64_audio = base64.b64encode(content).decode('utf-8')
    media_url = f"data:{file.content_type};base64,{base64_audio}"
    
    logger.info(f"Voice message uploaded for chat {chat_id}, size: {len(content)} bytes")
    
    return {
        "media_url": media_url,
        "file_size": len(content),
        "content_type": file.content_type
    }
