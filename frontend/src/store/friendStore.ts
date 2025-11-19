import { create } from 'zustand';
import { friendsAPI } from '../services/api';

export interface FriendRequest {
  id: string;
  sender_id: string;
  receiver_id: string;
  status: 'pending' | 'accepted' | 'rejected';
  created_at: string;
}

export interface User {
  id: string;
  username: string;
  display_name: string;
  avatar?: string;
  bio?: string;
  is_online?: boolean;
  last_seen?: string;
}

interface FriendState {
  friends: User[];
  pendingRequests: FriendRequest[];
  blockedUsers: User[];
  isLoading: boolean;
  
  fetchFriends: () => Promise<void>;
  fetchPendingRequests: () => Promise<void>;
  fetchBlockedUsers: () => Promise<void>;
  
  sendFriendRequest: (userId: string) => Promise<void>;
  acceptFriendRequest: (requestId: string) => Promise<void>;
  rejectFriendRequest: (requestId: string) => Promise<void>;
  blockUser: (userId: string) => Promise<void>;
  unblockUser: (userId: string) => Promise<void>;
}

export const useFriendStore = create<FriendState>((set, get) => ({
  friends: [],
  pendingRequests: [],
  blockedUsers: [],
  isLoading: false,

  fetchFriends: async () => {
    set({ isLoading: true });
    try {
      const response = await friendsAPI.getFriends();
      set({ friends: response.data });
    } catch (error) {
      console.error('Error fetching friends:', error);
    } finally {
      set({ isLoading: false });
    }
  },

  fetchPendingRequests: async () => {
    try {
      const response = await friendsAPI.getReceivedRequests();
      set({ pendingRequests: response.data });
    } catch (error) {
      console.error('Error fetching requests:', error);
    }
  },

  fetchBlockedUsers: async () => {
    try {
      const response = await friendsAPI.getBlockedUsers();
      set({ blockedUsers: response.data });
    } catch (error) {
      console.error('Error fetching blocked users:', error);
    }
  },

  sendFriendRequest: async (userId: string) => {
    try {
      await friendsAPI.sendRequest(userId);
      // Optionally refresh something or show toast
    } catch (error) {
      console.error('Error sending friend request:', error);
      throw error;
    }
  },

  acceptFriendRequest: async (requestId: string) => {
    try {
      await friendsAPI.acceptRequest(requestId);
      // Remove from pending and refresh friends
      set((state) => ({
        pendingRequests: state.pendingRequests.filter(r => r.id !== requestId)
      }));
      await get().fetchFriends();
    } catch (error) {
      console.error('Error accepting request:', error);
      throw error;
    }
  },

  rejectFriendRequest: async (requestId: string) => {
    try {
      await friendsAPI.rejectRequest(requestId);
      set((state) => ({
        pendingRequests: state.pendingRequests.filter(r => r.id !== requestId)
      }));
    } catch (error) {
      console.error('Error rejecting request:', error);
      throw error;
    }
  },

  blockUser: async (userId: string) => {
    try {
      await friendsAPI.blockUser(userId);
      // Refresh friends and blocked list
      await get().fetchFriends();
      await get().fetchBlockedUsers();
    } catch (error) {
      console.error('Error blocking user:', error);
      throw error;
    }
  },

  unblockUser: async (userId: string) => {
    try {
      await friendsAPI.unblockUser(userId);
      await get().fetchBlockedUsers();
    } catch (error) {
      console.error('Error unblocking user:', error);
      throw error;
    }
  },
}));
