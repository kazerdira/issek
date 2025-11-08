from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from utils import utc_now

class UserRole(str, Enum):
    REGULAR = "regular"
    PREMIUM = "premium"
    ADMIN = "admin"

class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    FILE = "file"
    VOICE = "voice"

class ChatType(str, Enum):
    DIRECT = "direct"
    GROUP = "group"

class MessageStatus(str, Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"

# User Models
class UserBase(BaseModel):
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    username: str
    display_name: str
    bio: Optional[str] = None
    avatar: Optional[str] = None  # base64
    role: UserRole = UserRole.REGULAR

class UserCreate(UserBase):
    password: Optional[str] = None

class UserLogin(BaseModel):
    phone_number: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None

class UserResponse(UserBase):
    id: str
    is_online: bool = False
    last_seen: Optional[datetime] = None
    created_at: datetime

class User(UserBase):
    id: str
    hashed_password: Optional[str] = None
    is_online: bool = False
    last_seen: Optional[datetime] = None
    contacts: List[str] = []  # user IDs
    blocked_users: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    google_id: Optional[str] = None

# OTP Models
class OTPRequest(BaseModel):
    phone_number: str

class OTPVerify(BaseModel):
    phone_number: str
    otp: str

class OTP(BaseModel):
    phone_number: str
    otp: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    verified: bool = False

# Message Models
class MessageBase(BaseModel):
    chat_id: str
    sender_id: str
    content: str
    message_type: MessageType = MessageType.TEXT
    reply_to: Optional[str] = None  # message ID
    forwarded_from: Optional[str] = None  # message ID
    media_url: Optional[str] = None  # base64 for images/videos
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    duration: Optional[int] = None  # for voice/video messages
    scheduled_at: Optional[datetime] = None
    delete_at: Optional[datetime] = None  # for disappearing messages

class MessageCreate(MessageBase):
    pass

class Message(MessageBase):
    id: str
    status: MessageStatus = MessageStatus.SENT
    delivered_to: List[str] = []  # user IDs who received
    read_by: List[str] = []  # user IDs who read
    reactions: Dict[str, List[str]] = {}  # {emoji: [user_ids]}
    edited: bool = False
    deleted: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class MessageResponse(Message):
    sender: Optional[UserResponse] = None

# Reaction Models
class ReactionCreate(BaseModel):
    message_id: str
    emoji: str

class ReactionRemove(BaseModel):
    message_id: str
    emoji: str

# Chat Models
class ChatBase(BaseModel):
    chat_type: ChatType
    name: Optional[str] = None  # for groups
    description: Optional[str] = None
    avatar: Optional[str] = None  # base64
    participants: List[str]  # user IDs

class ChatCreate(ChatBase):
    pass

class Chat(ChatBase):
    id: str
    created_by: str
    admins: List[str] = []  # for groups
    pinned_messages: List[str] = []  # message IDs
    muted_by: List[str] = []  # user IDs
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_message: Optional[Dict[str, Any]] = None

class ChatResponse(Chat):
    participant_details: Optional[List[UserResponse]] = None
    unread_count: Optional[int] = 0

# Typing Indicator
class TypingIndicator(BaseModel):
    chat_id: str
    user_id: str
    is_typing: bool

# Token Response
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
