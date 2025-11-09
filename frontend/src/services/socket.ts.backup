import { io, Socket } from 'socket.io-client';
import Constants from 'expo-constants';
import { useChatStore } from '../store/chatStore';

const API_URL = Constants.expoConfig?.extra?.EXPO_PUBLIC_BACKEND_URL || process.env.EXPO_PUBLIC_BACKEND_URL;

class SocketService {
  private socket: Socket | null = null;
  private userId: string | null = null;

  connect(userId: string) {
    if (this.socket?.connected) {
      return;
    }

    this.userId = userId;
    
    this.socket = io(API_URL, {
      path: '/socket.io',
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: 5,
    });

    this.setupListeners();
  }

  private setupListeners() {
    if (!this.socket) return;

    this.socket.on('connect', () => {
      console.log('Socket connected');
      if (this.userId) {
        this.authenticate(this.userId);
      }
    });

    this.socket.on('disconnect', () => {
      console.log('Socket disconnected');
    });

    this.socket.on('authenticated', (data) => {
      console.log('Socket authenticated:', data);
    });

    this.socket.on('new_message', (message) => {
      console.log('New message received:', message);
      const { addMessage } = useChatStore.getState();
      addMessage(message.chat_id, message);
    });

    this.socket.on('message_status', (data) => {
      console.log('Message status update:', data);
      const { updateMessage } = useChatStore.getState();
      // Update message status in store
    });

    this.socket.on('message_reaction', (data) => {
      console.log('Message reaction:', data);
      // Handle reaction updates
    });

    this.socket.on('user_typing', (data) => {
      console.log('User typing:', data);
      const { setTypingUser } = useChatStore.getState();
      setTypingUser(data.chat_id, data.user_id, data.is_typing);
    });

    this.socket.on('user_status', (data) => {
      console.log('User status:', data);
      // Update user online/offline status
    });

    this.socket.on('error', (error) => {
      console.error('Socket error:', error);
    });
  }

  authenticate(userId: string) {
    this.socket?.emit('authenticate', { user_id: userId });
  }

  joinChat(chatId: string, userId: string) {
    this.socket?.emit('join_chat', { chat_id: chatId, user_id: userId });
  }

  leaveChat(chatId: string, userId: string) {
    this.socket?.emit('leave_chat', { chat_id: chatId, user_id: userId });
  }

  sendTyping(chatId: string, userId: string, isTyping: boolean) {
    this.socket?.emit('typing', { chat_id: chatId, user_id: userId, is_typing: isTyping });
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.userId = null;
    }
  }
}

export const socketService = new SocketService();
