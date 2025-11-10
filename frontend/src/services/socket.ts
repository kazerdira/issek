import { io, Socket } from 'socket.io-client';
import Constants from 'expo-constants';
import { useChatStore } from '../store/chatStore';

const API_URL = Constants.expoConfig?.extra?.EXPO_PUBLIC_BACKEND_URL || process.env.EXPO_PUBLIC_BACKEND_URL;

class SocketService {
  private socket: Socket | null = null;
  private userId: string | null = null;
  private currentChatId: string | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private isConnecting = false;

  connect(userId: string) {
    if (this.isConnecting) {
      console.log('Connection already in progress');
      return;
    }

    if (this.socket?.connected && this.userId === userId) {
      console.log('Socket already connected for this user');
      return;
    }

    this.isConnecting = true;
    this.userId = userId;
    
    console.log('Connecting to socket server:', API_URL);
    
    this.socket = io(API_URL, {
      path: '/socket.io',
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: this.maxReconnectAttempts,
      timeout: 20000,
      autoConnect: true,
    });

    this.setupListeners();
  }

  private setupListeners() {
    if (!this.socket) return;

    this.socket.on('connect', () => {
      console.log('✅ Socket connected successfully');
      this.isConnecting = false;
      this.reconnectAttempts = 0;
      
      if (this.userId) {
        console.log('Authenticating user:', this.userId);
        this.authenticate(this.userId);
      }
    });

    this.socket.on('disconnect', (reason) => {
      console.log('❌ Socket disconnected:', reason);
      this.isConnecting = false;
      
      if (reason === 'io server disconnect') {
        // Server disconnected, try to reconnect
        this.socket?.connect();
      }
    });

    this.socket.on('connect_error', (error) => {
      console.error('Socket connection error:', error);
      this.isConnecting = false;
      this.reconnectAttempts++;
      
      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
        console.error('Max reconnection attempts reached');
      }
    });

    this.socket.on('authenticated', (data) => {
      console.log('✅ Socket authenticated:', data);
    });

    this.socket.on('joined_chat', (data) => {
      console.log('✅ Joined chat successfully:', data);
    });

    this.socket.on('new_message', (message) => {
      console.log('📨 New message received:', message);
      try {
        const { addMessage, updateLastMessage, incrementChatUnreadCount } = useChatStore.getState();
        
        // Add message to store (it will check for duplicates)
        addMessage(message.chat_id, message);
        console.log('Message added to store for chat:', message.chat_id);
        
        // Update last message in chat list
        updateLastMessage(message.chat_id, message);
        
        // Increment unread count if: 1) not the sender, 2) not currently viewing this chat
        const isInCurrentChat = this.currentChatId === message.chat_id;
        const isSender = message.sender_id === this.userId;
        
        if (!isSender && !isInCurrentChat) {
          incrementChatUnreadCount(message.chat_id);
          console.log(`Incremented unread count for chat ${message.chat_id}`);
        }
      } catch (error) {
        console.error('Error handling new message:', error);
      }
    });

    this.socket.on('message_edited', (data) => {
      console.log('✏️ Message edited:', data);
      const { updateMessage } = useChatStore.getState();
      updateMessage(data.chat_id, data.message_id, { 
        content: data.content,
        edited: true 
      });
    });

    this.socket.on('message_deleted', (data) => {
      console.log('🗑️ Message deleted:', data);
      const { updateMessage } = useChatStore.getState();
      updateMessage(data.chat_id, data.message_id, { 
        deleted: true,
        content: 'This message was deleted'
      });
    });

    this.socket.on('message_status', (data) => {
      console.log('📊 Message status update:', data);
      const { updateMessage } = useChatStore.getState();
      updateMessage(data.chat_id, data.message_id, { 
        status: data.status 
      });
    });

    this.socket.on('message_reaction', (data) => {
      console.log('❤️ Message reaction received:', data);
      console.log('  → Action:', data.action);
      console.log('  → Emoji:', data.emoji);
      console.log('  → User:', data.user_id);
      console.log('  → Full reactions from backend:', data.reactions);
      
      const { updateMessage } = useChatStore.getState();
      
      // Use the full reactions object from backend (source of truth)
      if (data.reactions !== undefined) {
        console.log('  → Updating with backend reactions:', data.reactions);
        updateMessage(data.chat_id, data.message_id, { reactions: data.reactions });
      } else {
        // Fallback: manual calculation (shouldn't happen with updated backend)
        console.warn('  ⚠️ No reactions object from backend, using fallback');
        const { messages } = useChatStore.getState();
        const chatMessages = messages[data.chat_id] || [];
        const message = chatMessages.find(m => m.id === data.message_id);
        
        if (message) {
          const reactions = { ...message.reactions };
          if (data.action === 'add') {
            if (!reactions[data.emoji]) {
              reactions[data.emoji] = [];
            }
            if (!reactions[data.emoji].includes(data.user_id)) {
              reactions[data.emoji].push(data.user_id);
            }
          } else if (data.action === 'remove') {
            if (reactions[data.emoji]) {
              reactions[data.emoji] = reactions[data.emoji].filter(
                uid => uid !== data.user_id
              );
              if (reactions[data.emoji].length === 0) {
                delete reactions[data.emoji];
              }
            }
          }
          updateMessage(data.chat_id, data.message_id, { reactions });
        }
      }
    });

    this.socket.on('user_typing', (data) => {
      console.log('⌨️ User typing:', data);
      const { setTypingUser } = useChatStore.getState();
      setTypingUser(data.chat_id, data.user_id, data.is_typing);
    });

    this.socket.on('user_status', (data) => {
      console.log('👤 User status update:', data);
      // You could update user status in a separate store if needed
    });

    this.socket.on('user_joined', (data) => {
      console.log('👋 User joined chat:', data);
    });

    this.socket.on('error', (error) => {
      console.error('⚠️ Socket error:', error);
    });
  }

  authenticate(userId: string) {
    if (!this.socket?.connected) {
      console.warn('Cannot authenticate: socket not connected');
      return;
    }
    console.log('Sending authentication for user:', userId);
    this.socket.emit('authenticate', { user_id: userId });
  }

  setCurrentChat(chatId: string | null) {
    this.currentChatId = chatId;
    console.log('Current chat set to:', chatId);
  }

  joinChat(chatId: string, userId: string) {
    if (!this.socket?.connected) {
      console.warn('Cannot join chat: socket not connected');
      return;
    }
    console.log('Joining chat:', chatId, 'for user:', userId);
    this.socket.emit('join_chat', { chat_id: chatId, user_id: userId });
    this.setCurrentChat(chatId);
  }

  leaveChat(chatId: string, userId: string) {
    if (!this.socket?.connected) {
      console.warn('Cannot leave chat: socket not connected');
      return;
    }
    console.log('Leaving chat:', chatId);
    this.socket.emit('leave_chat', { chat_id: chatId, user_id: userId });
    this.setCurrentChat(null);
  }

  sendTyping(chatId: string, userId: string, isTyping: boolean) {
    if (!this.socket?.connected) {
      return;
    }
    this.socket.emit('typing', { chat_id: chatId, user_id: userId, is_typing: isTyping });
  }

  isConnected(): boolean {
    return this.socket?.connected || false;
  }

  disconnect() {
    if (this.socket) {
      console.log('Disconnecting socket');
      this.socket.disconnect();
      this.socket = null;
      this.userId = null;
      this.isConnecting = false;
      this.reconnectAttempts = 0;
    }
  }

  getConnectionStatus(): string {
    if (!this.socket) return 'disconnected';
    if (this.socket.connected) return 'connected';
    if (this.isConnecting) return 'connecting';
    return 'disconnected';
  }
}

export const socketService = new SocketService();
