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
  RefreshControl,
  SafeAreaView,
} from 'react-native';
import { useRouter } from 'expo-router';
import { usersAPI, chatsAPI } from '../../src/services/api';
import { Avatar } from '../../src/components/Avatar';
import { colors } from '../../src/theme/colors';
import { Ionicons } from '@expo/vector-icons';
import { useFriendStore, User, FriendRequest } from '../../src/store/friendStore';

type Tab = 'friends' | 'requests' | 'blocked';

export default function ContactsScreen() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<Tab>('friends');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<User[]>([]);
  const [searching, setSearching] = useState(false);
  
  const { 
    friends, 
    pendingRequests, 
    blockedUsers, 
    isLoading, 
    fetchFriends, 
    fetchPendingRequests, 
    fetchBlockedUsers,
    sendFriendRequest,
    acceptFriendRequest,
    rejectFriendRequest,
    blockUser,
    unblockUser
  } = useFriendStore();

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadData = async () => {
    await Promise.all([
      fetchFriends(),
      fetchPendingRequests(),
      fetchBlockedUsers()
    ]);
  };

  const handleSearch = async (query: string) => {
    setSearchQuery(query);
    if (query.length < 2) {
      setSearchResults([]);
      return;
    }

    setSearching(true);
    try {
      const response = await usersAPI.search(query);
      setSearchResults(response.data);
    } catch (error) {
      console.error('Error searching users:', error);
    } finally {
      setSearching(false);
    }
  };

  const handleStartChat = async (userId: string) => {
    try {
      const response = await chatsAPI.createChat({
        chat_type: 'direct',
        participants: [userId],
      });
      router.push(`/chat/${response.data.id}`);
    } catch (error) {
      Alert.alert('Error', 'Failed to create chat');
      console.error('Error creating chat:', error);
    }
  };

  const handleSendRequest = async (userId: string) => {
    try {
      await sendFriendRequest(userId);
      Alert.alert('Success', 'Friend request sent');
      handleSearch(searchQuery); // Refresh search results state if needed
    } catch (error: any) {
      const errorMessage = error?.response?.data?.detail || 'Failed to send request';
      Alert.alert('Error', errorMessage);
      console.error('Error sending friend request:', error);
    }
  };

  const handleBlock = async (userId: string) => {
    Alert.alert(
      'Block User',
      'Are you sure you want to block this user? They won\'t be able to message you.',
      [
        { text: 'Cancel', style: 'cancel' },
        { 
          text: 'Block', 
          style: 'destructive',
          onPress: async () => {
            try {
              await blockUser(userId);
              Alert.alert('Success', 'User blocked');
            } catch (error) {
              Alert.alert('Error', 'Failed to block user');
              console.error('Error blocking user:', error);
            }
          }
        }
      ]
    );
  };

  const renderUserItem = ({ item }: { item: User }) => {
    const isFriend = friends.some(f => f.id === item.id);
    const isBlocked = blockedUsers.some(u => u.id === item.id);
    const hasPending = pendingRequests.some(r => r.sender_id === item.id || r.receiver_id === item.id);

    return (
      <TouchableOpacity
        style={styles.userItem}
        onPress={() => handleStartChat(item.id)}
      >
        <Avatar
          uri={item.avatar}
          name={item.display_name}
          size={48}
          online={item.is_online}
        />
        <View style={styles.userInfo}>
          <Text style={styles.userName}>{item.display_name}</Text>
          <Text style={styles.userHandle}>@{item.username}</Text>
        </View>
        
        <View style={styles.actions}>
          {!isFriend && !isBlocked && !hasPending && (
            <TouchableOpacity 
              style={styles.actionButton}
              onPress={() => handleSendRequest(item.id)}
            >
              <Ionicons name="person-add" size={20} color={colors.primary} />
            </TouchableOpacity>
          )}
          
          {!isBlocked && (
            <TouchableOpacity 
              style={[styles.actionButton, { marginLeft: 8 }]}
              onPress={() => handleStartChat(item.id)}
            >
              <Ionicons name="chatbubble-outline" size={20} color={colors.primary} />
            </TouchableOpacity>
          )}

          {!isBlocked && (
             <TouchableOpacity 
               style={[styles.actionButton, { marginLeft: 8 }]}
               onPress={() => handleBlock(item.id)}
             >
               <Ionicons name="ban-outline" size={20} color={colors.error} />
             </TouchableOpacity>
          )}
        </View>
      </TouchableOpacity>
    );
  };

  const renderFriendItem = ({ item }: { item: User }) => (
    <TouchableOpacity
      style={styles.userItem}
      onPress={() => handleStartChat(item.id)}
    >
      <Avatar
        uri={item.avatar}
        name={item.display_name}
        size={48}
        online={item.is_online}
      />
      <View style={styles.userInfo}>
        <Text style={styles.userName}>{item.display_name}</Text>
        <Text style={styles.userHandle}>@{item.username}</Text>
      </View>
      <TouchableOpacity 
        style={styles.messageButton}
        onPress={() => handleStartChat(item.id)}
      >
        <Ionicons name="chatbubble" size={18} color={colors.textLight} />
        <Text style={styles.messageButtonText}>Message</Text>
      </TouchableOpacity>
    </TouchableOpacity>
  );

  const renderRequestItem = ({ item }: { item: FriendRequest }) => {
    // We need to fetch user details for the request, but for now let's assume we have basic info or fetch it
    // In a real app, the backend should return user details with the request or we fetch them.
    // For this demo, I'll assume the store or API handles this better, but let's just show ID for now if details missing
    // Actually, let's fetch user details on the fly or update the store to include them.
    // For now, let's just show a placeholder or fetch.
    // Ideally the backend endpoint `get_received_requests` should return user details.
    // Let's assume for now we might need to fix backend to return user details, but let's proceed with UI.
    
    return (
      <View style={styles.userItem}>
        <View style={styles.userInfo}>
          <Text style={styles.userName}>Request from {item.sender_id.substring(0, 8)}...</Text>
          <Text style={styles.userHandle}>Sent {new Date(item.created_at).toLocaleDateString()}</Text>
        </View>
        <View style={styles.actions}>
          <TouchableOpacity 
            style={[styles.actionButton, { backgroundColor: colors.primary }]}
            onPress={() => acceptFriendRequest(item.id)}
          >
            <Ionicons name="checkmark" size={20} color={colors.textLight} />
          </TouchableOpacity>
          <TouchableOpacity 
            style={[styles.actionButton, { marginLeft: 8, backgroundColor: colors.error }]}
            onPress={() => rejectFriendRequest(item.id)}
          >
            <Ionicons name="close" size={20} color={colors.textLight} />
          </TouchableOpacity>
        </View>
      </View>
    );
  };

  const renderBlockedItem = ({ item }: { item: User }) => (
    <View style={styles.userItem}>
      <Avatar
        uri={item.avatar}
        name={item.display_name}
        size={48}
      />
      <View style={styles.userInfo}>
        <Text style={styles.userName}>{item.display_name}</Text>
        <Text style={styles.userHandle}>@{item.username}</Text>
      </View>
      <TouchableOpacity 
        style={[styles.actionButton, { borderColor: colors.primary, borderWidth: 1 }]}
        onPress={() => unblockUser(item.id)}
      >
        <Text style={{ color: colors.primary, fontSize: 12, fontWeight: '600' }}>Unblock</Text>
      </TouchableOpacity>
    </View>
  );

  return (
    <View style={styles.container}>
      <SafeAreaView style={styles.safeAreaTop}>
        <View style={styles.searchContainer}>
          <View style={styles.searchBar}>
            <Ionicons name="search" size={20} color={colors.textSecondary} />
            <TextInput
              style={styles.searchInput}
              placeholder="Search users..."
              value={searchQuery}
              onChangeText={handleSearch}
              autoCapitalize="none"
            />
            {searching && <ActivityIndicator size="small" color={colors.primary} />}
          </View>
        </View>
      </SafeAreaView>

      {searchQuery.length >= 2 ? (
        <FlatList
          data={searchResults}
          renderItem={renderUserItem}
          keyExtractor={(item) => item.id}
          ListEmptyComponent={
            !searching ? (
              <View style={styles.emptyState}>
                <Text style={styles.emptyText}>No users found</Text>
              </View>
            ) : null
          }
        />
      ) : (
        <>
          <View style={styles.tabs}>
            <TouchableOpacity 
              style={[styles.tab, activeTab === 'friends' && styles.activeTab]}
              onPress={() => setActiveTab('friends')}
            >
              <Text style={[styles.tabText, activeTab === 'friends' && styles.activeTabText]}>Friends</Text>
            </TouchableOpacity>
            <TouchableOpacity 
              style={[styles.tab, activeTab === 'requests' && styles.activeTab]}
              onPress={() => setActiveTab('requests')}
            >
              <Text style={[styles.tabText, activeTab === 'requests' && styles.activeTabText]}>
                Requests {pendingRequests.length > 0 && `(${pendingRequests.length})`}
              </Text>
            </TouchableOpacity>
            <TouchableOpacity 
              style={[styles.tab, activeTab === 'blocked' && styles.activeTab]}
              onPress={() => setActiveTab('blocked')}
            >
              <Text style={[styles.tabText, activeTab === 'blocked' && styles.activeTabText]}>Blocked</Text>
            </TouchableOpacity>
          </View>

          {activeTab === 'friends' && (
            <FlatList
              data={friends}
              renderItem={renderFriendItem}
              keyExtractor={(item) => item.id}
              refreshControl={<RefreshControl refreshing={isLoading} onRefresh={loadData} />}
              ListEmptyComponent={
                <View style={styles.emptyState}>
                  <Ionicons name="people-outline" size={64} color={colors.textMuted} />
                  <Text style={styles.emptyText}>No friends yet</Text>
                  <Text style={styles.emptySubtext}>Search for users to add them</Text>
                </View>
              }
            />
          )}

          {activeTab === 'requests' && (
            <FlatList
              data={pendingRequests}
              renderItem={renderRequestItem}
              keyExtractor={(item) => item.id}
              refreshControl={<RefreshControl refreshing={isLoading} onRefresh={fetchPendingRequests} />}
              ListEmptyComponent={
                <View style={styles.emptyState}>
                  <Ionicons name="mail-unread-outline" size={64} color={colors.textMuted} />
                  <Text style={styles.emptyText}>No pending requests</Text>
                </View>
              }
            />
          )}

          {activeTab === 'blocked' && (
            <FlatList
              data={blockedUsers}
              renderItem={renderBlockedItem}
              keyExtractor={(item) => item.id}
              refreshControl={<RefreshControl refreshing={isLoading} onRefresh={fetchBlockedUsers} />}
              ListEmptyComponent={
                <View style={styles.emptyState}>
                  <Ionicons name="shield-checkmark-outline" size={64} color={colors.textMuted} />
                  <Text style={styles.emptyText}>No blocked users</Text>
                </View>
              }
            />
          )}
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  safeAreaTop: {
    backgroundColor: colors.background,
  },
  searchContainer: {
    padding: 16,
    backgroundColor: colors.background,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  searchBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: 12,
    paddingHorizontal: 12,
    height: 44,
  },
  searchInput: {
    flex: 1,
    marginLeft: 8,
    fontSize: 16,
    color: colors.text,
  },
  tabs: {
    flexDirection: 'row',
    padding: 12,
    backgroundColor: colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  tab: {
    flex: 1,
    paddingVertical: 8,
    alignItems: 'center',
    borderRadius: 20,
  },
  activeTab: {
    backgroundColor: colors.primary + '20', // 20% opacity
  },
  tabText: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.textSecondary,
  },
  activeTabText: {
    color: colors.primary,
  },
  userItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    backgroundColor: colors.surface,
  },
  userInfo: {
    flex: 1,
    marginLeft: 12,
  },
  userName: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 2,
  },
  userHandle: {
    fontSize: 14,
    color: colors.textSecondary,
  },
  actions: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  actionButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.background,
  },
  messageButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 20,
    backgroundColor: colors.primary,
    gap: 6,
  },
  messageButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.textLight,
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
    textAlign: 'center',
  },
});
