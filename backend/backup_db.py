"""
MongoDB Backup Script
Exports all collections to JSON files for backup before migration
"""
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

async def backup_database():
    """Backup MongoDB database to JSON files"""
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    client = AsyncIOMotorClient(mongo_url)
    db = client['chatapp']
    
    # Create backup directory with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = f'../backup/json_backup_{timestamp}'
    os.makedirs(backup_dir, exist_ok=True)
    
    print(f"Starting backup to: {backup_dir}")
    
    # Get all collection names
    collections = await db.list_collection_names()
    print(f"Found collections: {collections}")
    
    for collection_name in collections:
        collection = db[collection_name]
        documents = await collection.find({}).to_list(length=None)
        
        # Convert ObjectId to string for JSON serialization
        for doc in documents:
            if '_id' in doc:
                doc['_id'] = str(doc['_id'])
        
        # Save to JSON file
        filepath = os.path.join(backup_dir, f'{collection_name}.json')
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(documents, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"✓ Backed up {collection_name}: {len(documents)} documents")
    
    # Create backup metadata
    metadata = {
        'timestamp': timestamp,
        'collections': collections,
        'total_collections': len(collections),
        'mongo_url': mongo_url.split('@')[-1] if '@' in mongo_url else mongo_url  # Hide credentials
    }
    
    with open(os.path.join(backup_dir, '_backup_metadata.json'), 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\n✅ Backup completed successfully!")
    print(f"   Location: {backup_dir}")
    print(f"   Collections: {len(collections)}")
    
    client.close()

if __name__ == '__main__':
    asyncio.run(backup_database())
