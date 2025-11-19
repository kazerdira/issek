"""
Fix MongoDB indexes for friend_requests collection
The old index uses sender_id/receiver_id but code uses from_user_id/to_user_id
"""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from database import Database

async def fix_indexes():
    db = Database.get_db()
    
    print("🔧 Fixing friend_requests indexes...")
    
    # Drop old indexes
    try:
        await db.friend_requests.drop_index("sender_id_1_receiver_id_1")
        print("✅ Dropped old index: sender_id_1_receiver_id_1")
    except Exception as e:
        print(f"⚠️  Could not drop sender_id_1_receiver_id_1: {e}")
    
    # Create correct index
    await db.friend_requests.create_index(
        [("from_user_id", 1), ("to_user_id", 1)],
        unique=True
    )
    print("✅ Created new index: from_user_id_1_to_user_id_1")
    
    # List all indexes
    indexes = await db.friend_requests.list_indexes().to_list(None)
    print("\n📋 Current indexes:")
    for idx in indexes:
        print(f"  - {idx['name']}: {idx.get('key', {})}")
    
    print("\n🎉 Indexes fixed!")

if __name__ == "__main__":
    asyncio.run(fix_indexes())
