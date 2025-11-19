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
    SYSTEM = "system"  # For system messages like "User joined"

class ChatType(str, Enum):
    DIRECT = "direct"
    GROUP = "group"
    CHANNEL = "channel"

class MessageStatus(str, Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"

class FriendRequestStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

class AdminPermission(str, Enum):
    # Group/Channel permissions
    CAN_CHANGE_INFO = "can_change_info"
    CAN_DELETE_MESSAGES = "can_delete_messages"
    CAN_BAN_USERS = "can_ban_users"
    CAN_INVITE_USERS = "can_invite_users"
    CAN_PIN_MESSAGES = "can_pin_messages"
    CAN_ADD_ADMINS = "can_add_admins"
    # Channel-specific
    CAN_POST = "can_post"
    CAN_EDIT_MESSAGES = "can_edit_messages"
    # Group-specific
    CAN_RESTRICT_MEMBERS = "can_restrict_members"

# ============ User Models ============
class UserBase(BaseModel):
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    username: str
    display_name: str
    bio: Optional[str] = None
    avatar: Optional[str] = None
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
    friends: List[str] = []  # Accepted friend user IDs
    friend_requests_sent: List[str] = []  # Pending requests sent
    friend_requests_received: List[str] = []  # Pending requests received
    blocked_users: List[str] = []  # Users I've blocked
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    google_id: Optional[str] = None

# ============ Friend Request Models ============
class FriendRequest(BaseModel):
    id: str
    from_user_id: str
    to_user_id: str
    status: FriendRequestStatus = FriendRequestStatus.PENDING
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

class FriendRequestCreate(BaseModel):
    to_user_id: str

class FriendRequestResponse(BaseModel):
    id: str
    from_user: UserResponse
    to_user: UserResponse
    status: FriendRequestStatus
    created_at: datetime

# ============ Block Models ============
class BlockUser(BaseModel):
    id: str
    blocker_id: str  # User who blocked
    blocked_id: str  # User who was blocked
    created_at: datetime = Field(default_factory=utc_now)

# ============ Chat/Group/Channel Models ============
class ChatPermissions(BaseModel):
    """Permissions for regular members in groups"""
    can_send_messages: bool = True
    can_send_media: bool = True
    can_send_polls: bool = True
    can_send_other: bool = True
    can_add_web_page_previews: bool = True
    can_change_info: bool = False
    can_invite_users: bool = False
    can_pin_messages: bool = False

class AdminRights(BaseModel):
    """Admin-specific permissions"""
    permissions: List[AdminPermission] = []
    custom_title: Optional[str] = None

class ChatMember(BaseModel):
    """Member information in a chat"""
    user_id: str
    role: str = "member"  # member, admin, owner
    joined_at: datetime = Field(default_factory=utc_now)
    admin_rights: Optional[AdminRights] = None
    restrictions: Optional[ChatPermissions] = None  # For restricted members

class BannedUser(BaseModel):
    """Banned user record"""
    user_id: str
    banned_by: str  # Admin who banned
    banned_at: datetime = Field(default_factory=utc_now)
    reason: Optional[str] = None
    until_date: Optional[datetime] = None  # For temporary bans

class ChatBase(BaseModel):
    chat_type: ChatType
    name: Optional[str] = None
    description: Optional[str] = None
    avatar: Optional[str] = None
    # For groups
    max_members: Optional[int] = 200000  # Groups: 200k limit
    default_permissions: Optional[ChatPermissions] = Field(default_factory=ChatPermissions)
    # For channels
    is_public: bool = False  # Public channels can be found in search
    username: Optional[str] = None  # For public channels/groups
    invite_link: Optional[str] = None

class ChatCreate(BaseModel):
    chat_type: ChatType
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: bool = False
    username: Optional[str] = None
    participant_ids: List[str] = []  # Initial members (for groups)

class Chat(ChatBase):
    id: str
    created_by: str
    owner_id: str  # Owner has root privileges
    # Members and permissions
    members: List[ChatMember] = []  # For groups
    subscribers: List[str] = []  # For channels (just IDs, not visible to each other)
    admins: List[str] = []  # Quick lookup for admin IDs
    banned_users: List[BannedUser] = []
    # Metadata
    member_count: int = 0
    subscriber_count: int = 0
    pinned_messages: List[str] = []
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    last_message: Optional[Dict[str, Any]] = None

class ChatResponse(Chat):
    participant_details: Optional[List[UserResponse]] = None
    my_role: Optional[str] = None  # Current user's role
    my_permissions: Optional[AdminRights] = None
    unread_count: Optional[int] = 0
    can_send_messages: bool = True  # Based on permissions

# ============ Message Models ============
class MessageBase(BaseModel):
    chat_id: str
    sender_id: str
    content: str
    message_type: MessageType = MessageType.TEXT
    reply_to: Optional[str] = None
    forwarded_from: Optional[str] = None
    media_url: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    duration: Optional[int] = None
    scheduled_at: Optional[datetime] = None
    delete_at: Optional[datetime] = None

class MessageCreate(MessageBase):
    pass

class Message(MessageBase):
    id: str
    status: MessageStatus = MessageStatus.SENT
    delivered_to: List[str] = []
    read_by: List[str] = []
    reactions: Dict[str, List[str]] = {}
    edited: bool = False
    deleted: bool = False
    views: int = 0  # For channels
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

class MessageResponse(Message):
    sender: Optional[UserResponse] = None

# ============ Search Models ============
class SearchResult(BaseModel):
    type: str  # "user", "group", "channel"
    id: str
    name: str
    username: Optional[str] = None
    avatar: Optional[str] = None
    description: Optional[str] = None
    member_count: Optional[int] = None
    is_member: bool = False
    is_public: bool = False

# ============ OTP Models ============
class OTPRequest(BaseModel):
    phone_number: str

class OTPVerify(BaseModel):
    phone_number: str
    otp: str

class OTP(BaseModel):
    phone_number: str
    otp: str
    created_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime
    verified: bool = False

# ============ Other Models ============
class ReactionCreate(BaseModel):
    message_id: str
    emoji: str

class ReactionRemove(BaseModel):
    message_id: str
    emoji: str

class TypingIndicator(BaseModel):
    chat_id: str
    user_id: str
    is_typing: bool

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class JoinRequest(BaseModel):
    """For joining public channels/groups"""
    chat_id: str

class InviteRequest(BaseModel):
    """For inviting users to groups/channels"""
    chat_id: str
    user_ids: List[str]

class UpdatePermissionsRequest(BaseModel):
    """For updating member permissions"""
    chat_id: str
    user_id: str
    permissions: Optional[ChatPermissions] = None
    admin_rights: Optional[AdminRights] = None

class BanUserRequest(BaseModel):
    """For banning users"""
    chat_id: str
    user_id: str
    reason: Optional[str] = None
    until_date: Optional[datetime] = None
