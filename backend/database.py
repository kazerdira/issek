from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
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
            try:
                mongo_url = os.environ['MONGO_URL']
                
                # Configure connection pooling
                cls.client = AsyncIOMotorClient(
                    mongo_url,
                    maxPoolSize=50,  # Maximum connections in pool
                    minPoolSize=10,  # Minimum connections maintained
                    maxIdleTimeMS=60000,  # Close idle connections after 1 minute
                    serverSelectionTimeoutMS=5000,  # Timeout for server selection
                    connectTimeoutMS=10000,  # Timeout for initial connection
                    socketTimeoutMS=20000  # Timeout for socket operations
                )
                
                cls.db = cls.client[os.environ.get('DB_NAME', 'chatapp')]
                logger.info("Database connection established with connection pooling")
            except Exception as e:
                logger.error(f"Failed to connect to MongoDB: {str(e)}")
                raise RuntimeError(f"Database connection failed: {str(e)}")
        
        return cls.db

    @classmethod
    async def close_db(cls):
        if cls.client:
            try:
                cls.client.close()
                logger.info("Database connection closed")
            except Exception as e:
                logger.error(f"Error closing database connection: {str(e)}")
    
    @classmethod
    async def health_check(cls) -> bool:
        """Check if database connection is alive"""
        try:
            db = cls.get_db()
            await db.command('ping')
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return False

    @classmethod
    async def create_indexes(cls):
        """Create database indexes for better performance"""
        db = cls.get_db()
        
        # Drop existing indexes to recreate them properly
        try:
            await db.users.drop_index("phone_number_1")
        except:
            pass
        try:
            await db.users.drop_index("email_1")
        except:
            pass
        
        # Users indexes - partialFilterExpression ensures unique only when field exists
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
        
        # Messages indexes
        await db.messages.create_index("chat_id")
        await db.messages.create_index("sender_id")
        await db.messages.create_index([("chat_id", 1), ("created_at", -1)])
        await db.messages.create_index("scheduled_at", sparse=True)
        
        # Chats indexes
        await db.chats.create_index("participants")
        await db.chats.create_index("created_by")
        
        # OTP indexes
        await db.otps.create_index("phone_number")
        await db.otps.create_index("created_at", expireAfterSeconds=600)  # Auto-delete after 10 minutes
        
        # Friend Requests indexes
        await db.friend_requests.create_index([("sender_id", 1), ("receiver_id", 1)], unique=True)
        await db.friend_requests.create_index("receiver_id")
        await db.friend_requests.create_index("sender_id")
        
        logger.info("Database indexes created successfully")

# Helper functions
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

async def get_chat_by_id(chat_id: str):
    db = Database.get_db()
    chat = await db.chats.find_one({"id": chat_id})
    return chat

async def get_user_chats(user_id: str):
    db = Database.get_db()
    chats = await db.chats.find({"participants": user_id}).sort("updated_at", -1).to_list(1000)
    return chats

async def create_chat(chat_data: dict):
    db = Database.get_db()
    result = await db.chats.insert_one(chat_data)
    return result.inserted_id

async def get_chat_messages(chat_id: str, limit: int = 50, skip: int = 0):
    db = Database.get_db()
    messages = await db.messages.find(
        {"chat_id": chat_id, "deleted": False}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return list(reversed(messages))  # Return in chronological order

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
    return result.inserted_id

async def update_message(message_id: str, update_data: dict):
    db = Database.get_db()
    update_data['updated_at'] = utc_now()
    await db.messages.update_one({"id": message_id}, {"$set": update_data})

async def get_message_by_id(message_id: str):
    db = Database.get_db()
    message = await db.messages.find_one({"id": message_id})
    return message
