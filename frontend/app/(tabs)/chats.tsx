import React, { useEffect, useState, useCallback } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  RefreshControl,
  Platform,
  BackHandler,
  SafeAreaView,
} from 'react-native';
import { useRouter, useFocusEffect } from 'expo-router';
import { useChatStore, Chat } from '../../src/store/chatStore';
import { chatsAPI } from '../../src/services/api';
import { Avatar } from '../../src/components/Avatar';
import { colors, safeArea } from '../../src/theme/colors';
import { Ionicons } from '@expo/vector-icons';
import { format } from 'date-fns';
import { useAuthStore } from '../../src/store/authStore';

export default function ChatsScreen() {
  const router = useRouter();
  const { chats, setChats } = useChatStore();
  const { user } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Handle Android back button
  useFocusEffect(
    useCallback(() => {
      const onBackPress = () => {
        // Return true to prevent default back behavior (exit app)
        // Return false to allow default back behavior
        return true; // Stay on this screen
      };

      if (Platform.OS === 'android') {
        const subscription = BackHandler.addEventListener('hardwareBackPress', onBackPress);
        return () => subscription.remove();
      }
    }, [])
  );

  // Reload chats when screen comes into focus
  useFocusEffect(
    useCallback(() => {
      console.log('Chats screen focused, reloading chats');
      loadChats();
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])
  );

  useEffect(() => {
    loadChats();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadChats = async () => {
    try {
      const response = await chatsAPI.getChats();
      setChats(response.data);
      console.log(`Loaded ${response.data.length} chats`);
    } catch (error) {
      console.error('Error loading chats:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadChats();
  };

  const handleCreateChat = () => {
    router.push('/chat/create');
  };

  const handleChatPress = (chatId: string) => {
    console.log('Navigating to chat:', chatId);
    router.push(`/chat/${chatId}`);
  };

  const getChatName = (chat: Chat) => {
    if (chat.chat_type === 'group' || chat.chat_type === 'channel') {
      return chat.name || (chat.chat_type === 'channel' ? 'Channel' : 'Group Chat');
    }
    // For direct chats, show the other user's name
    const otherUser = chat.participant_details?.find((p) => p.id !== user?.id);
    return otherUser?.display_name || 'Unknown';
  };

  const getChatAvatar = (chat: Chat) => {
    if (chat.chat_type === 'group' || chat.chat_type === 'channel') {
      return chat.avatar;
    }
    const otherUser = chat.participant_details?.find((p) => p.id !== user?.id);
    return otherUser?.avatar;
  };

  const getChatOnlineStatus = (chat: Chat) => {
    if (chat.chat_type === 'group' || chat.chat_type === 'channel') return false;
    const otherUser = chat.participant_details?.find((p) => p.id !== user?.id);
    return otherUser?.is_online || false;
  };

  const getLastMessagePreview = (chat: Chat) => {
    if (!chat.last_message) return 'No messages yet';
    
    const content = chat.last_message.content;
    const messageType = chat.last_message.message_type;
    
    if (messageType === 'image') return '📷 Image';
    if (messageType === 'video') return '🎥 Video';
    if (messageType === 'audio') return '🎵 Audio';
    if (messageType === 'file') return '📎 File';
    if (messageType === 'voice') return '🎤 Voice message';
    
    return content || 'Message';
  };

  const renderChat = ({ item }: { item: Chat }) => {
    const lastMessageTime = item.last_message?.created_at
      ? format(new Date(item.last_message.created_at), 'HH:mm')
      : '';

    const unreadCount = item.unread_count || 0;
    const hasUnread = unreadCount > 0;

    return (
      <TouchableOpacity
        style={[styles.chatItem, hasUnread && styles.chatItemUnread]}
        onPress={() => handleChatPress(item.id)}
        activeOpacity={0.7}
      >
        <Avatar
          uri={getChatAvatar(item)}
          name={getChatName(item)}
          size={56}
          online={getChatOnlineStatus(item)}
        />

        <View style={styles.chatInfo}>
          <View style={styles.chatHeader}>
            <Text style={[styles.chatName, hasUnread && styles.chatNameUnread]} numberOfLines={1}>
              {getChatName(item)}
            </Text>
            {lastMessageTime && (
              <Text style={[styles.chatTime, hasUnread && styles.chatTimeUnread]}>
                {lastMessageTime}
              </Text>
            )}
          </View>

          <View style={styles.chatFooter}>
            <Text 
              style={[styles.chatMessage, hasUnread && styles.chatMessageUnread]} 
              numberOfLines={1}
            >
              {getLastMessagePreview(item)}
            </Text>
            {hasUnread && (
              <View style={styles.unreadBadge}>
                <Text style={styles.unreadText}>
                  {unreadCount > 99 ? '99+' : unreadCount}
                </Text>
              </View>
            )}
          </View>
        </View>
      </TouchableOpacity>
    );
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  // Sort chats by last message timestamp (newest first)
  const sortedChats = [...chats].sort((a, b) => {
    const aTime = a.last_message?.created_at ? new Date(a.last_message.created_at).getTime() : 0;
    const bTime = b.last_message?.created_at ? new Date(b.last_message.created_at).getTime() : 0;
    return bTime - aTime; // Descending order (newest first)
  });

  return (
    <View style={styles.container}>
      <SafeAreaView style={styles.safeAreaTop}>
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Chats</Text>
          <TouchableOpacity onPress={handleCreateChat} style={styles.createButton}>
            <Ionicons name="people-circle-outline" size={28} color={colors.primary} />
          </TouchableOpacity>
        </View>
      </SafeAreaView>

      <FlatList
        data={sortedChats}
        renderItem={renderChat}
        keyExtractor={(item) => item.id}
        contentContainerStyle={sortedChats.length === 0 ? styles.emptyContainer : undefined}
        ListEmptyComponent={
          <View style={styles.emptyState}>
            <Ionicons name="chatbubbles-outline" size={64} color={colors.textMuted} />
            <Text style={styles.emptyText}>No chats yet</Text>
            <Text style={styles.emptySubtext}>Start a conversation from Contacts</Text>
          </View>
        }
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            tintColor={colors.primary}
          />
        }
      />

      <TouchableOpacity
        style={styles.fab}
        onPress={() => router.push('/(tabs)/contacts')}
        activeOpacity={0.8}
      >
        <Ionicons name="create" size={24} color={colors.textLight} />
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    paddingTop: safeArea.top,
  },
  safeAreaTop: {
    backgroundColor: colors.surface,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 16,
    backgroundColor: colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: colors.text,
  },
  createButton: {
    padding: 8,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.background,
  },
  chatItem: {
    flexDirection: 'row',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    backgroundColor: colors.background,
  },
  chatInfo: {
    flex: 1,
    marginLeft: 12,
    justifyContent: 'center',
  },
  chatHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  chatName: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
    flex: 1,
  },
  chatTime: {
    fontSize: 12,
    color: colors.textSecondary,
    marginLeft: 8,
  },
  chatFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  chatMessage: {
    fontSize: 14,
    color: colors.textSecondary,
    flex: 1,
  },
  chatItemUnread: {
    backgroundColor: colors.surface,
  },
  chatNameUnread: {
    fontWeight: '600',
    color: colors.text,
  },
  chatTimeUnread: {
    fontWeight: '600',
    color: colors.primary,
  },
  chatMessageUnread: {
    fontWeight: '500',
    color: colors.text,
  },
  unreadBadge: {
    backgroundColor: colors.primary,
    borderRadius: 12,
    paddingHorizontal: 8,
    paddingVertical: 2,
    marginLeft: 8,
    minWidth: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  unreadText: {
    color: colors.textLight,
    fontSize: 12,
    fontWeight: '600',
  },
  emptyContainer: {
    flex: 1,
  },
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingTop: 100,
  },
  emptyText: {
    fontSize: 18,
    fontWeight: '600',
    color: colors.textSecondary,
    marginTop: 16,
  },
  emptySubtext: {
    fontSize: 14,
    color: colors.textMuted,
    marginTop: 8,
  },
  fab: {
    position: 'absolute',
    right: 20,
    bottom: 20,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.primary,
    justifyContent: 'center',
    alignItems: 'center',
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
  },
});
