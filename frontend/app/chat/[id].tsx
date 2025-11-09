import React, { useEffect, useState, useRef } from 'react';
import {
  View,
  Text,
  FlatList,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  Alert,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { useChatStore, Message } from '../../src/store/chatStore';
import { useAuthStore } from '../../src/store/authStore';
import { chatsAPI } from '../../src/services/api';
import { socketService } from '../../src/services/socket';
import { MessageBubble, TypingIndicator, ChatHeader, LoadingSpinner } from '../../src/components';
import { colors } from '../../src/theme/colors';
import { Ionicons } from '@expo/vector-icons';
import { formatDistanceToNow } from 'date-fns';

export default function ChatScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams();
  const chatId = typeof id === 'string' ? id : id[0];
  
  const { currentChat, setCurrentChat, messages, setMessages, addMessage, updateMessage, removeMessage } = useChatStore();
  const { user } = useAuthStore();
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [typingUsers, setTypingUsers] = useState<string[]>([]);
  const [replyTo, setReplyTo] = useState<{ id: string; content: string; sender_name: string } | null>(null);
  const [editingMessage, setEditingMessage] = useState<{ id: string; content: string } | null>(null);
  const flatListRef = useRef<FlatList>(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    loadChat();
    loadMessages();

    if (user) {
      socketService.joinChat(chatId, user.id);
    }

    return () => {
      if (user) {
        socketService.leaveChat(chatId, user.id);
      }
    };
  }, [chatId]);

  const loadChat = async () => {
    try {
      const response = await chatsAPI.getChat(chatId);
      setCurrentChat(response.data);
    } catch (error) {
      console.error('Error loading chat:', error);
    }
  };

  const loadMessages = async () => {
    try {
      const response = await chatsAPI.getMessages(chatId);
      setMessages(chatId, response.data);
    } catch (error) {
      console.error('Error loading messages:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSend = async () => {
    if (!inputText.trim() || !user) return;

    const messageText = inputText.trim();

    // Handle editing
    if (editingMessage) {
      await handleEditMessage(editingMessage.id, messageText);
      return;
    }

    setInputText('');
    setSending(true);

    try {
      const messageData: any = {
        chat_id: chatId,
        sender_id: user.id,
        content: messageText,
        message_type: 'text',
      };

      // Add reply_to if replying
      if (replyTo) {
        messageData.reply_to = replyTo.id;
      }

      const response = await chatsAPI.sendMessage(chatId, messageData);

      addMessage(chatId, response.data);
      setReplyTo(null); // Clear reply
      flatListRef.current?.scrollToEnd({ animated: true });
    } catch (error) {
      console.error('Error sending message:', error);
      setInputText(messageText);
    } finally {
      setSending(false);
    }
  };

  const handleReply = (messageId: string, content: string) => {
    const message = messages[chatId]?.find(m => m.id === messageId);
    if (message) {
      setReplyTo({
        id: messageId,
        content,
        sender_name: message.sender?.display_name || 'User',
      });
    }
  };

  const handleEdit = (messageId: string, content: string) => {
    setEditingMessage({ id: messageId, content });
    setInputText(content);
  };

  const handleEditMessage = async (messageId: string, newContent: string) => {
    try {
      await chatsAPI.editMessage(messageId, newContent);
      setEditingMessage(null);
      setInputText('');
      // Update will come through socket
    } catch (error) {
      console.error('Error editing message:', error);
      Alert.alert('Error', 'Failed to edit message');
    }
  };

  const handleDelete = async (messageId: string) => {
    Alert.alert(
      'Delete Message',
      'Are you sure you want to delete this message?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await chatsAPI.deleteMessage(messageId);
              // Removal will come through socket
            } catch (error) {
              console.error('Error deleting message:', error);
              Alert.alert('Error', 'Failed to delete message');
            }
          },
        },
      ]
    );
  };

  const handleForward = (messageId: string) => {
    // TODO: Implement forward flow - show chat selector
    Alert.alert('Forward', 'Forward feature coming soon!');
  };

  const handleReact = async (messageId: string, emoji: string) => {
    try {
      await chatsAPI.addReaction(messageId, emoji);
      // Update will come through socket
    } catch (error) {
      console.error('Error adding reaction:', error);
    }
  };

  const handleRemoveReaction = async (messageId: string, emoji: string) => {
    try {
      await chatsAPI.removeReaction(messageId, emoji);
      // Update will come through socket
    } catch (error) {
      console.error('Error removing reaction:', error);
    }
  };

  const cancelReply = () => {
    setReplyTo(null);
  };

  const cancelEdit = () => {
    setEditingMessage(null);
    setInputText('');
  };

  const getChatName = () => {
    if (!currentChat) return 'Chat';
    if (currentChat.chat_type === 'group') {
      return currentChat.name || 'Group Chat';
    }
    const otherUser = currentChat.participant_details?.find((p) => p.id !== user?.id);
    return otherUser?.display_name || 'Unknown';
  };

  const getChatAvatar = () => {
    if (!currentChat) return undefined;
    if (currentChat.chat_type === 'group') {
      return currentChat.avatar;
    }
    const otherUser = currentChat.participant_details?.find((p) => p.id !== user?.id);
    return otherUser?.avatar;
  };

  const getChatOnlineStatus = () => {
    if (!currentChat || currentChat.chat_type === 'group') return false;
    const otherUser = currentChat.participant_details?.find((p) => p.id !== user?.id);
    return otherUser?.is_online || false;
  };

  const renderMessage = ({ item }: { item: Message }) => {
    const isOwn = item.sender_id === user?.id;
    
    return (
      <MessageBubble
        id={item.id}
        content={item.content}
        sender_id={item.sender_id}
        sender_name={item.sender?.display_name || 'User'}
        created_at={item.created_at}
        edited={item.edited}
        isOwn={isOwn}
        reactions={item.reactions}
        reply_to_message={item.reply_to_message}
        onReply={handleReply}
        onEdit={handleEdit}
        onDelete={handleDelete}
        onForward={handleForward}
        onReact={handleReact}
        onRemoveReaction={handleRemoveReaction}
        currentUserId={user?.id}
      />
    );
  };

  const getLastSeen = () => {
    if (!currentChat || currentChat.chat_type === 'group') return undefined;
    const otherUser = currentChat.participant_details?.find((p) => p.id !== user?.id);
    if (!otherUser?.last_seen) return undefined;
    return formatDistanceToNow(new Date(otherUser.last_seen), { addSuffix: true });
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <LoadingSpinner size={50} />
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={90}
    >
      {/* Header */}
      <ChatHeader
        name={getChatName()}
        avatar={getChatAvatar()}
        isOnline={getChatOnlineStatus()}
        lastSeen={getLastSeen()}
        isGroup={currentChat?.chat_type === 'group'}
        participantCount={currentChat?.participants?.length}
        onBack={() => router.back()}
        onInfo={() => {/* TODO: Navigate to chat info */}}
      />

      {/* Messages */}
      <FlatList
        ref={flatListRef}
        data={messages[chatId] || []}
        renderItem={renderMessage}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.messagesList}
        inverted={false}
        onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: false })}
        ListEmptyComponent={
          <View style={styles.emptyState}>
            <Ionicons name="chatbubbles-outline" size={64} color={colors.textMuted} />
            <Text style={styles.emptyText}>No messages yet</Text>
            <Text style={styles.emptySubtext}>Start the conversation</Text>
          </View>
        }
        ListFooterComponent={
          typingUsers.length > 0 ? (
            <TypingIndicator users={typingUsers} />
          ) : null
        }
      />

      {/* Reply/Edit Bar */}
      {(replyTo || editingMessage) && (
        <View style={styles.actionBar}>
          <View style={styles.actionBarContent}>
            <Ionicons
              name={editingMessage ? 'create-outline' : 'arrow-undo'}
              size={20}
              color={colors.primary}
            />
            <View style={styles.actionBarText}>
              <Text style={styles.actionBarTitle}>
                {editingMessage ? 'Edit Message' : `Reply to ${replyTo?.sender_name}`}
              </Text>
              <Text style={styles.actionBarSubtitle} numberOfLines={1}>
                {editingMessage ? editingMessage.content : replyTo?.content}
              </Text>
            </View>
          </View>
          <TouchableOpacity
            onPress={editingMessage ? cancelEdit : cancelReply}
            hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
          >
            <Ionicons name="close" size={24} color={colors.textSecondary} />
          </TouchableOpacity>
        </View>
      )}

      {/* Input */}
      <View style={styles.inputContainer}>
        <TouchableOpacity style={styles.inputAction}>
          <Ionicons name="add-circle" size={28} color={colors.primary} />
        </TouchableOpacity>
        
        <TextInput
          style={styles.input}
          placeholder={editingMessage ? 'Edit message...' : 'Type a message...'}
          value={inputText}
          onChangeText={setInputText}
          multiline
          maxLength={1000}
        />

        {inputText.trim() ? (
          <TouchableOpacity 
            style={styles.sendButton} 
            onPress={handleSend}
            disabled={sending}
          >
            {sending ? (
              <LoadingSpinner size={20} color={colors.textLight} />
            ) : (
              <Ionicons 
                name={editingMessage ? 'checkmark' : 'send'} 
                size={20} 
                color={colors.textLight} 
              />
            )}
          </TouchableOpacity>
        ) : (
          <TouchableOpacity style={styles.inputAction}>
            <Ionicons name="mic" size={24} color={colors.primary} />
          </TouchableOpacity>
        )}
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.background,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 8,
    paddingTop: 48,
    backgroundColor: colors.primary,
  },
  backButton: {
    padding: 8,
  },
  headerCenter: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    marginLeft: 8,
  },
  headerText: {
    marginLeft: 12,
  },
  headerTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.textLight,
  },
  headerSubtitle: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.8)',
  },
  headerButton: {
    padding: 8,
    marginLeft: 4,
  },
  messagesList: {
    padding: 16,
    flexGrow: 1,
  },
  messageContainer: {
    flexDirection: 'row',
    marginBottom: 12,
    alignItems: 'flex-end',
  },
  messageContainerMe: {
    justifyContent: 'flex-end',
  },
  messageContainerOther: {
    justifyContent: 'flex-start',
  },
  messageBubble: {
    maxWidth: '70%',
    padding: 12,
    borderRadius: 16,
    marginLeft: 8,
  },
  messageBubbleMe: {
    backgroundColor: colors.messageSent,
    borderBottomRightRadius: 4,
  },
  messageBubbleOther: {
    backgroundColor: colors.messageReceived,
    borderBottomLeftRadius: 4,
  },
  senderName: {
    fontSize: 12,
    fontWeight: '600',
    color: colors.primary,
    marginBottom: 4,
  },
  messageText: {
    fontSize: 16,
    lineHeight: 22,
  },
  messageTextMe: {
    color: colors.textLight,
  },
  messageTextOther: {
    color: colors.text,
  },
  messageFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 4,
    justifyContent: 'flex-end',
  },
  messageTime: {
    fontSize: 11,
  },
  messageTimeMe: {
    color: 'rgba(255, 255, 255, 0.7)',
  },
  messageTimeOther: {
    color: colors.textMuted,
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
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 8,
    backgroundColor: colors.surface,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  inputAction: {
    padding: 8,
  },
  input: {
    flex: 1,
    backgroundColor: colors.background,
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 8,
    fontSize: 16,
    maxHeight: 100,
    color: colors.text,
  },
  sendButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.primary,
    justifyContent: 'center',
    alignItems: 'center',
    marginLeft: 8,
  },
  actionBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: colors.surface,
    padding: 12,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  actionBarContent: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
  },
  actionBarText: {
    flex: 1,
    marginLeft: 12,
  },
  actionBarTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 2,
  },
  actionBarSubtitle: {
    fontSize: 13,
    color: colors.textSecondary,
  },
});
