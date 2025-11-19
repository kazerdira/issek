"""
Database Migration Script
Migrates existing chat application to new Groups & Channels structure
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import utc_now

async def migrate_database():
    """Run all migrations"""
    
    # Connect to database
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ.get('DB_NAME', 'chatapp')]
    
    print("Starting migration...")
    
    # Migration 1: Add friends fields to users
    print("\n1. Migrating users collection...")
    users_result = await db.users.update_many(
        {},
        {
            '$set': {
                'friends': [],
                'friend_requests_sent': [],
                'friend_requests_received': [],
                'blocked_users': []
            }
        }
    )
    print(f"   Updated {users_result.modified_count} users")
    
    # Migration 2: Update chats to new structure
    print("\n2. Migrating chats collection...")
    
    # Get all chats
    chats = await db.chats.find({}).to_list(None)
    
    for chat in chats:
        chat_id = chat['id']
        
        # Determine chat type if not set
        if 'chat_type' not in chat:
            # If has 'participants' field, it's a group or direct chat
            if 'participants' in chat:
                participants = chat['participants']
                if len(participants) == 2:
                    chat_type = 'direct'
                else:
                    chat_type = 'group'
            else:
                chat_type = 'group'  # Default to group
        else:
            chat_type = chat['chat_type']
        
        # Build update based on chat type
        update = {
            'chat_type': chat_type,
            'banned_users': chat.get('banned_users', []),
            'is_public': chat.get('is_public', False),
            'invite_link': chat.get('invite_link'),
        }
        
        # Set owner_id if not exists
        if 'owner_id' not in chat:
            update['owner_id'] = chat.get('created_by')
        
        if chat_type == 'direct':
            # Direct chat - convert participants to members
            if 'participants' in chat:
                members = []
                for participant_id in chat['participants']:
                    members.append({
                        'user_id': participant_id,
                        'role': 'member',
                        'joined_at': chat.get('created_at', utc_now())
                    })
                update['members'] = members
                update['member_count'] = len(members)
            update['subscribers'] = []
            update['subscriber_count'] = 0
            update['admins'] = []
        
        elif chat_type == 'group':
            # Group - convert participants to members
            if 'participants' in chat and 'members' not in chat:
                members = []
                for participant_id in chat['participants']:
                    role = 'owner' if participant_id == chat.get('owner_id') else 'member'
                    members.append({
                        'user_id': participant_id,
                        'role': role,
                        'joined_at': chat.get('created_at', utc_now())
                    })
                update['members'] = members
                update['member_count'] = len(members)
            update['subscribers'] = []
            update['subscriber_count'] = 0
            update['admins'] = chat.get('admins', [])
            update['max_members'] = 200000
            update['default_permissions'] = {
                'can_send_messages': True,
                'can_send_media': True,
                'can_send_polls': True,
                'can_send_other': True,
                'can_add_web_page_previews': True,
                'can_change_info': False,
                'can_invite_users': False,
                'can_pin_messages': False
            }
        
        elif chat_type == 'channel':
            # Channel - subscribers only
            if 'participants' in chat:
                update['subscribers'] = chat['participants']
                update['subscriber_count'] = len(chat['participants'])
            else:
                update['subscribers'] = []
                update['subscriber_count'] = 0
            update['members'] = []
            update['member_count'] = 0
            update['admins'] = chat.get('admins', [])
        
        # Remove old 'participants' field
        await db.chats.update_one(
            {'id': chat_id},
            {
                '$set': update,
                '$unset': {'participants': ''}
            }
        )
    
    print(f"   Migrated {len(chats)} chats")
    
    # Migration 3: Add views field to messages (for channels)
    print("\n3. Migrating messages collection...")
    messages_result = await db.messages.update_many(
        {},
        {
            '$set': {
                'views': 0
            }
        }
    )
    print(f"   Updated {messages_result.modified_count} messages")
    
    # Migration 4: Create friend_requests collection
    print("\n4. Creating friend_requests collection...")
    # Collection will be created automatically when first document is inserted
    print("   Friend requests collection ready")
    
    # Migration 5: Create blocks collection
    print("\n5. Creating blocks collection...")
    # Collection will be created automatically when first document is inserted
    print("   Blocks collection ready")
    
    # Migration 6: Create indexes
    print("\n6. Creating database indexes...")
    
    # Users indexes
    await db.users.create_index("phone_number", unique=True, partialFilterExpression={"phone_number": {"$type": "string"}})
    await db.users.create_index("email", unique=True, partialFilterExpression={"email": {"$type": "string"}})
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
    
    print("   All indexes created")
    
    print("\n✅ Migration completed successfully!")
    print("\nNext steps:")
    print("1. Restart your backend server")
    print("2. Test the API endpoints")
    print("3. Update your frontend")
    
    client.close()

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    from pathlib import Path
    
    ROOT_DIR = Path(__file__).parent.parent
    load_dotenv(ROOT_DIR / '.env')
    
    print("=" * 60)
    print("Database Migration - Groups & Channels")
    print("=" * 60)
    print("\nThis will migrate your database to the new structure.")
    print("It's recommended to backup your database first.")
    print("\nContinue? (y/n): ", end='')
    
    response = input().strip().lower()
    if response == 'y':
        asyncio.run(migrate_database())
    else:
        print("Migration cancelled.")
