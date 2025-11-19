from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, List, Dict
import os
from datetime import datetime, timedelta
import logging
from utils import utc_now

logger = logging.getLogger(__name__)

class Database:
    client: Optional[AsyncIOMotorClient] = None
    db = None

    @classmethod
    def get_db(cls):
        if cls.db is None:
            mongo_url = os.environ['MONGO_URL']
            cls.client = AsyncIOMotorClient(mongo_url)
            cls.db = cls.client[os.environ.get('DB_NAME', 'chatapp')]
            logger.info("Database connection established")
        return cls.db

    @classmethod
    async def close_db(cls):
        if cls.client:
            cls.client.close()
            logger.info("Database connection closed")

    @classmethod
    async def create_indexes(cls):
        """Create database indexes for better performance"""
        db = cls.get_db()
        
        # Drop old indexes
        try:
            await db.users.drop_index("phone_number_1")
            await db.users.drop_index("email_1")
        except:
            pass
        
        # Users indexes
        await db.users.create_index(
            "phone_number", 
            unique=True, 
            partialFilterExpression={"phone_number": {"$type": "string"}}
        )
        await db.users.create_index(
            "email", 
            unique=True,
            partialFilterExpression={"email": {"$type": "string"}}
        )
        await db.users.create_index("username", unique=True)
        await db.users.create_index("google_id", sparse=True)
        await db.users.create_index("friends")
        await db.users.create_index("blocked_users")
        
        # Messages indexes
        await db.messages.create_index("chat_id")
        await db.messages.create_index("sender_id")
        await db.messages.create_index([("chat_id", 1), ("created_at", -1)])
        await db.messages.create_index("scheduled_at", sparse=True)
        
        # Chats indexes
        await db.chats.create_index("chat_type")
        await db.chats.create_index("owner_id")
        await db.chats.create_index("members.user_id")
        await db.chats.create_index("subscribers")
        await db.chats.create_index("username", unique=True, sparse=True)
        await db.chats.create_index("is_public")
        await db.chats.create_index([("name", "text"), ("description", "text")])
        
        # Friend requests indexes
        await db.friend_requests.create_index("from_user_id")
        await db.friend_requests.create_index("to_user_id")
        await db.friend_requests.create_index("status")
        await db.friend_requests.create_index([("from_user_id", 1), ("to_user_id", 1)], unique=True)
        
        # Blocks indexes
        await db.blocks.create_index("blocker_id")
        await db.blocks.create_index("blocked_id")
        await db.blocks.create_index([("blocker_id", 1), ("blocked_id", 1)], unique=True)
        
        # OTP indexes
        await db.otps.create_index("phone_number")
        await db.otps.create_index("created_at", expireAfterSeconds=600)
        
        logger.info("Database indexes created successfully")

# ============ User Operations ============
async def get_user_by_phone(phone_number: str):
    db = Database.get_db()
    user = await db.users.find_one({"phone_number": phone_number})
    return user

async def get_user_by_email(email: str):
    db = Database.get_db()
    user = await db.users.find_one({"email": email})
    return user

async def get_user_by_id(user_id: str):
    db = Database.get_db()
    user = await db.users.find_one({"id": user_id})
    return user

async def get_user_by_username(username: str):
    db = Database.get_db()
    user = await db.users.find_one({"username": username})
    return user

async def create_user(user_data: dict):
    db = Database.get_db()
    result = await db.users.insert_one(user_data)
    return result.inserted_id

async def update_user(user_id: str, update_data: dict):
    db = Database.get_db()
    update_data['updated_at'] = utc_now()
    await db.users.update_one({"id": user_id}, {"$set": update_data})

async def get_users_by_ids(user_ids: List[str]) -> List[dict]:
    """Batch fetch users"""
    db = Database.get_db()
    users = await db.users.find({"id": {"$in": user_ids}}).to_list(None)
    return users

# ============ Friend Operations ============
async def create_friend_request(request_data: dict):
    db = Database.get_db()
    result = await db.friend_requests.insert_one(request_data)
    return result.inserted_id

async def get_friend_request(from_user_id: str, to_user_id: str):
    db = Database.get_db()
    return await db.friend_requests.find_one({
        "from_user_id": from_user_id,
        "to_user_id": to_user_id
    })

async def get_friend_request_by_id(request_id: str):
    db = Database.get_db()
    return await db.friend_requests.find_one({"id": request_id})

async def update_friend_request(request_id: str, update_data: dict):
    db = Database.get_db()
    update_data['updated_at'] = utc_now()
    await db.friend_requests.update_one({"id": request_id}, {"$set": update_data})

async def get_pending_friend_requests(user_id: str):
    """Get pending requests sent to this user"""
    db = Database.get_db()
    return await db.friend_requests.find({
        "to_user_id": user_id,
        "status": "pending"
    }).to_list(100)

async def get_sent_friend_requests(user_id: str):
    """Get pending requests sent by this user"""
    db = Database.get_db()
    return await db.friend_requests.find({
        "from_user_id": user_id,
        "status": "pending"
    }).to_list(100)

# ============ Block Operations ============
async def create_block(block_data: dict):
    db = Database.get_db()
    result = await db.blocks.insert_one(block_data)
    return result.inserted_id

async def delete_block(blocker_id: str, blocked_id: str):
    db = Database.get_db()
    await db.blocks.delete_one({
        "blocker_id": blocker_id,
        "blocked_id": blocked_id
    })

async def is_blocked(blocker_id: str, blocked_id: str) -> bool:
    """Check if blocker has blocked blocked_id"""
    db = Database.get_db()
    block = await db.blocks.find_one({
        "blocker_id": blocker_id,
        "blocked_id": blocked_id
    })
    return block is not None

async def is_blocked_by_any(user1_id: str, user2_id: str) -> bool:
    """Check if either user has blocked the other"""
    return await is_blocked(user1_id, user2_id) or await is_blocked(user2_id, user1_id)

# ============ Chat/Group/Channel Operations ============
async def get_chat_by_id(chat_id: str):
    db = Database.get_db()
    chat = await db.chats.find_one({"id": chat_id})
    return chat

async def get_chat_by_username(username: str):
    db = Database.get_db()
    chat = await db.chats.find_one({"username": username})
    return chat

async def get_user_chats(user_id: str):
    """Get all chats where user is a member or subscriber"""
    db = Database.get_db()
    chats = await db.chats.find({
        "$or": [
            {"members.user_id": user_id},
            {"subscribers": user_id}
        ]
    }).sort("updated_at", -1).to_list(1000)
    return chats

async def create_chat(chat_data: dict):
    db = Database.get_db()
    result = await db.chats.insert_one(chat_data)
    return result.inserted_id

async def update_chat(chat_id: str, update_data: dict):
    db = Database.get_db()
    update_data['updated_at'] = utc_now()
    await db.chats.update_one({"id": chat_id}, {"$set": update_data})

async def add_chat_member(chat_id: str, member_data: dict):
    """Add a member to a group"""
    db = Database.get_db()
    await db.chats.update_one(
        {"id": chat_id},
        {
            "$addToSet": {"members": member_data},
            "$inc": {"member_count": 1},
            "$set": {"updated_at": utc_now()}
        }
    )

async def remove_chat_member(chat_id: str, user_id: str):
    """Remove a member from a group"""
    db = Database.get_db()
    await db.chats.update_one(
        {"id": chat_id},
        {
            "$pull": {"members": {"user_id": user_id}},
            "$inc": {"member_count": -1},
            "$set": {"updated_at": utc_now()}
        }
    )

async def add_channel_subscriber(chat_id: str, user_id: str):
    """Add a subscriber to a channel"""
    db = Database.get_db()
    await db.chats.update_one(
        {"id": chat_id},
        {
            "$addToSet": {"subscribers": user_id},
            "$inc": {"subscriber_count": 1},
            "$set": {"updated_at": utc_now()}
        }
    )

async def remove_channel_subscriber(chat_id: str, user_id: str):
    """Remove a subscriber from a channel"""
    db = Database.get_db()
    await db.chats.update_one(
        {"id": chat_id},
        {
            "$pull": {"subscribers": user_id},
            "$inc": {"subscriber_count": -1},
            "$set": {"updated_at": utc_now()}
        }
    )

async def ban_user_from_chat(chat_id: str, banned_user_data: dict):
    """Ban a user from a group/channel"""
    db = Database.get_db()
    chat = await get_chat_by_id(chat_id)
    
    # Remove from members or subscribers
    if chat['chat_type'] == 'channel':
        await remove_channel_subscriber(chat_id, banned_user_data['user_id'])
    else:
        await remove_chat_member(chat_id, banned_user_data['user_id'])
    
    # Add to banned list
    await db.chats.update_one(
        {"id": chat_id},
        {
            "$addToSet": {"banned_users": banned_user_data},
            "$set": {"updated_at": utc_now()}
        }
    )

async def unban_user_from_chat(chat_id: str, user_id: str):
    """Unban a user from a group/channel"""
    db = Database.get_db()
    await db.chats.update_one(
        {"id": chat_id},
        {
            "$pull": {"banned_users": {"user_id": user_id}},
            "$set": {"updated_at": utc_now()}
        }
    )

async def is_user_banned(chat_id: str, user_id: str) -> bool:
    """Check if user is banned from chat"""
    db = Database.get_db()
    chat = await db.chats.find_one({
        "id": chat_id,
        "banned_users.user_id": user_id
    })
    return chat is not None

async def get_member_role(chat_id: str, user_id: str) -> Optional[dict]:
    """Get user's role and permissions in a chat"""
    db = Database.get_db()
    chat = await get_chat_by_id(chat_id)
    
    if not chat:
        return None
    
    if chat['owner_id'] == user_id:
        return {
            "role": "owner",
            "permissions": "all"
        }
    
    for member in chat.get('members', []):
        if member['user_id'] == user_id:
            return {
                "role": member.get('role', 'member'),
                "permissions": member.get('admin_rights') or member.get('restrictions')
            }
    
    return None

async def update_member_role(chat_id: str, user_id: str, role: str, admin_rights: Optional[dict] = None):
    """Update member's role and permissions"""
    db = Database.get_db()
    update_data = {"members.$.role": role, "members.$.updated_at": utc_now()}
    
    if admin_rights:
        update_data["members.$.admin_rights"] = admin_rights
        # Add to admins list if promoting
        await db.chats.update_one(
            {"id": chat_id},
            {"$addToSet": {"admins": user_id}}
        )
    else:
        # Remove from admins list if demoting
        await db.chats.update_one(
            {"id": chat_id},
            {"$pull": {"admins": user_id}}
        )
    
    await db.chats.update_one(
        {"id": chat_id, "members.user_id": user_id},
        {"$set": update_data}
    )

# ============ Message Operations ============
async def get_chat_messages(chat_id: str, limit: int = 50, skip: int = 0):
    db = Database.get_db()
    messages = await db.messages.find(
        {"chat_id": chat_id, "deleted": False}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return list(reversed(messages))

async def create_message(message_data: dict):
    db = Database.get_db()
    result = await db.messages.insert_one(message_data)
    
    # Update chat's last_message
    await db.chats.update_one(
        {"id": message_data["chat_id"]},
        {
            "$set": {
                "last_message": {
                    "content": message_data.get("content", ""),
                    "created_at": message_data["created_at"],
                    "sender_id": message_data["sender_id"],
                    "message_type": message_data["message_type"]
                },
                "updated_at": utc_now()
            }
        }
    )
    
    # Increment view count for channels
    chat = await get_chat_by_id(message_data["chat_id"])
    if chat and chat['chat_type'] == 'channel':
        await db.messages.update_one(
            {"id": message_data["id"]},
            {"$inc": {"views": 1}}
        )
    
    return result.inserted_id

async def update_message(message_id: str, update_data: dict):
    db = Database.get_db()
    update_data['updated_at'] = utc_now()
    await db.messages.update_one({"id": message_id}, {"$set": update_data})

async def get_message_by_id(message_id: str):
    db = Database.get_db()
    message = await db.messages.find_one({"id": message_id})
    return message

# ============ Search Operations ============
async def search_global(query: str, user_id: str, limit: int = 20):
    """Search across users, groups, and public channels"""
    db = Database.get_db()
    results = []
    
    # Search users
    users = await db.users.find({
        "$or": [
            {"username": {"$regex": query, "$options": "i"}},
            {"display_name": {"$regex": query, "$options": "i"}}
        ],
        "id": {"$ne": user_id}
    }).limit(limit).to_list(limit)
    
    for user in users:
        results.append({
            "type": "user",
            "id": user['id'],
            "name": user['display_name'],
            "username": user['username'],
            "avatar": user.get('avatar'),
            "is_friend": user_id in user.get('friends', [])
        })
    
    # Search public groups
    groups = await db.chats.find({
        "chat_type": "group",
        "is_public": True,
        "$or": [
            {"name": {"$regex": query, "$options": "i"}},
            {"username": {"$regex": query, "$options": "i"}},
            {"description": {"$regex": query, "$options": "i"}}
        ]
    }).limit(limit).to_list(limit)
    
    for group in groups:
        results.append({
            "type": "group",
            "id": group['id'],
            "name": group.get('name', 'Group'),
            "username": group.get('username'),
            "avatar": group.get('avatar'),
            "description": group.get('description'),
            "member_count": group.get('member_count', 0),
            "is_member": any(m['user_id'] == user_id for m in group.get('members', [])),
            "is_public": group['is_public']
        })
    
    # Search public channels
    channels = await db.chats.find({
        "chat_type": "channel",
        "is_public": True,
        "$or": [
            {"name": {"$regex": query, "$options": "i"}},
            {"username": {"$regex": query, "$options": "i"}},
            {"description": {"$regex": query, "$options": "i"}}
        ]
    }).limit(limit).to_list(limit)
    
    for channel in channels:
        results.append({
            "type": "channel",
            "id": channel['id'],
            "name": channel.get('name', 'Channel'),
            "username": channel.get('username'),
            "avatar": channel.get('avatar'),
            "description": channel.get('description'),
            "member_count": channel.get('subscriber_count', 0),
            "is_member": user_id in channel.get('subscribers', []),
            "is_public": channel['is_public']
        })
    
    return results
