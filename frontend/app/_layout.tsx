import React, { useEffect } from 'react';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useAuthStore } from '../src/store/authStore';
import { setAuthToken } from '../src/services/api';
import { socketService } from '../src/services/socket';

export default function RootLayout() {
  const { loadAuth, token, user } = useAuthStore();

  useEffect(() => {
    loadAuth();
  }, []);

  useEffect(() => {
    if (token) {
      setAuthToken(token);
      if (user) {
        socketService.connect(user.id);
      }
    } else {
      setAuthToken(null);
      socketService.disconnect();
    }
  }, [token, user]);

  return (
    <>
      <StatusBar style="auto" />
      <Stack
        screenOptions={{
          headerShown: false,
        }}
      >
        <Stack.Screen name="index" />
        <Stack.Screen name="(auth)/login" />
        <Stack.Screen name="(auth)/register" />
        <Stack.Screen name="(auth)/phone" />
        <Stack.Screen name="(tabs)" />
        <Stack.Screen name="chat/[id]" />
      </Stack>
    </>
  );
}
