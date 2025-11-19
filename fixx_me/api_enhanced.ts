import axios from 'axios';
import Constants from 'expo-constants';

const API_URL = Constants.expoConfig?.extra?.EXPO_PUBLIC_BACKEND_URL || process.env.EXPO_PUBLIC_BACKEND_URL;

export const api = axios.create({
  baseURL: `${API_URL}/api`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      console.log('Unauthorized request');
    }
    return Promise.reject(error);
  }
);

export const setAuthToken = (token: string | null) => {
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common['Authorization'];
  }
};

// ============ Auth API ============
export const authAPI = {
  register: (data: any) => api.post('/auth/register', data),
  login: (data: any) => api.post('/auth/login', data),
  requestOTP: (phone_number: string) => api.post('/auth/request-otp', { phone_number }),
  verifyOTP: (phone_number: string, otp: string) => api.post('/auth/verify-otp', { phone_number, otp }),
  getMe: () => api.get('/auth/me'),
  updateProfile: (data: any) => api.put('/auth/profile', data),
};

// ============ Friends API ============
export const friendsAPI = {
  // Friend requests
  sendFriendRequest: (to_user_id: string) => 
    api.post('/friends/request', { to_user_id }),
  acceptFriendRequest: (request_id: string) => 
    api.post(`/friends/accept/${request_id}`),
  rejectFriendRequest: (request_id: string) => 
    api.post(`/friends/reject/${request_id}`),
  getFriendRequests: () => 
    api.get('/friends/requests/received'),
  
  // Friends management
  getFriends: () => api.get('/friends/list'),
  removeFriend: (user_id: string) => 
    api.delete(`/friends/remove/${user_id}`),
  
  // Blocking
  blockUser: (user_id: string) => 
    api.post(`/friends/block/${user_id}`),
  unblockUser: (user_id: string) => 
    api.delete(`/friends/unblock/${user_id}`),
  getBlockedUsers: () => 
    api.get('/friends/blocked'),
};

// ============ Users API ============
export const usersAPI = {
  search: (query: string) => 
    api.get(`/users/search?q=${encodeURIComponent(query)}`),
  getUser: (userId: string) => 
    api.get(`/users/${userId}`),
};

// ============ Chats API (Enhanced with Groups & Channels) ============
export const chatsAPI = {
  // Global search (users, groups, channels)
  searchGlobal: (query: string) => 
    api.get(`/chats/search?q=${encodeURIComponent(query)}`),
  
  // Basic chat operations
  getChats: () => api.get('/chats'),
  getChat: (chatId: string) => api.get(`/chats/${chatId}`),
  createChat: (data: {
    chat_type: 'direct' | 'group' | 'channel';
    name?: string;
    description?: string;
    is_public?: boolean;
    username?: string;
    participant_ids?: string[];
  }) => api.post('/chats', data),
  
  // Join/Leave
  joinChat: (chatId: string) => 
    api.post(`/chats/${chatId}/join`),
  leaveChat: (chatId: string) => 
    api.post(`/chats/${chatId}/leave`),
  
  // Messages
  getMessages: (chatId: string, limit = 50, skip = 0) => 
    api.get(`/chats/${chatId}/messages?limit=${limit}&skip=${skip}`),
  sendMessage: (chatId: string, data: any) => 
    api.post(`/chats/${chatId}/messages`, data),
  editMessage: (messageId: string, content: string) => 
    api.put(`/chats/messages/${messageId}`, { content }),
  deleteMessage: (messageId: string, forEveryone = false) => 
    api.delete(`/chats/messages/${messageId}?for_everyone=${forEveryone}`),
  markAsRead: (messageId: string) => 
    api.post(`/chats/messages/${messageId}/read`),
  
  // Reactions
  addReaction: (messageId: string, emoji: string) => 
    api.post(`/chats/messages/${messageId}/react`, { message_id: messageId, emoji }),
  removeReaction: (messageId: string, emoji: string) => 
    api.delete(`/chats/messages/${messageId}/react`, { data: { message_id: messageId, emoji } }),
  
  // Admin operations
  inviteUsers: (chatId: string, user_ids: string[]) => 
    api.post(`/chats/${chatId}/invite`, { chat_id: chatId, user_ids }),
  removeUser: (chatId: string, userId: string) => 
    api.post(`/chats/${chatId}/remove/${userId}`),
  banUser: (chatId: string, userId: string, reason?: string) => 
    api.post(`/chats/${chatId}/ban`, { chat_id: chatId, user_id: userId, reason }),
  unbanUser: (chatId: string, userId: string) => 
    api.post(`/chats/${chatId}/unban/${userId}`),
  promoteToAdmin: (chatId: string, userId: string, permissions?: string[]) => {
    const url = `/chats/${chatId}/promote/${userId}`;
    return permissions 
      ? api.post(`${url}?${permissions.map(p => `permissions=${p}`).join('&')}`)
      : api.post(url);
  },
  demoteAdmin: (chatId: string, userId: string) => 
    api.post(`/chats/${chatId}/demote/${userId}`),
  
  // Chat settings
  updateChatInfo: (chatId: string, data: {
    name?: string;
    description?: string;
    avatar?: string;
  }) => api.put(`/chats/${chatId}/info`, data),
  updatePermissions: (chatId: string, userId: string, permissions: any) => 
    api.put(`/chats/${chatId}/permissions/${userId}`, permissions),
  pinMessage: (chatId: string, messageId: string) => 
    api.post(`/chats/${chatId}/pin/${messageId}`),
  unpinMessage: (chatId: string, messageId: string) => 
    api.delete(`/chats/${chatId}/pin/${messageId}`),
};

// ============ Channels API (Specific) ============
export const channelsAPI = {
  create: (data: {
    name: string;
    description?: string;
    is_public?: boolean;
    username?: string;
  }) => api.post('/chats', { ...data, chat_type: 'channel' }),
  
  getChannelInfo: (chatId: string) => 
    api.get(`/chats/${chatId}`),
  
  subscribe: (chatId: string) => 
    api.post(`/chats/${chatId}/join`),
  
  unsubscribe: (chatId: string) => 
    api.post(`/chats/${chatId}/leave`),
  
  post: (chatId: string, content: string, messageType = 'text') => 
    api.post(`/chats/${chatId}/messages`, {
      chat_id: chatId,
      content,
      message_type: messageType,
    }),
};

// ============ Groups API (Specific) ============
export const groupsAPI = {
  create: (data: {
    name: string;
    description?: string;
    is_public?: boolean;
    username?: string;
    participant_ids?: string[];
  }) => api.post('/chats', { ...data, chat_type: 'group' }),
  
  getGroupInfo: (chatId: string) => 
    api.get(`/chats/${chatId}`),
  
  join: (chatId: string) => 
    api.post(`/chats/${chatId}/join`),
  
  leave: (chatId: string) => 
    api.post(`/chats/${chatId}/leave`),
  
  addMembers: (chatId: string, userIds: string[]) => 
    api.post(`/chats/${chatId}/invite`, { chat_id: chatId, user_ids: userIds }),
  
  removeMember: (chatId: string, userId: string) => 
    api.post(`/chats/${chatId}/remove/${userId}`),
};
