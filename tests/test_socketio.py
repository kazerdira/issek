#!/usr/bin/env python3
"""
Socket.IO Real-time Messaging Tests
Tests authentication, room joining, and message delivery
"""

import asyncio
import json
import logging
from socketio import AsyncClient
import sys
import os

# Add backend path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

class SocketIOTester:
    def __init__(self, server_url="http://localhost:8001"):
        self.server_url = server_url
        self.clients = {}
        self.received_messages = {}
        
    async def create_client(self, user_name, token):
        """Create and connect a Socket.IO client"""
        client = AsyncClient(logger=False, engineio_logger=False)
        
        @client.event
        async def connect():
            print(f"✅ {user_name} connected to Socket.IO server")
            await client.emit('authenticate', {'token': token})
        
        @client.event
        async def connect_error(data):
            print(f"❌ {user_name} connection error: {data}")
        
        @client.event
        async def disconnect():
            print(f"🔌 {user_name} disconnected from Socket.IO server")
        
        @client.event
        async def authenticated(data):
            print(f"🔐 {user_name} authenticated successfully: {data}")
        
        @client.event
        async def authentication_error(data):
            print(f"❌ {user_name} authentication error: {data}")
        
        @client.event
        async def room_joined(data):
            print(f"🏠 {user_name} joined room: {data.get('room_id')}")
        
        @client.event
        async def new_message(data):
            print(f"📨 {user_name} received message: {data}")
            if user_name not in self.received_messages:
                self.received_messages[user_name] = []
            self.received_messages[user_name].append(data)
        
        @client.event
        async def user_joined_room(data):
            print(f"👥 {user_name} sees user joined room: {data}")
        
        @client.event
        async def user_left_room(data):
            print(f"👋 {user_name} sees user left room: {data}")
        
        # Connect to server
        await client.connect(self.server_url)
        self.clients[user_name] = client
        return client
    
    async def join_room(self, user_name, room_id):
        """Join a chat room"""
        client = self.clients.get(user_name)
        if client:
            await client.emit('join_room', {'room_id': room_id})
            print(f"🔄 {user_name} attempting to join room: {room_id}")
    
    async def send_message(self, user_name, room_id, message):
        """Send a message to a room"""
        client = self.clients.get(user_name)
        if client:
            await client.emit('send_message', {
                'room_id': room_id,
                'content': message,
                'message_type': 'text'
            })
            print(f"📤 {user_name} sent message: '{message}' to room {room_id}")
    
    async def disconnect_all(self):
        """Disconnect all clients"""
        for user_name, client in self.clients.items():
            await client.disconnect()
            print(f"🔌 {user_name} disconnected")

async def test_socketio_messaging():
    """Test Socket.IO real-time messaging functionality"""
    print("🚀 Starting Socket.IO messaging tests...\n")
    
    # Test tokens (these would come from login API calls)
    # Using the token we got from alice login earlier
    alice_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1ZGNkNWIzMC1mNzk1LTRmODYtOGJkNS00MDkxNDYzOTQzZmQiLCJleHAiOjE3NjUyMTg1NTF9.Nce_PdJpyyf8IKAqp5FB1RDK9g7ROWlifTVqXW2UzVQ"
    
    # For this test, we'll need Bob's token too. Let's use a placeholder for now
    bob_token = "placeholder_bob_token"  # We'd get this from Bob's login
    
    tester = SocketIOTester()
    
    try:
        print("1️⃣ Testing Alice connection and authentication...")
        alice_client = await tester.create_client("Alice", alice_token)
        await asyncio.sleep(2)  # Wait for authentication
        
        print("\n2️⃣ Testing room joining...")
        test_room_id = "test_room_123"
        await tester.join_room("Alice", test_room_id)
        await asyncio.sleep(2)
        
        print("\n3️⃣ Testing message sending...")
        await tester.send_message("Alice", test_room_id, "Hello from Alice! 👋")
        await asyncio.sleep(2)
        
        print("\n4️⃣ Testing multiple users (Alice only for now)...")
        await tester.send_message("Alice", test_room_id, "Second message from Alice 📱")
        await asyncio.sleep(2)
        
        print("\n📊 Test Results:")
        print(f"- Alice received {len(tester.received_messages.get('Alice', []))} messages")
        
        for user, messages in tester.received_messages.items():
            print(f"  {user} messages: {messages}")
        
        await asyncio.sleep(2)
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n🔚 Cleaning up...")
        await tester.disconnect_all()
    
    print("✅ Socket.IO tests completed!")

async def test_authentication_only():
    """Test just Socket.IO authentication"""
    print("🔐 Testing Socket.IO authentication only...\n")
    
    alice_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1ZGNkNWIzMC1mNzk1LTRmODYtOGJkNS00MDkxNDYzOTQzZmQiLCJleHAiOjE3NjUyMTg1NTF9.Nce_PdJpyyf8IKAqp5FB1RDK9g7ROWlifTVqXW2UzVQ"
    
    tester = SocketIOTester()
    
    try:
        print("Connecting and authenticating Alice...")
        await tester.create_client("Alice", alice_token)
        await asyncio.sleep(5)  # Wait for authentication events
        
    except Exception as e:
        print(f"❌ Authentication test error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await tester.disconnect_all()

if __name__ == "__main__":
    print("Socket.IO Test Options:")
    print("1. Full messaging test")
    print("2. Authentication only test")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        asyncio.run(test_socketio_messaging())
    elif choice == "2":
        asyncio.run(test_authentication_only())
    else:
        print("Invalid choice, running authentication test...")
        asyncio.run(test_authentication_only())