import asyncio
from database import Database

async def check_db():
    db = Database.get_db()
    collections = await db.list_collection_names()
    print('Collections:', collections)
    
    if 'friend_requests' in collections:
        indexes = await db.friend_requests.list_indexes().to_list(None)
        print('Friend requests indexes:', [idx['name'] for idx in indexes])
        for idx in indexes:
            if 'key' in idx:
                print(f'  {idx["name"]}: {idx["key"]}')

asyncio.run(check_db())