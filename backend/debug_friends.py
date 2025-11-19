import asyncio
import httpx
import random

async def test():
    async with httpx.AsyncClient() as client:
        # Create two users
        users = []
        for i in range(2):
            phone = f'+1555{random.randint(1000000, 9999999)}'
            data = {
                'username': f'testuser_debug_{random.randint(1000, 9999)}',
                'display_name': f'Test User {i}',
                'phone_number': phone,
                'password': 'TestPass123!@#'
            }
            
            response = await client.post('http://localhost:8000/api/auth/register', json=data)
            if response.status_code == 200:
                result = response.json()
                users.append({
                    'data': data,
                    'token': result['access_token'],
                    'user_id': result['user']['id']
                })
                print(f'Created user {i}: {result["user"]["username"]} with ID {result["user"]["id"]}')
        
        if len(users) == 2:
            # Send friend request
            friend_data = {'to_user_id': users[1]['user_id']}
            print(f'Sending friend request from user 0 to user 1')
            
            try:
                friend_response = await client.post(
                    'http://localhost:8000/api/friends/request',
                    json=friend_data,
                    headers={'Authorization': f'Bearer {users[0]["token"]}'},
                    timeout=30.0
                )
                print('Friends request response:', friend_response.status_code)
                print('Response text:', friend_response.text)
            except Exception as e:
                print('Exception during friend request:', e)

asyncio.run(test())