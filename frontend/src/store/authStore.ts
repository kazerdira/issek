import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';

interface User {
  id: string;
  username: string;
  display_name: string;
  avatar?: string;
  bio?: string;
  phone_number?: string;
  email?: string;
  role: string;
  is_online: boolean;
  last_seen?: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  setUser: (user: User | null) => void;
  setToken: (token: string | null) => void;
  setRefreshToken: (refreshToken: string | null) => void;
  setLoading: (loading: boolean) => void;
  login: (token: string, refreshToken: string, user: User) => Promise<void>;
  logout: () => Promise<void>;
  loadAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  refreshToken: null,
  isLoading: true,
  isAuthenticated: false,

  setUser: (user) => set({ user, isAuthenticated: !!user }),
  
  setToken: (token) => set({ token }),
  
  setRefreshToken: (refreshToken) => set({ refreshToken }),
  
  setLoading: (isLoading) => set({ isLoading }),

  login: async (token: string, refreshToken: string, user: User) => {
    await AsyncStorage.setItem('token', token);
    await AsyncStorage.setItem('refreshToken', refreshToken);
    await AsyncStorage.setItem('user', JSON.stringify(user));
    set({ token, refreshToken, user, isAuthenticated: true, isLoading: false });
  },

  logout: async () => {
    await AsyncStorage.removeItem('token');
    await AsyncStorage.removeItem('refreshToken');
    await AsyncStorage.removeItem('user');
    set({ token: null, refreshToken: null, user: null, isAuthenticated: false, isLoading: false });
  },

  loadAuth: async () => {
    try {
      const token = await AsyncStorage.getItem('token');
      const refreshToken = await AsyncStorage.getItem('refreshToken');
      const userStr = await AsyncStorage.getItem('user');
      
      if (token && refreshToken && userStr) {
        const user = JSON.parse(userStr);
        set({ token, refreshToken, user, isAuthenticated: true, isLoading: false });
      } else {
        set({ isLoading: false });
      }
    } catch (error) {
      console.error('Error loading auth:', error);
      set({ isLoading: false });
    }
  },
}));
