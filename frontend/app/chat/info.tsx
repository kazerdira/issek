import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  TextInput,
  Switch,
  ActivityIndicator,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { useChatStore } from '../../src/store/chatStore';
import { useAuthStore } from '../../src/store/authStore';
import { chatsAPI, friendsAPI } from '../../src/services/api';
import { Avatar } from '../../src/components/Avatar';
import { colors } from '../../src/theme/colors';
import { Ionicons } from '@expo/vector-icons';

export default function ChatInfoScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams();
  const chatId = typeof id === 'string' ? id : id[0];
  
  const { currentChat, setCurrentChat } = useChatStore();
  const { user } = useAuthStore();
  
  const [isEditing, setIsEditing] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [onlyAdminsPost, setOnlyAdminsPost] = useState(false);
  const [loading, setLoading] = useState(false);
  const [friends, setFriends] = useState<any[]>([]);
  const [showAddMembers, setShowAddMembers] = useState(false);

  const isAdmin = currentChat?.admins?.includes(user?.id || '');
  const isGroup = currentChat?.chat_type === 'group' || currentChat?.chat_type === 'channel';

  useEffect(() => {
    if (currentChat) {
      setName(currentChat.name || '');
      setDescription(currentChat.description || '');
      setOnlyAdminsPost(currentChat.only_admins_can_post || false);
    }
  }, [currentChat]);

  const handleSaveInfo = async () => {
    if (!name.trim()) {
      Alert.alert('Error', 'Name cannot be empty');
      return;
    }
    
    try {
      setLoading(true);
      const response = await chatsAPI.updateChat(chatId, {
        name,
        description,
        only_admins_can_post: onlyAdminsPost,
      });
      setCurrentChat(response.data);
      setIsEditing(false);
      Alert.alert('Success', 'Chat info updated');
    } catch (error) {
      console.error('Error updating chat:', error);
      Alert.alert('Error', 'Failed to update chat info');
    } finally {
      setLoading(false);
    }
  };

  const handleLeaveChat = async () => {
    Alert.alert(
      'Leave Chat',
      'Are you sure you want to leave this chat?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Leave',
          style: 'destructive',
          onPress: async () => {
            try {
              setLoading(true);
              await chatsAPI.removeParticipant(chatId, user?.id || '');
              router.replace('/(tabs)/chats');
            } catch (error) {
              console.error('Error leaving chat:', error);
              Alert.alert('Error', 'Failed to leave chat');
            } finally {
              setLoading(false);
            }
          },
        },
      ]
    );
  };

  const handleRemoveParticipant = async (participantId: string) => {
    Alert.alert(
      'Remove User',
      'Are you sure you want to remove this user?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Remove',
          style: 'destructive',
          onPress: async () => {
            try {
              const response = await chatsAPI.removeParticipant(chatId, participantId);
              setCurrentChat(response.data);
            } catch (error) {
              console.error('Error removing participant:', error);
              Alert.alert('Error', 'Failed to remove participant');
            }
          },
        },
      ]
    );
  };

  const handlePromoteAdmin = async (participantId: string) => {
    try {
      const response = await chatsAPI.promoteAdmin(chatId, participantId);
      setCurrentChat(response.data);
      Alert.alert('Success', 'User promoted to admin');
    } catch (error) {
      console.error('Error promoting admin:', error);
      Alert.alert('Error', 'Failed to promote user');
    }
  };

  const handleDemoteAdmin = async (participantId: string) => {
    try {
      const response = await chatsAPI.demoteAdmin(chatId, participantId);
      setCurrentChat(response.data);
      Alert.alert('Success', 'User demoted from admin');
    } catch (error) {
      console.error('Error demoting admin:', error);
      Alert.alert('Error', 'Failed to demote user');
    }
  };

  const loadFriends = async () => {
    try {
      const response = await friendsAPI.getFriends();
      // Filter out existing participants
      const existingIds = currentChat?.participants || [];
      const availableFriends = response.data.filter((f: any) => !existingIds.includes(f.id));
      setFriends(availableFriends);
      setShowAddMembers(true);
    } catch (error) {
      console.error('Error loading friends:', error);
    }
  };

  const handleAddMember = async (friendId: string) => {
    try {
      const response = await chatsAPI.addParticipants(chatId, [friendId]);
      setCurrentChat(response.data);
      setShowAddMembers(false);
      Alert.alert('Success', 'Member added');
    } catch (error) {
      console.error('Error adding member:', error);
      Alert.alert('Error', 'Failed to add member');
    }
  };

  if (!currentChat) return null;

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}>
          <Ionicons name="arrow-back" size={24} color={colors.text} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Chat Info</Text>
        {isAdmin && !isEditing && (
          <TouchableOpacity onPress={() => setIsEditing(true)}>
            <Text style={styles.editButton}>Edit</Text>
          </TouchableOpacity>
        )}
        {isEditing && (
          <TouchableOpacity onPress={handleSaveInfo} disabled={loading}>
            {loading ? (
              <ActivityIndicator size="small" color={colors.primary} />
            ) : (
              <Text style={styles.saveButton}>Save</Text>
            )}
          </TouchableOpacity>
        )}
      </View>

      <ScrollView style={styles.content}>
        <View style={styles.infoSection}>
          <View style={styles.avatarContainer}>
            <Avatar 
              uri={currentChat.avatar} 
              name={currentChat.name || 'Chat'} 
              size={80} 
            />
            {isEditing && (
              <TouchableOpacity style={styles.changeAvatarButton}>
                <Ionicons name="camera" size={20} color={colors.textLight} />
              </TouchableOpacity>
            )}
          </View>

          {isEditing ? (
            <View style={styles.editForm}>
              <Text style={styles.label}>Name</Text>
              <TextInput
                style={styles.input}
                value={name}
                onChangeText={setName}
                placeholder="Chat Name"
              />
              
              <Text style={styles.label}>Description</Text>
              <TextInput
                style={[styles.input, styles.textArea]}
                value={description}
                onChangeText={setDescription}
                placeholder="Description"
                multiline
              />

              {currentChat.chat_type === 'channel' && (
                <View style={styles.switchContainer}>
                  <Text style={styles.label}>Only Admins Can Post</Text>
                  <Switch
                    value={onlyAdminsPost}
                    onValueChange={setOnlyAdminsPost}
                    trackColor={{ false: colors.border, true: colors.primary }}
                  />
                </View>
              )}
            </View>
          ) : (
            <View style={styles.displayInfo}>
              <Text style={styles.chatName}>{currentChat.name}</Text>
              {currentChat.description && (
                <Text style={styles.chatDescription}>{currentChat.description}</Text>
              )}
              <Text style={styles.chatType}>
                {currentChat.chat_type === 'channel' ? 'Channel' : 'Group'} • {currentChat.participants.length} members
              </Text>
            </View>
          )}
        </View>

        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Participants</Text>
            {isAdmin && (
              <TouchableOpacity onPress={loadFriends}>
                <Ionicons name="person-add" size={24} color={colors.primary} />
              </TouchableOpacity>
            )}
          </View>

          {currentChat.participant_details?.map((participant) => {
            const isParticipantAdmin = currentChat.admins?.includes(participant.id);
            const isMe = participant.id === user?.id;

            return (
              <View key={participant.id} style={styles.participantItem}>
                <Avatar uri={participant.avatar} name={participant.display_name} size={40} />
                <View style={styles.participantInfo}>
                  <Text style={styles.participantName}>
                    {participant.display_name} {isMe && '(You)'}
                  </Text>
                  <Text style={styles.participantRole}>
                    {isParticipantAdmin ? 'Admin' : 'Member'}
                  </Text>
                </View>
                
                {isAdmin && !isMe && (
                  <View style={styles.adminActions}>
                    <TouchableOpacity 
                      onPress={() => isParticipantAdmin 
                        ? handleDemoteAdmin(participant.id) 
                        : handlePromoteAdmin(participant.id)
                      }
                      style={styles.actionIcon}
                    >
                      <Ionicons 
                        name={isParticipantAdmin ? "shield-outline" : "shield"} 
                        size={20} 
                        color={colors.primary} 
                      />
                    </TouchableOpacity>
                    <TouchableOpacity 
                      onPress={() => handleRemoveParticipant(participant.id)}
                      style={styles.actionIcon}
                    >
                      <Ionicons name="trash-outline" size={20} color={colors.error} />
                    </TouchableOpacity>
                  </View>
                )}
              </View>
            );
          })}
        </View>

        <TouchableOpacity style={styles.leaveButton} onPress={handleLeaveChat}>
          <Ionicons name="log-out-outline" size={24} color={colors.error} />
          <Text style={styles.leaveButtonText}>Leave Chat</Text>
        </TouchableOpacity>
      </ScrollView>

      {/* Add Members Modal/Overlay */}
      {showAddMembers && (
        <View style={styles.addMembersOverlay}>
          <View style={styles.addMembersContainer}>
            <View style={styles.addMembersHeader}>
              <Text style={styles.addMembersTitle}>Add Members</Text>
              <TouchableOpacity onPress={() => setShowAddMembers(false)}>
                <Ionicons name="close" size={24} color={colors.text} />
              </TouchableOpacity>
            </View>
            <ScrollView>
              {friends.length === 0 ? (
                <Text style={styles.emptyText}>No friends available to add</Text>
              ) : (
                friends.map(friend => (
                  <TouchableOpacity 
                    key={friend.id} 
                    style={styles.friendItem}
                    onPress={() => handleAddMember(friend.id)}
                  >
                    <Avatar uri={friend.avatar} name={friend.display_name} size={40} />
                    <Text style={styles.friendName}>{friend.display_name}</Text>
                    <Ionicons name="add-circle-outline" size={24} color={colors.primary} />
                  </TouchableOpacity>
                ))
              )}
            </ScrollView>
          </View>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    paddingTop: 60,
    backgroundColor: colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: colors.text,
  },
  editButton: {
    color: colors.primary,
    fontSize: 16,
    fontWeight: '600',
  },
  saveButton: {
    color: colors.success,
    fontSize: 16,
    fontWeight: '600',
  },
  content: {
    flex: 1,
  },
  infoSection: {
    alignItems: 'center',
    padding: 24,
    backgroundColor: colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  avatarContainer: {
    position: 'relative',
    marginBottom: 16,
  },
  changeAvatarButton: {
    position: 'absolute',
    bottom: 0,
    right: 0,
    backgroundColor: colors.primary,
    padding: 8,
    borderRadius: 20,
    borderWidth: 2,
    borderColor: colors.surface,
  },
  displayInfo: {
    alignItems: 'center',
  },
  chatName: {
    fontSize: 24,
    fontWeight: 'bold',
    color: colors.text,
    marginBottom: 8,
  },
  chatDescription: {
    fontSize: 16,
    color: colors.textSecondary,
    textAlign: 'center',
    marginBottom: 8,
  },
  chatType: {
    fontSize: 14,
    color: colors.textMuted,
  },
  editForm: {
    width: '100%',
  },
  label: {
    fontSize: 14,
    fontWeight: '500',
    color: colors.textSecondary,
    marginBottom: 8,
    marginTop: 16,
  },
  input: {
    backgroundColor: colors.background,
    padding: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.border,
    fontSize: 16,
    color: colors.text,
  },
  textArea: {
    height: 80,
    textAlignVertical: 'top',
  },
  switchContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 16,
  },
  section: {
    marginTop: 24,
    backgroundColor: colors.surface,
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderColor: colors.border,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.textSecondary,
  },
  participantItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  participantInfo: {
    flex: 1,
    marginLeft: 12,
  },
  participantName: {
    fontSize: 16,
    fontWeight: '500',
    color: colors.text,
  },
  participantRole: {
    fontSize: 12,
    color: colors.textMuted,
  },
  adminActions: {
    flexDirection: 'row',
    gap: 16,
  },
  actionIcon: {
    padding: 4,
  },
  leaveButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 32,
    marginBottom: 48,
    padding: 16,
    backgroundColor: colors.surface,
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderColor: colors.border,
  },
  leaveButtonText: {
    marginLeft: 8,
    fontSize: 16,
    fontWeight: '600',
    color: colors.error,
  },
  addMembersOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  addMembersContainer: {
    backgroundColor: colors.surface,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    height: '70%',
    padding: 20,
  },
  addMembersHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  addMembersTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: colors.text,
  },
  friendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  friendName: {
    flex: 1,
    marginLeft: 12,
    fontSize: 16,
    color: colors.text,
  },
  emptyText: {
    textAlign: 'center',
    color: colors.textSecondary,
    marginTop: 20,
  },
});
