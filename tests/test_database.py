"""
Unit tests for database operations (database.py).
Tests database connection, user CRUD operations, and message handling.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from backend.database import Database


class TestDatabase:
    """Test suite for Database class."""
    
    @pytest.fixture
    def mock_mongo_client(self):
        """Mock MongoDB client."""
        client = MagicMock()
        db = MagicMock()
        client.__getitem__.return_value = db
        return client, db
    
    @pytest.mark.asyncio
    async def test_database_initialization(self, mock_mongo_client):
        """Test database initialization."""
        client, db = mock_mongo_client
        
        with patch('backend.database.AsyncIOMotorClient', return_value=client):
            database = Database()
            await database.connect()
            
            assert database.client == client
            assert database.db == db
            assert hasattr(database, 'users')
            assert hasattr(database, 'messages')
            assert hasattr(database, 'chat_rooms')
    
    @pytest.mark.asyncio
    async def test_connect_success(self, mock_mongo_client):
        """Test successful database connection."""
        client, db = mock_mongo_client
        client.admin.command = AsyncMock(return_value={"ismaster": True})
        
        with patch('backend.database.AsyncIOMotorClient', return_value=client):
            database = Database()
            result = await database.connect()
            
            assert result is True
            client.admin.command.assert_called_once_with('ismaster')
    
    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test database connection failure."""
        with patch('backend.database.AsyncIOMotorClient') as mock_client:
            mock_client.side_effect = Exception("Connection failed")
            
            database = Database()
            result = await database.connect()
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_disconnect(self, mock_mongo_client):
        """Test database disconnection."""
        client, db = mock_mongo_client
        
        with patch('backend.database.AsyncIOMotorClient', return_value=client):
            database = Database()
            await database.connect()
            await database.disconnect()
            
            client.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_user(self, mock_mongo_client, test_user_data):
        """Test user creation."""
        client, db = mock_mongo_client
        mock_collection = MagicMock()
        mock_collection.insert_one = AsyncMock(return_value=MagicMock(inserted_id="user123"))
        db.__getitem__.return_value = mock_collection
        
        with patch('backend.database.AsyncIOMotorClient', return_value=client):
            database = Database()
            await database.connect()
            
            result = await database.create_user(test_user_data)
            
            assert result == "user123"
            mock_collection.insert_one.assert_called_once()
            
            # Verify timestamp was added
            call_args = mock_collection.insert_one.call_args[0][0]
            assert "created_at" in call_args
    
    @pytest.mark.asyncio
    async def test_get_user_by_email(self, mock_mongo_client, test_user_hashed):
        """Test user retrieval by email."""
        client, db = mock_mongo_client
        mock_collection = MagicMock()
        mock_collection.find_one = AsyncMock(return_value=test_user_hashed)
        db.__getitem__.return_value = mock_collection
        
        with patch('backend.database.AsyncIOMotorClient', return_value=client):
            database = Database()
            await database.connect()
            
            result = await database.get_user_by_email(test_user_hashed["email"])
            
            assert result == test_user_hashed
            mock_collection.find_one.assert_called_once_with({"email": test_user_hashed["email"]})
    
    @pytest.mark.asyncio
    async def test_get_user_by_id(self, mock_mongo_client, test_user_hashed):
        """Test user retrieval by ID."""
        client, db = mock_mongo_client
        mock_collection = MagicMock()
        mock_collection.find_one = AsyncMock(return_value=test_user_hashed)
        db.__getitem__.return_value = mock_collection
        
        with patch('backend.database.AsyncIOMotorClient', return_value=client):
            database = Database()
            await database.connect()
            
            result = await database.get_user_by_id(test_user_hashed["_id"])
            
            assert result == test_user_hashed
            mock_collection.find_one.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_all_users(self, mock_mongo_client, alice_user, bob_user):
        """Test retrieval of all users."""
        client, db = mock_mongo_client
        mock_collection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[alice_user, bob_user])
        mock_collection.find.return_value = mock_cursor
        db.__getitem__.return_value = mock_collection
        
        with patch('backend.database.AsyncIOMotorClient', return_value=client):
            database = Database()
            await database.connect()
            
            result = await database.get_all_users()
            
            assert len(result) == 2
            assert alice_user in result
            assert bob_user in result
            mock_collection.find.assert_called_once_with({}, {"password_hash": 0})
    
    @pytest.mark.asyncio
    async def test_update_user(self, mock_mongo_client):
        """Test user update."""
        client, db = mock_mongo_client
        mock_collection = MagicMock()
        mock_collection.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
        db.__getitem__.return_value = mock_collection
        
        with patch('backend.database.AsyncIOMotorClient', return_value=client):
            database = Database()
            await database.connect()
            
            user_id = "user123"
            update_data = {"name": "Updated Name"}
            result = await database.update_user(user_id, update_data)
            
            assert result is True
            mock_collection.update_one.assert_called_once()
            
            # Verify the update includes updated_at timestamp
            call_args = mock_collection.update_one.call_args
            assert "$set" in call_args[0][1]
            assert "updated_at" in call_args[0][1]["$set"]
    
    @pytest.mark.asyncio
    async def test_update_user_not_found(self, mock_mongo_client):
        """Test updating non-existent user."""
        client, db = mock_mongo_client
        mock_collection = MagicMock()
        mock_collection.update_one = AsyncMock(return_value=MagicMock(modified_count=0))
        db.__getitem__.return_value = mock_collection
        
        with patch('backend.database.AsyncIOMotorClient', return_value=client):
            database = Database()
            await database.connect()
            
            result = await database.update_user("nonexistent", {"name": "Test"})
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_delete_user(self, mock_mongo_client):
        """Test user deletion."""
        client, db = mock_mongo_client
        mock_collection = MagicMock()
        mock_collection.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))
        db.__getitem__.return_value = mock_collection
        
        with patch('backend.database.AsyncIOMotorClient', return_value=client):
            database = Database()
            await database.connect()
            
            result = await database.delete_user("user123")
            
            assert result is True
            mock_collection.delete_one.assert_called_once_with({"_id": "user123"})
    
    @pytest.mark.asyncio
    async def test_create_message(self, mock_mongo_client, test_message):
        """Test message creation."""
        client, db = mock_mongo_client
        mock_collection = MagicMock()
        mock_collection.insert_one = AsyncMock(return_value=MagicMock(inserted_id="msg123"))
        db.__getitem__.return_value = mock_collection
        
        with patch('backend.database.AsyncIOMotorClient', return_value=client):
            database = Database()
            await database.connect()
            
            result = await database.create_message(test_message)
            
            assert result == "msg123"
            mock_collection.insert_one.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_messages_between_users(self, mock_mongo_client, test_message):
        """Test retrieving messages between two users."""
        client, db = mock_mongo_client
        mock_collection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[test_message])
        mock_collection.find.return_value = mock_cursor
        db.__getitem__.return_value = mock_collection
        
        with patch('backend.database.AsyncIOMotorClient', return_value=client):
            database = Database()
            await database.connect()
            
            result = await database.get_messages_between_users("alice123", "bob456", limit=50)
            
            assert len(result) == 1
            assert result[0] == test_message
            mock_collection.find.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_mark_message_as_read(self, mock_mongo_client):
        """Test marking message as read."""
        client, db = mock_mongo_client
        mock_collection = MagicMock()
        mock_collection.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
        db.__getitem__.return_value = mock_collection
        
        with patch('backend.database.AsyncIOMotorClient', return_value=client):
            database = Database()
            await database.connect()
            
            result = await database.mark_message_as_read("msg123")
            
            assert result is True
            mock_collection.update_one.assert_called_once_with(
                {"_id": "msg123"},
                {"$set": {"is_read": True}}
            )
    
    @pytest.mark.asyncio
    async def test_create_chat_room(self, mock_mongo_client, test_chat_room):
        """Test chat room creation."""
        client, db = mock_mongo_client
        mock_collection = MagicMock()
        mock_collection.insert_one = AsyncMock(return_value=MagicMock(inserted_id="room123"))
        db.__getitem__.return_value = mock_collection
        
        with patch('backend.database.AsyncIOMotorClient', return_value=client):
            database = Database()
            await database.connect()
            
            result = await database.create_chat_room(test_chat_room["participants"])
            
            assert result == "room123"
            mock_collection.insert_one.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_chat_room_by_participants(self, mock_mongo_client, test_chat_room):
        """Test retrieving chat room by participants."""
        client, db = mock_mongo_client
        mock_collection = MagicMock()
        mock_collection.find_one = AsyncMock(return_value=test_chat_room)
        db.__getitem__.return_value = mock_collection
        
        with patch('backend.database.AsyncIOMotorClient', return_value=client):
            database = Database()
            await database.connect()
            
            participants = ["alice123", "bob456"]
            result = await database.get_chat_room_by_participants(participants)
            
            assert result == test_chat_room
            mock_collection.find_one.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_chat_room_last_message(self, mock_mongo_client):
        """Test updating chat room's last message."""
        client, db = mock_mongo_client
        mock_collection = MagicMock()
        mock_collection.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
        db.__getitem__.return_value = mock_collection
        
        with patch('backend.database.AsyncIOMotorClient', return_value=client):
            database = Database()
            await database.connect()
            
            room_id = "room123"
            message_data = {
                "content": "Hello!",
                "sender_id": "alice123",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            result = await database.update_chat_room_last_message(room_id, message_data)
            
            assert result is True
            mock_collection.update_one.assert_called_once()


class TestDatabaseErrorHandling:
    """Test error handling in database operations."""
    
    @pytest.mark.asyncio
    async def test_connection_error_handling(self):
        """Test handling of database connection errors."""
        with patch('backend.database.AsyncIOMotorClient') as mock_client:
            mock_client.side_effect = Exception("Connection failed")
            
            database = Database()
            result = await database.connect()
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_operation_error_handling(self, mock_mongo_client):
        """Test handling of database operation errors."""
        client, db = mock_mongo_client
        mock_collection = MagicMock()
        mock_collection.find_one = AsyncMock(side_effect=Exception("Database error"))
        db.__getitem__.return_value = mock_collection
        
        with patch('backend.database.AsyncIOMotorClient', return_value=client):
            database = Database()
            await database.connect()
            
            result = await database.get_user_by_email("test@example.com")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_insert_error_handling(self, mock_mongo_client):
        """Test handling of insert operation errors."""
        client, db = mock_mongo_client
        mock_collection = MagicMock()
        mock_collection.insert_one = AsyncMock(side_effect=Exception("Insert failed"))
        db.__getitem__.return_value = mock_collection
        
        with patch('backend.database.AsyncIOMotorClient', return_value=client):
            database = Database()
            await database.connect()
            
            result = await database.create_user({"email": "test@example.com"})
            
            assert result is None


class TestDatabaseValidation:
    """Test input validation for database operations."""
    
    @pytest.mark.asyncio
    async def test_create_user_empty_data(self, mock_mongo_client):
        """Test user creation with empty data."""
        client, db = mock_mongo_client
        
        with patch('backend.database.AsyncIOMotorClient', return_value=client):
            database = Database()
            await database.connect()
            
            # Test with None and empty dict
            assert await database.create_user(None) is None
            assert await database.create_user({}) is None
    
    @pytest.mark.asyncio
    async def test_get_user_by_email_invalid_input(self, mock_mongo_client):
        """Test user retrieval with invalid email input."""
        client, db = mock_mongo_client
        
        with patch('backend.database.AsyncIOMotorClient', return_value=client):
            database = Database()
            await database.connect()
            
            # Test with None and empty string
            assert await database.get_user_by_email(None) is None
            assert await database.get_user_by_email("") is None
    
    @pytest.mark.asyncio
    async def test_create_message_invalid_data(self, mock_mongo_client):
        """Test message creation with invalid data."""
        client, db = mock_mongo_client
        
        with patch('backend.database.AsyncIOMotorClient', return_value=client):
            database = Database()
            await database.connect()
            
            # Test with None and empty dict
            assert await database.create_message(None) is None
            assert await database.create_message({}) is None