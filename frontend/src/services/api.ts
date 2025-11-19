import axios from 'axios';
import Constants from 'expo-constants';

const API_URL = Constants.expoConfig?.extra?.EXPO_PUBLIC_BACKEND_URL || process.env.EXPO_PUBLIC_BACKEND_URL;

console.log('🔧 API Configuration:', {
  API_URL,
  baseURL: `${API_URL}/api`,
  expoConfig: Constants.expoConfig?.extra?.EXPO_PUBLIC_BACKEND_URL,
  processEnv: process.env.EXPO_PUBLIC_BACKEND_URL
});

export const api = axios.create({
  baseURL: `${API_URL}/api`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    // Token will be set dynamically
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized
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

// Auth API
export const authAPI = {
  register: (data: any) => api.post('/auth/register', data),
  login: (data: any) => api.post('/auth/login', data),
  refresh: (refreshToken: string) => api.post('/auth/refresh', { refresh_token: refreshToken }),
  requestOTP: (phone_number: string) => api.post('/auth/request-otp', { phone_number }),
  verifyOTP: (phone_number: string, otp: string) => api.post('/auth/verify-otp', { phone_number, otp }),
  getMe: () => api.get('/auth/me'),
  updateProfile: (data: any) => api.put('/auth/profile', data),
};

// Users API
export const usersAPI = {
  search: (query: string) => api.get(`/users/search?q=${encodeURIComponent(query)}`),
  getUser: (userId: string) => api.get(`/users/${userId}`),
  addContact: (userId: string) => api.post(`/users/contacts/${userId}`),
  removeContact: (userId: string) => api.delete(`/users/contacts/${userId}`),
  getContacts: () => api.get('/users/contacts'),
};

// Friends API
export const friendsAPI = {
  sendRequest: (userId: string) => api.post(`/friends/request/${userId}`),
  acceptRequest: (requestId: string) => api.post(`/friends/request/${requestId}/accept`),
  rejectRequest: (requestId: string) => api.post(`/friends/request/${requestId}/reject`),
  getReceivedRequests: () => api.get('/friends/requests/received'),
  getFriends: () => api.get('/friends/list'),
  blockUser: (userId: string) => api.post(`/friends/block/${userId}`),
  unblockUser: (userId: string) => api.post(`/friends/unblock/${userId}`),
  getBlockedUsers: () => api.get('/friends/blocked'),
};

// Chats API
export const chatsAPI = {
  getChats: () => api.get('/chats'),
  getChat: (chatId: string) => api.get(`/chats/${chatId}`),
  createChat: (data: any) => api.post('/chats', data),
  getMessages: (chatId: string, limit = 50, skip = 0) => 
    api.get(`/chats/${chatId}/messages?limit=${limit}&skip=${skip}`),
  sendMessage: (chatId: string, data: any) => api.post(`/chats/${chatId}/messages`, data),
  editMessage: (messageId: string, content: string) => 
    api.put(`/chats/messages/${messageId}?content=${encodeURIComponent(content)}`),
  deleteMessage: (messageId: string) => 
    api.delete(`/chats/messages/${messageId}`),
  addReaction: (messageId: string, emoji: string) => 
    api.post(`/chats/messages/${messageId}/react`, { emoji }),
  removeReaction: (messageId: string, emoji: string) => 
    api.delete(`/chats/messages/${messageId}/react?emoji=${encodeURIComponent(emoji)}`),
  pinMessage: (messageId: string) => 
    api.post(`/chats/messages/${messageId}/pin`),
  unpinMessage: (messageId: string) => 
    api.delete(`/chats/messages/${messageId}/pin`),
  forwardMessages: (chatId: string, fromChatId: string, messageIds: string[]) => {
    const params = new URLSearchParams();
    params.append('from_chat_id', fromChatId);
    messageIds.forEach(id => params.append('message_ids', id));
    return api.post(`/chats/${chatId}/forward?${params.toString()}`);
  },
  markAsRead: (messageId: string) => api.post(`/chats/messages/${messageId}/read`),
  
  // Group/Channel Management
  updateChat: (chatId: string, data: any) => api.put(`/chats/${chatId}`, data),
  addParticipants: (chatId: string, userIds: string[]) => api.post(`/chats/${chatId}/participants`, userIds),
  removeParticipant: (chatId: string, userId: string) => api.delete(`/chats/${chatId}/participants/${userId}`),
  promoteAdmin: (chatId: string, userId: string) => api.post(`/chats/${chatId}/admins/${userId}`),
  demoteAdmin: (chatId: string, userId: string) => api.delete(`/chats/${chatId}/admins/${userId}`),
};
