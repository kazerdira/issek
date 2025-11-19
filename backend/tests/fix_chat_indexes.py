"""
Fix MongoDB indexes for chats collection
Removes old username_1 index and creates sparse unique index
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import OperationFailure

MONGO_URL = "mongodb://localhost:27017"
DATABASE_NAME = "chatapp"


async def fix_chat_indexes():
    """Fix indexes for chats collection"""
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DATABASE_NAME]
    
    print("Checking chats collection indexes...")
    
    # Get existing indexes
    indexes = await db.chats.index_information()
    print(f"Existing indexes: {list(indexes.keys())}")
    
    # Drop old username_1 index if it exists
    if "username_1" in indexes:
        print("Found old username_1 index, dropping it...")
        try:
            await db.chats.drop_index("username_1")
            print("✓ Dropped old username_1 index")
        except OperationFailure as e:
            print(f"✗ Failed to drop index: {e}")
    
    # Create new sparse NON-UNIQUE index (allows multiple null values)
    print("Creating new sparse (non-unique) index for username...")
    try:
        await db.chats.create_index("username", unique=False, sparse=True)
        print("✓ Created sparse non-unique index for username")
    except OperationFailure as e:
        print(f"Note: Index may already exist correctly: {e}")
    
    # Verify final indexes
    indexes = await db.chats.index_information()
    print(f"\nFinal indexes: {list(indexes.keys())}")
    
    if "username_1" in indexes:
        index_info = indexes["username_1"]
        print(f"username_1 index info: {index_info}")
        if index_info.get("sparse"):
            print("✓ Username index is sparse!")
        if not index_info.get("unique"):
            print("✓ Username index is non-unique (allows multiple nulls)!")
    
    client.close()
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(fix_chat_indexes())
