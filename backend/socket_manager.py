import socketio
import logging
from typing import Dict, Set
from datetime import datetime

logger = logging.getLogger(__name__)

class SocketManager:
    def __init__(self):
        # Create Socket.IO server with CORS settings
        self.sio = socketio.AsyncServer(
            async_mode='asgi',
            cors_allowed_origins='*',
            logger=True,
            engineio_logger=True
        )
        
        # Track connected users: {user_id: {sid1, sid2, ...}}
        self.user_connections: Dict[str, Set[str]] = {}
        
        # Track user presence in chats: {chat_id: {user_id1, user_id2, ...}}
        self.chat_presence: Dict[str, Set[str]] = {}
        
        # Track typing indicators: {chat_id: {user_id1, user_id2, ...}}
        self.typing_users: Dict[str, Set[str]] = {}
        
        self._register_handlers()
    
    def _register_handlers(self):
        @self.sio.event
        async def connect(sid, environ):
            logger.info(f"Client connected: {sid}")
            await self.sio.emit('connected', {'sid': sid}, room=sid)
        
        @self.sio.event
        async def disconnect(sid):
            logger.info(f"Client disconnected: {sid}")
            # Remove user from all tracking
            user_id = None
            # Iterate over a copy to avoid modification during iteration
            for uid, sids in list(self.user_connections.items()):
                if sid in sids:
                    user_id = uid
                    sids.remove(sid)
                    # Remove the user entirely if no more connections
                    if not sids:
                        self.user_connections.pop(uid, None)
                    break
            
            if user_id:
                # Update user status only if no other connections exist
                if user_id not in self.user_connections:
                    from database import update_user
                    await update_user(user_id, {
                        'is_online': False,
                        'last_seen': datetime.utcnow()
                    })
                    
                    # Notify contacts
                    await self.broadcast_user_status(user_id, False)
        
        @self.sio.event
        async def authenticate(sid, data):
            """Authenticate user and register connection"""
            try:
                user_id = data.get('user_id')
                if not user_id:
                    await self.sio.emit('error', {'message': 'Invalid user_id'}, room=sid)
                    return
                
                # Register connection
                if user_id not in self.user_connections:
                    self.user_connections[user_id] = set()
                self.user_connections[user_id].add(sid)
                
                # Update user status
                from database import update_user
                await update_user(user_id, {'is_online': True, 'last_seen': datetime.utcnow()})
                
                logger.info(f"User {user_id} authenticated with session {sid}")
                await self.sio.emit('authenticated', {'user_id': user_id}, room=sid)
                
                # Notify contacts
                await self.broadcast_user_status(user_id, True)
                
            except Exception as e:
                logger.error(f"Authentication error: {e}")
                await self.sio.emit('error', {'message': str(e)}, room=sid)
        
        @self.sio.event
        async def join_chat(sid, data):
            """User joins a chat room"""
            try:
                chat_id = data.get('chat_id')
                user_id = data.get('user_id')
                
                if not chat_id or not user_id:
                    return
                
                # Join Socket.IO room
                await self.sio.enter_room(sid, chat_id)
                
                # Track presence
                if chat_id not in self.chat_presence:
                    self.chat_presence[chat_id] = set()
                self.chat_presence[chat_id].add(user_id)
                
                logger.info(f"User {user_id} joined chat {chat_id}")
                
                # Notify others in chat
                await self.sio.emit('user_joined', {
                    'user_id': user_id,
                    'chat_id': chat_id
                }, room=chat_id, skip_sid=sid)
                
            except Exception as e:
                logger.error(f"Join chat error: {e}")
        
        @self.sio.event
        async def leave_chat(sid, data):
            """User leaves a chat room"""
            try:
                chat_id = data.get('chat_id')
                user_id = data.get('user_id')
                
                if not chat_id or not user_id:
                    return
                
                # Leave Socket.IO room
                await self.sio.leave_room(sid, chat_id)
                
                # Remove from presence
                if chat_id in self.chat_presence:
                    self.chat_presence[chat_id].discard(user_id)
                
                # Stop typing if was typing
                if chat_id in self.typing_users:
                    self.typing_users[chat_id].discard(user_id)
                
                logger.info(f"User {user_id} left chat {chat_id}")
                
            except Exception as e:
                logger.error(f"Leave chat error: {e}")
        
        @self.sio.event
        async def typing(sid, data):
            """Handle typing indicator"""
            try:
                chat_id = data.get('chat_id')
                user_id = data.get('user_id')
                is_typing = data.get('is_typing', True)
                
                if not chat_id or not user_id:
                    return
                
                if chat_id not in self.typing_users:
                    self.typing_users[chat_id] = set()
                
                if is_typing:
                    self.typing_users[chat_id].add(user_id)
                else:
                    self.typing_users[chat_id].discard(user_id)
                
                # Broadcast to others in chat
                await self.sio.emit('user_typing', {
                    'user_id': user_id,
                    'chat_id': chat_id,
                    'is_typing': is_typing
                }, room=chat_id, skip_sid=sid)
                
            except Exception as e:
                logger.error(f"Typing indicator error: {e}")
    
    async def send_message_to_chat(self, chat_id: str, message_data: dict):
        """Send a message to all users in a chat"""
        try:
            await self.sio.emit('new_message', message_data, room=chat_id)
            logger.info(f"Message sent to chat {chat_id}")
        except Exception as e:
            logger.error(f"Error sending message to chat: {e}")
    
    async def send_message_to_user(self, user_id: str, event: str, data: dict):
        """Send a message to a specific user (all their connections)"""
        try:
            if user_id in self.user_connections:
                for sid in self.user_connections[user_id]:
                    await self.sio.emit(event, data, room=sid)
        except Exception as e:
            logger.error(f"Error sending message to user: {e}")
    
    async def broadcast_user_status(self, user_id: str, is_online: bool):
        """Broadcast user online/offline status to their contacts"""
        try:
            from database import get_user_by_id
            user = await get_user_by_id(user_id)
            
            if not user:
                return
            
            # Send status to all contacts
            contacts = user.get('contacts', [])
            for contact_id in contacts:
                await self.send_message_to_user(contact_id, 'user_status', {
                    'user_id': user_id,
                    'is_online': is_online,
                    'last_seen': user.get('last_seen').isoformat() if user.get('last_seen') else None
                })
        except Exception as e:
            logger.error(f"Error broadcasting user status: {e}")
    
    async def update_message_status(self, chat_id: str, message_id: str, status: str, user_id: str):
        """Broadcast message status update"""
        try:
            await self.sio.emit('message_status', {
                'message_id': message_id,
                'status': status,
                'user_id': user_id
            }, room=chat_id)
        except Exception as e:
            logger.error(f"Error updating message status: {e}")
    
    async def broadcast_reaction(self, chat_id: str, reaction_data: dict):
        """Broadcast message reaction to chat"""
        try:
            await self.sio.emit('message_reaction', reaction_data, room=chat_id)
        except Exception as e:
            logger.error(f"Error broadcasting reaction: {e}")

# Global socket manager instance
socket_manager = SocketManager()
