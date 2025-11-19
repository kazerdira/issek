import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  StyleSheet,
  ActivityIndicator,
  Alert,
  Switch,
  SafeAreaView,
} from 'react-native';
import { useRouter } from 'expo-router';
import { usersAPI, chatsAPI, friendsAPI } from '../../src/services/api';
import { Avatar } from '../../src/components/Avatar';
import { colors } from '../../src/theme/colors';
import { Ionicons } from '@expo/vector-icons';
import { useAuthStore } from '../../src/store/authStore';

interface User {
  id: string;
  username: string;
  display_name: string;
  avatar?: string;
}

export default function CreateChatScreen() {
  const router = useRouter();
  const { user } = useAuthStore();
  const [step, setStep] = useState<1 | 2>(1); // 1: Select Type & Info, 2: Select Participants
  const [chatType, setChatType] = useState<'group' | 'channel'>('group');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isPublic, setIsPublic] = useState(false);
  const [onlyAdminsPost, setOnlyAdminsPost] = useState(false);
  
  const [friends, setFriends] = useState<User[]>([]);
  const [selectedUsers, setSelectedUsers] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    loadFriends();
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
    }
  };

  const toggleUserSelection = (userId: string) => {
    if (selectedUsers.includes(userId)) {
      setSelectedUsers(selectedUsers.filter(id => id !== userId));
    } else {
      setSelectedUsers([...selectedUsers, userId]);
    }
  };

  const handleCreate = async () => {
    if (!name.trim()) {
      Alert.alert('Error', 'Please enter a name');
      return;
    }
    if (selectedUsers.length === 0) {
      Alert.alert('Error', 'Please select at least one participant');
      return;
    }

    setCreating(true);
    try {
      const response = await chatsAPI.createChat({
        chat_type: chatType,
        name,
        description,
        participants: selectedUsers, // Backend adds creator automatically
        is_public: isPublic,
        only_admins_can_post: chatType === 'channel' ? true : onlyAdminsPost, // Channels usually restricted
      });
      router.replace(`/chat/${response.data.id}`);
    } catch (error: any) {
      Alert.alert('Error', 'Failed to create chat');
      console.error(error);
    } finally {
      setCreating(false);
    }
  };

  const renderFriendItem = ({ item }: { item: User }) => (
    <TouchableOpacity
      style={styles.userItem}
      onPress={() => toggleUserSelection(item.id)}
    >
      <Avatar uri={item.avatar} name={item.display_name} size={40} />
      <View style={styles.userInfo}>
        <Text style={styles.userName}>{item.display_name}</Text>
        <Text style={styles.userHandle}>@{item.username}</Text>
      </View>
      <View style={[
        styles.checkbox,
        selectedUsers.includes(item.id) && styles.checkboxSelected
      ]}>
        {selectedUsers.includes(item.id) && (
          <Ionicons name="checkmark" size={16} color={colors.textLight} />
        )}
      </View>
    </TouchableOpacity>
  );

  return (
    <View style={styles.container}>
      <SafeAreaView style={styles.safeAreaTop}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => step === 1 ? router.back() : setStep(1)}>
            <Ionicons name="arrow-back" size={24} color={colors.text} />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>
            {step === 1 ? 'New Group / Channel' : 'Add Participants'}
          </Text>
          {step === 2 && (
            <TouchableOpacity onPress={handleCreate} disabled={creating}>
              {creating ? (
                <ActivityIndicator size="small" color={colors.primary} />
              ) : (
                <Text style={styles.createButton}>Create</Text>
              )}
            </TouchableOpacity>
          )}
          {step === 1 && (
            <TouchableOpacity onPress={() => setStep(2)}>
              <Text style={styles.createButton}>Next</Text>
            </TouchableOpacity>
          )}
        </View>
      </SafeAreaView>

      {step === 1 ? (
        <View style={styles.form}>
          <View style={styles.typeSelector}>
            <TouchableOpacity 
              style={[styles.typeOption, chatType === 'group' && styles.typeOptionActive]}
              onPress={() => setChatType('group')}
            >
              <Ionicons name="people" size={24} color={chatType === 'group' ? colors.primary : colors.textSecondary} />
              <Text style={[styles.typeText, chatType === 'group' && styles.typeTextActive]}>Group</Text>
            </TouchableOpacity>
            <TouchableOpacity 
              style={[styles.typeOption, chatType === 'channel' && styles.typeOptionActive]}
              onPress={() => setChatType('channel')}
            >
              <Ionicons name="megaphone" size={24} color={chatType === 'channel' ? colors.primary : colors.textSecondary} />
              <Text style={[styles.typeText, chatType === 'channel' && styles.typeTextActive]}>Channel</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Name</Text>
            <TextInput
              style={styles.input}
              placeholder="Enter name..."
              value={name}
              onChangeText={setName}
            />
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Description (Optional)</Text>
            <TextInput
              style={[styles.input, styles.textArea]}
              placeholder="Enter description..."
              value={description}
              onChangeText={setDescription}
              multiline
            />
          </View>

          <View style={styles.switchGroup}>
            <Text style={styles.label}>Public</Text>
            <Switch
              value={isPublic}
              onValueChange={setIsPublic}
              trackColor={{ false: colors.border, true: colors.primary }}
            />
          </View>
          
          {chatType === 'group' && (
             <View style={styles.switchGroup}>
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
        <View style={styles.participantsContainer}>
          <Text style={styles.subtitle}>Select Friends</Text>
          {loading ? (
            <ActivityIndicator size="large" color={colors.primary} style={{ marginTop: 20 }} />
          ) : (
            <FlatList
              data={friends}
              renderItem={renderFriendItem}
              keyExtractor={(item) => item.id}
              ListEmptyComponent={
                <Text style={styles.emptyText}>No friends found. Add friends first!</Text>
              }
            />
          )}
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
  safeAreaTop: {
    backgroundColor: colors.surface,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    backgroundColor: colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: colors.text,
  },
  createButton: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.primary,
  },
  form: {
    padding: 20,
  },
  typeSelector: {
    flexDirection: 'row',
    marginBottom: 24,
    gap: 16,
  },
  typeOption: {
    flex: 1,
    alignItems: 'center',
    padding: 16,
    backgroundColor: colors.surface,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
  },
  typeOptionActive: {
    borderColor: colors.primary,
    backgroundColor: colors.primary + '10',
  },
  typeText: {
    marginTop: 8,
    fontSize: 16,
    fontWeight: '500',
    color: colors.textSecondary,
  },
  typeTextActive: {
    color: colors.primary,
  },
  inputGroup: {
    marginBottom: 20,
  },
  label: {
    fontSize: 14,
    fontWeight: '500',
    color: colors.textSecondary,
    marginBottom: 8,
  },
  input: {
    backgroundColor: colors.surface,
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
  switchGroup: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
    backgroundColor: colors.surface,
    padding: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.border,
  },
  participantsContainer: {
    flex: 1,
    padding: 16,
  },
  subtitle: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.textSecondary,
    marginBottom: 12,
  },
  userItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    backgroundColor: colors.surface,
    marginBottom: 8,
    borderRadius: 8,
  },
  userInfo: {
    flex: 1,
    marginLeft: 12,
  },
  userName: {
    fontSize: 16,
    fontWeight: '500',
    color: colors.text,
  },
  userHandle: {
    fontSize: 14,
    color: colors.textSecondary,
  },
  checkbox: {
    width: 24,
    height: 24,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: colors.border,
    justifyContent: 'center',
    alignItems: 'center',
  },
  checkboxSelected: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  emptyText: {
    textAlign: 'center',
    color: colors.textSecondary,
    marginTop: 20,
  },
});
