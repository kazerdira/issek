"""
Clean test data from MongoDB
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = "mongodb://localhost:27017"
DATABASE_NAME = "chatapp"


async def clean_data():
    """Delete all test data"""
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DATABASE_NAME]
    
    # Delete test chats (those with null username or test names)
    result = await db.chats.delete_many({
        "$or": [
            {"username": None},
            {"name": {"$regex": "^Test"}},
            {"name": {"$regex": "Test Group"}},
            {"name": {"$regex": "Test Channel"}}
        ]
    })
    print(f"✓ Deleted {result.deleted_count} test chats")
    
    # Delete test users (those with testuser prefix)
    result = await db.users.delete_many({
        "username": {"$regex": "^testuser_"}
    })
    print(f"✓ Deleted {result.deleted_count} test users")
    
    # Delete test messages
    result = await db.messages.delete_many({})
    print(f"✓ Deleted {result.deleted_count} messages")
    
    # Delete test friend requests
    result = await db.friend_requests.delete_many({})
    print(f"✓ Deleted {result.deleted_count} friend requests")
    
    client.close()
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(clean_data())
