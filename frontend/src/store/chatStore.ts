import { create } from 'zustand';

export interface Message {
  id: string;
  chat_id: string;
  sender_id: string;
  content: string;
  message_type: 'text' | 'image' | 'video' | 'audio' | 'file' | 'voice';
  status: 'sent' | 'delivered' | 'read';
  reactions: Record<string, string[]>;
  reply_to?: string;
  reply_to_message?: Message; // Populated replied message from backend
  media_url?: string;
  file_name?: string;
  created_at: string;
  updated_at: string;
  sender?: any;
  edited: boolean;
  deleted: boolean;
}

export interface Chat {
  id: string;
  chat_type: 'direct' | 'group';
  name?: string;
  description?: string;
  avatar?: string;
  participants: string[];
  participant_details?: any[];
  last_message?: any;
  unread_count: number;
  created_at: string;
  updated_at: string;
}

interface ChatState {
  chats: Chat[];
  currentChat: Chat | null;
  messages: Record<string, Message[]>;
  typingUsers: Record<string, string[]>;
  setChats: (chats: Chat[]) => void;
  setCurrentChat: (chat: Chat | null) => void;
  addChat: (chat: Chat) => void;
  updateChat: (chatId: string, updates: Partial<Chat>) => void;
  updateChatUnreadCount: (chatId: string, count: number) => void;
  incrementChatUnreadCount: (chatId: string) => void;
  resetChatUnreadCount: (chatId: string) => void;
  setMessages: (chatId: string, messages: Message[]) => void;
  addMessage: (chatId: string, message: Message) => void;
  updateMessage: (chatId: string, messageId: string, updates: Partial<Message>) => void;
  setTypingUser: (chatId: string, userId: string, isTyping: boolean) => void;
  updateLastMessage: (chatId: string, message: Message) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  chats: [],
  currentChat: null,
  messages: {},
  typingUsers: {},

  setChats: (chats) => set({ chats }),

  setCurrentChat: (currentChat) => set({ currentChat }),

  addChat: (chat) => set((state) => ({
    chats: [chat, ...state.chats],
  })),

  updateChat: (chatId, updates) => set((state) => ({
    chats: state.chats.map((chat) =>
      chat.id === chatId ? { ...chat, ...updates } : chat
    ),
    currentChat: state.currentChat?.id === chatId 
      ? { ...state.currentChat, ...updates } 
      : state.currentChat,
  })),

  updateChatUnreadCount: (chatId, count) => set((state) => ({
    chats: state.chats.map((chat) =>
      chat.id === chatId ? { ...chat, unread_count: count } : chat
    ),
  })),

  incrementChatUnreadCount: (chatId) => set((state) => ({
    chats: state.chats.map((chat) =>
      chat.id === chatId ? { ...chat, unread_count: (chat.unread_count || 0) + 1 } : chat
    ),
  })),

  resetChatUnreadCount: (chatId) => set((state) => ({
    chats: state.chats.map((chat) =>
      chat.id === chatId ? { ...chat, unread_count: 0 } : chat
    ),
  })),

  setMessages: (chatId, messages) => set((state) => ({
    messages: { ...state.messages, [chatId]: messages },
  })),

  addMessage: (chatId, message) => set((state) => {
    const chatMessages = state.messages[chatId] || [];
    
    // Check if message already exists (prevent duplicates)
    const messageExists = chatMessages.some(msg => msg.id === message.id);
    if (messageExists) {
      return state;
    }
    
    return {
      messages: {
        ...state.messages,
        [chatId]: [...chatMessages, message],
      },
    };
  }),

  updateMessage: (chatId, messageId, updates) => set((state) => {
    const chatMessages = state.messages[chatId] || [];
    return {
      messages: {
        ...state.messages,
        [chatId]: chatMessages.map((msg) =>
          msg.id === messageId ? { ...msg, ...updates } : msg
        ),
      },
    };
  }),

  setTypingUser: (chatId, userId, isTyping) => set((state) => {
    const typingInChat = state.typingUsers[chatId] || [];
    const updated = isTyping
      ? [...typingInChat.filter((id) => id !== userId), userId]
      : typingInChat.filter((id) => id !== userId);
    
    return {
      typingUsers: {
        ...state.typingUsers,
        [chatId]: updated,
      },
    };
  }),

  updateLastMessage: (chatId, message) => set((state) => ({
    chats: state.chats.map((chat) =>
      chat.id === chatId 
        ? { 
            ...chat, 
            last_message: {
              content: message.content,
              created_at: message.created_at,
              sender_id: message.sender_id,
              message_type: message.message_type,
            },
            updated_at: message.created_at,
          } 
        : chat
    ),
  })),
}));
