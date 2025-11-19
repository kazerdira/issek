import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  TextInput,
  StyleSheet,
  ActivityIndicator,
  Alert,
  SafeAreaView,
  RefreshControl,
} from 'react-native';
import { useRouter } from 'expo-router';
import { usersAPI, chatsAPI, friendsAPI } from '../../src/services/api';
import { Avatar } from '../../src/components/Avatar';
import { colors, spacing, borderRadius, typography, shadows, safeArea } from '../../src/theme/theme';
import { Ionicons } from '@expo/vector-icons';

interface SearchResult {
  type: 'user' | 'group' | 'channel';
  id: string;
  name: string;
  username?: string;
  avatar?: string;
  description?: string;
  member_count?: number;
  is_member?: boolean;
  is_friend?: boolean;
  is_public?: boolean;
}

interface Friend {
  id: string;
  username: string;
  display_name: string;
  avatar?: string;
  is_online: boolean;
}

interface FriendRequest {
  id: string;
  from_user: Friend;
  status: string;
  created_at: string;
}

export default function ContactsScreen() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [friends, setFriends] = useState<Friend[]>([]);
  const [friendRequests, setFriendRequests] = useState<FriendRequest[]>([]);
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<'friends' | 'requests'>('friends');

  useEffect(() => {
    loadFriends();
    loadFriendRequests();
  }, []);

  const loadFriends = async () => {
    try {
      setLoading(true);
      const response = await friendsAPI.getFriends();
      setFriends(response.data);
    } catch (error) {
      console.error('Error loading friends:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const loadFriendRequests = async () => {
    try {
      const response = await friendsAPI.getFriendRequests();
      setFriendRequests(response.data);
    } catch (error) {
      console.error('Error loading friend requests:', error);
    }
  };

  const handleSearch = async (query: string) => {
    setSearchQuery(query);
    if (query.length < 2) {
      setSearchResults([]);
      return;
    }

    setSearching(true);
    try {
      const response = await chatsAPI.searchGlobal(query);
      setSearchResults(response.data);
    } catch (error) {
      console.error('Error searching:', error);
    } finally {
      setSearching(false);
    }
  };

  const handleSendFriendRequest = async (userId: string) => {
    try {
      await friendsAPI.sendFriendRequest(userId);
      Alert.alert('Success', 'Friend request sent');
      handleSearch(searchQuery); // Refresh search results
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to send friend request');
    }
  };

  const handleAcceptRequest = async (requestId: string) => {
    try {
      await friendsAPI.acceptFriendRequest(requestId);
      loadFriends();
      loadFriendRequests();
      Alert.alert('Success', 'Friend request accepted');
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to accept request');
    }
  };

  const handleRejectRequest = async (requestId: string) => {
    try {
      await friendsAPI.rejectFriendRequest(requestId);
      loadFriendRequests();
      Alert.alert('Success', 'Friend request rejected');
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to reject request');
    }
  };

  const handleStartChat = async (user: Friend) => {
    try {
      const response = await chatsAPI.createChat({
        chat_type: 'direct',
        participant_ids: [user.id],
      });
      router.push(`/chat/${response.data.id}`);
    } catch (error: any) {
      Alert.alert('Error', 'Failed to create chat');
    }
  };

  const handleJoinChat = async (chatId: string, chatType: string) => {
    try {
      await chatsAPI.joinChat(chatId);
      Alert.alert('Success', `Joined ${chatType} successfully`);
      if (chatType === 'group' || chatType === 'channel') {
        router.push(`/chat/${chatId}`);
      }
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to join');
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadFriends();
    loadFriendRequests();
  };

  const renderSearchResult = ({ item }: { item: SearchResult }) => {
    if (item.type === 'user') {
      return (
        <View style={styles.resultItem}>
          <TouchableOpacity
            style={styles.resultContent}
            onPress={() => {
              if (item.is_friend) {
                handleStartChat({
                  id: item.id,
                  username: item.username || '',
                  display_name: item.name,
                  avatar: item.avatar,
                  is_online: false,
                });
              }
            }}
          >
            <Avatar
              uri={item.avatar}
              name={item.name}
              size={48}
            />
            <View style={styles.resultInfo}>
              <Text style={styles.resultName}>{item.name}</Text>
              {item.username && (
                <Text style={styles.resultHandle}>@{item.username}</Text>
              )}
            </View>
          </TouchableOpacity>
          
          {item.is_friend ? (
            <TouchableOpacity
              style={styles.actionButton}
              onPress={() => handleStartChat({
                id: item.id,
                username: item.username || '',
                display_name: item.name,
                avatar: item.avatar,
                is_online: false,
              })}
            >
              <Ionicons name="chatbubble" size={20} color={colors.primary} />
            </TouchableOpacity>
          ) : (
            <TouchableOpacity
              style={[styles.actionButton, styles.addButton]}
              onPress={() => handleSendFriendRequest(item.id)}
            >
              <Ionicons name="person-add" size={20} color={colors.textLight} />
            </TouchableOpacity>
          )}
        </View>
      );
    } else {
      // Group or Channel
      const isChannel = item.type === 'channel';
      return (
        <TouchableOpacity
          style={styles.resultItem}
          onPress={() => {
            if (item.is_member) {
              router.push(`/chat/${item.id}`);
            } else {
              handleJoinChat(item.id, item.type);
            }
          }}
        >
          <View style={styles.channelIcon}>
            {item.avatar ? (
              <Avatar uri={item.avatar} name={item.name} size={48} />
            ) : (
              <View style={styles.channelIconPlaceholder}>
                <Ionicons
                  name={isChannel ? 'megaphone' : 'people'}
                  size={24}
                  color={colors.primary}
                />
              </View>
            )}
          </View>
          
          <View style={styles.resultInfo}>
            <View style={styles.channelHeader}>
              <Text style={styles.resultName}>{item.name}</Text>
              {isChannel && (
                <View style={styles.channelBadge}>
                  <Text style={styles.channelBadgeText}>CHANNEL</Text>
                </View>
              )}
            </View>
            {item.description && (
              <Text style={styles.channelDescription} numberOfLines={1}>
                {item.description}
              </Text>
            )}
            <Text style={styles.memberCount}>
              {item.member_count || 0} {isChannel ? 'subscribers' : 'members'}
            </Text>
          </View>
          
          {!item.is_member && (
            <TouchableOpacity
              style={[styles.actionButton, styles.joinButton]}
              onPress={() => handleJoinChat(item.id, item.type)}
            >
              <Text style={styles.joinButtonText}>Join</Text>
            </TouchableOpacity>
          )}
        </TouchableOpacity>
      );
    }
  };

  const renderFriend = ({ item }: { item: Friend }) => (
    <TouchableOpacity
      style={styles.friendItem}
      onPress={() => handleStartChat(item)}
    >
      <Avatar
        uri={item.avatar}
        name={item.display_name}
        size={48}
        online={item.is_online}
      />
      <View style={styles.friendInfo}>
        <Text style={styles.friendName}>{item.display_name}</Text>
        <Text style={styles.friendHandle}>@{item.username}</Text>
      </View>
      <Ionicons name="chatbubble-outline" size={24} color={colors.primary} />
    </TouchableOpacity>
  );

  const renderFriendRequest = ({ item }: { item: FriendRequest }) => (
    <View style={styles.requestItem}>
      <Avatar
        uri={item.from_user.avatar}
        name={item.from_user.display_name}
        size={48}
      />
      <View style={styles.requestInfo}>
        <Text style={styles.requestName}>{item.from_user.display_name}</Text>
        <Text style={styles.requestHandle}>@{item.from_user.username}</Text>
      </View>
      <View style={styles.requestActions}>
        <TouchableOpacity
          style={[styles.requestButton, styles.acceptButton]}
          onPress={() => handleAcceptRequest(item.id)}
        >
          <Ionicons name="checkmark" size={20} color={colors.textLight} />
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.requestButton, styles.rejectButton]}
          onPress={() => handleRejectRequest(item.id)}
        >
          <Ionicons name="close" size={20} color={colors.textLight} />
        </TouchableOpacity>
      </View>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      {/* Search Bar */}
      <View style={styles.searchContainer}>
        <View style={styles.searchBar}>
          <Ionicons name="search" size={20} color={colors.textSecondary} />
          <TextInput
            style={styles.searchInput}
            placeholder="Search users, groups, channels..."
            value={searchQuery}
            onChangeText={handleSearch}
            autoCapitalize="none"
          />
          {searching && <ActivityIndicator size="small" color={colors.primary} />}
        </View>
      </View>

      {searchQuery.length >= 2 ? (
        /* Search Results */
        <FlatList
          data={searchResults}
          renderItem={renderSearchResult}
          keyExtractor={(item) => `${item.type}-${item.id}`}
          contentContainerStyle={styles.listContent}
          ListEmptyComponent={
            !searching ? (
              <View style={styles.emptyState}>
                <Ionicons name="search-outline" size={64} color={colors.textMuted} />
                <Text style={styles.emptyText}>No results found</Text>
              </View>
            ) : null
          }
        />
      ) : (
        /* Friends and Requests */
        <>
          {/* Tabs */}
          <View style={styles.tabs}>
            <TouchableOpacity
              style={[styles.tab, activeTab === 'friends' && styles.activeTab]}
              onPress={() => setActiveTab('friends')}
            >
              <Text style={[styles.tabText, activeTab === 'friends' && styles.activeTabText]}>
                Friends
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.tab, activeTab === 'requests' && styles.activeTab]}
              onPress={() => setActiveTab('requests')}
            >
              <Text style={[styles.tabText, activeTab === 'requests' && styles.activeTabText]}>
                Requests
              </Text>
              {friendRequests.length > 0 && (
                <View style={styles.badge}>
                  <Text style={styles.badgeText}>{friendRequests.length}</Text>
                </View>
              )}
            </TouchableOpacity>
          </View>

          {loading ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color={colors.primary} />
            </View>
          ) : activeTab === 'friends' ? (
            <FlatList
              data={friends}
              renderItem={renderFriend}
              keyExtractor={(item) => item.id}
              contentContainerStyle={styles.listContent}
              refreshControl={
                <RefreshControl
                  refreshing={refreshing}
                  onRefresh={handleRefresh}
                  tintColor={colors.primary}
                />
              }
              ListEmptyComponent={
                <View style={styles.emptyState}>
                  <Ionicons name="people-outline" size={64} color={colors.textMuted} />
                  <Text style={styles.emptyText}>No friends yet</Text>
                  <Text style={styles.emptySubtext}>Search for users to add friends</Text>
                </View>
              }
            />
          ) : (
            <FlatList
              data={friendRequests}
              renderItem={renderFriendRequest}
              keyExtractor={(item) => item.id}
              contentContainerStyle={styles.listContent}
              refreshControl={
                <RefreshControl
                  refreshing={refreshing}
                  onRefresh={handleRefresh}
                  tintColor={colors.primary}
                />
              }
              ListEmptyComponent={
                <View style={styles.emptyState}>
                  <Ionicons name="mail-outline" size={64} color={colors.textMuted} />
                  <Text style={styles.emptyText}>No pending requests</Text>
                </View>
              }
            />
          )}
        </>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  searchContainer: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.sm,
    paddingBottom: spacing.md,
    backgroundColor: colors.background,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  searchBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: borderRadius.md,
    paddingHorizontal: spacing.md,
    height: 44,
    gap: spacing.sm,
  },
  searchInput: {
    flex: 1,
    ...typography.body,
    color: colors.text,
  },
  tabs: {
    flexDirection: 'row',
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    backgroundColor: colors.background,
  },
  tab: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: spacing.md,
    gap: spacing.xs,
  },
  activeTab: {
    borderBottomWidth: 2,
    borderBottomColor: colors.primary,
  },
  tabText: {
    ...typography.body,
    color: colors.textSecondary,
  },
  activeTabText: {
    color: colors.primary,
    fontWeight: '600',
  },
  badge: {
    backgroundColor: colors.primary,
    borderRadius: 10,
    paddingHorizontal: 6,
    paddingVertical: 2,
    minWidth: 20,
    alignItems: 'center',
  },
  badgeText: {
    ...typography.caption,
    color: colors.textLight,
    fontWeight: '600',
  },
  listContent: {
    flexGrow: 1,
    paddingBottom: safeArea.bottom + safeArea.tabBar,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  resultItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  resultContent: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
  },
  resultInfo: {
    flex: 1,
    marginLeft: spacing.md,
  },
  resultName: {
    ...typography.body,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 2,
  },
  resultHandle: {
    ...typography.bodySmall,
    color: colors.textSecondary,
  },
  actionButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: colors.primary,
  },
  addButton: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  joinButton: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    backgroundColor: colors.primary,
    borderRadius: borderRadius.md,
    borderColor: colors.primary,
  },
  joinButtonText: {
    ...typography.bodySmall,
    fontWeight: '600',
    color: colors.textLight,
  },
  channelIcon: {
    width: 48,
    height: 48,
  },
  channelIconPlaceholder: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: colors.surface,
    alignItems: 'center',
    justifyContent: 'center',
  },
  channelHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginBottom: 2,
  },
  channelBadge: {
    backgroundColor: colors.primary,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  channelBadgeText: {
    ...typography.caption,
    fontSize: 10,
    fontWeight: '700',
    color: colors.textLight,
  },
  channelDescription: {
    ...typography.bodySmall,
    color: colors.textSecondary,
    marginBottom: 2,
  },
  memberCount: {
    ...typography.caption,
    color: colors.textMuted,
  },
  friendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  friendInfo: {
    flex: 1,
    marginLeft: spacing.md,
  },
  friendName: {
    ...typography.body,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 2,
  },
  friendHandle: {
    ...typography.bodySmall,
    color: colors.textSecondary,
  },
  requestItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  requestInfo: {
    flex: 1,
    marginLeft: spacing.md,
  },
  requestName: {
    ...typography.body,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 2,
  },
  requestHandle: {
    ...typography.bodySmall,
    color: colors.textSecondary,
  },
  requestActions: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  requestButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
  acceptButton: {
    backgroundColor: colors.success,
  },
  rejectButton: {
    backgroundColor: colors.error,
  },
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingTop: 100,
  },
  emptyText: {
    ...typography.h4,
    color: colors.textSecondary,
    marginTop: spacing.lg,
  },
  emptySubtext: {
    ...typography.bodySmall,
    color: colors.textMuted,
    marginTop: spacing.sm,
    textAlign: 'center',
  },
});
