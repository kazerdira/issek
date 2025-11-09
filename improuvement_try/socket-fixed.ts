import { io, Socket } from 'socket.io-client';
import Constants from 'expo-constants';
import { useChatStore } from '../store/chatStore';
import { useAuthStore } from '../store/authStore';

const API_URL = Constants.expoConfig?.extra?.EXPO_PUBLIC_BACKEND_URL || process.env.EXPO_PUBLIC_BACKEND_URL;

class SocketService {
  private socket: Socket | null = null;
  private userId: string | null = null;
  private currentChatId: string | null = null;

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
      const { addMessage, updateLastMessage, incrementChatUnreadCount } = useChatStore.getState();
      const { user } = useAuthStore.getState();
      
      // Add message to store (it will check for duplicates)
      addMessage(message.chat_id, message);
      
      // Update last message in chat list
      updateLastMessage(message.chat_id, message);
      
      // Increment unread count if message is from someone else and not in current chat
      if (message.sender_id !== user?.id && this.currentChatId !== message.chat_id) {
        incrementChatUnreadCount(message.chat_id);
      }
    });

    this.socket.on('message_edited', (data) => {
      console.log('Message edited:', data);
      const { updateMessage } = useChatStore.getState();
      updateMessage(data.chat_id, data.message_id, { 
        content: data.content, 
        edited: true 
      });
    });

    this.socket.on('message_deleted', (data) => {
      console.log('Message deleted:', data);
      const { updateMessage } = useChatStore.getState();
      updateMessage(data.chat_id, data.message_id, { 
        deleted: true, 
        content: 'This message was deleted' 
      });
    });

    this.socket.on('message_status', (data) => {
      console.log('Message status update:', data);
      const { updateMessage, messages } = useChatStore.getState();
      
      // Find the message to update
      const chatMessages = messages[data.chat_id] || [];
      const messageToUpdate = chatMessages.find(m => m.id === data.message_id);
      
      if (messageToUpdate) {
        const updates: any = { status: data.status };
        
        // Update read_by or delivered_to arrays
        if (data.status === 'read' && data.user_id) {
          const readBy = [...(messageToUpdate.read_by || [])];
          if (!readBy.includes(data.user_id)) {
            readBy.push(data.user_id);
          }
          updates.read_by = readBy;
        } else if (data.status === 'delivered' && data.user_id) {
          const deliveredTo = [...(messageToUpdate.delivered_to || [])];
          if (!deliveredTo.includes(data.user_id)) {
            deliveredTo.push(data.user_id);
          }
          updates.delivered_to = deliveredTo;
        }
        
        updateMessage(data.chat_id, data.message_id, updates);
      }
    });

    this.socket.on('message_reaction', (data) => {
      console.log('Message reaction:', data);
      const { updateMessage, messages } = useChatStore.getState();
      
      const chatMessages = messages[data.chat_id] || [];
      const messageToUpdate = chatMessages.find(m => m.id === data.message_id);
      
      if (messageToUpdate) {
        const reactions = { ...messageToUpdate.reactions };
        const emoji = data.emoji;
        
        if (data.action === 'add') {
          if (!reactions[emoji]) {
            reactions[emoji] = [];
          }
          if (!reactions[emoji].includes(data.user_id)) {
            reactions[emoji].push(data.user_id);
          }
        } else if (data.action === 'remove') {
          if (reactions[emoji]) {
            reactions[emoji] = reactions[emoji].filter(id => id !== data.user_id);
            if (reactions[emoji].length === 0) {
              delete reactions[emoji];
            }
          }
        }
        
        updateMessage(data.chat_id, data.message_id, { reactions });
      }
    });

    this.socket.on('user_typing', (data) => {
      console.log('User typing:', data);
      const { setTypingUser } = useChatStore.getState();
      setTypingUser(data.chat_id, data.user_id, data.is_typing);
    });

    this.socket.on('user_status', (data) => {
      console.log('User status:', data);
      const { chats, setChats, currentChat, setCurrentChat } = useChatStore.getState();
      
      // Update user status in chats list
      const updatedChats = chats.map(chat => {
        if (chat.participant_details) {
          const updatedParticipants = chat.participant_details.map(participant => {
            if (participant.id === data.user_id) {
              return {
                ...participant,
                is_online: data.is_online,
                last_seen: data.last_seen,
              };
            }
            return participant;
          });
          return { ...chat, participant_details: updatedParticipants };
        }
        return chat;
      });
      
      setChats(updatedChats);
      
      // Update current chat if needed
      if (currentChat && currentChat.participant_details) {
        const updatedParticipants = currentChat.participant_details.map(participant => {
          if (participant.id === data.user_id) {
            return {
              ...participant,
              is_online: data.is_online,
              last_seen: data.last_seen,
            };
          }
          return participant;
        });
        setCurrentChat({ ...currentChat, participant_details: updatedParticipants });
      }
    });

    this.socket.on('error', (error) => {
      console.error('Socket error:', error);
    });
  }

  authenticate(userId: string) {
    this.socket?.emit('authenticate', { user_id: userId });
  }

  joinChat(chatId: string, userId: string) {
    this.currentChatId = chatId;
    this.socket?.emit('join_chat', { chat_id: chatId, user_id: userId });
    
    // Reset unread count when joining chat
    const { resetChatUnreadCount } = useChatStore.getState();
    resetChatUnreadCount(chatId);
  }

  leaveChat(chatId: string, userId: string) {
    if (this.currentChatId === chatId) {
      this.currentChatId = null;
    }
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
      this.currentChatId = null;
    }
  }
}

export const socketService = new SocketService();
