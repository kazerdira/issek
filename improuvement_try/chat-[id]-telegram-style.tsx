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
  ActivityIndicator,
  Image,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { useChatStore, Message } from '../../src/store/chatStore';
import { useAuthStore } from '../../src/store/authStore';
import { chatsAPI } from '../../src/services/api';
import { socketService } from '../../src/services/socket';
import { Avatar } from '../../src/components/Avatar';
import { colors } from '../../src/theme/colors';
import { Ionicons } from '@expo/vector-icons';
import { format } from 'date-fns';

export default function ChatScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams();
  const chatId = typeof id === 'string' ? id : id[0];
  
  const { currentChat, setCurrentChat, messages, setMessages, addMessage } = useChatStore();
  const { user } = useAuthStore();
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const flatListRef = useRef<FlatList>(null);

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
    setInputText('');
    setSending(true);

    try {
      const response = await chatsAPI.sendMessage(chatId, {
        chat_id: chatId,
        sender_id: user.id,
        content: messageText,
        message_type: 'text',
      });

      addMessage(chatId, response.data);
      flatListRef.current?.scrollToEnd({ animated: true });
    } catch (error) {
      console.error('Error sending message:', error);
      setInputText(messageText);
    } finally {
      setSending(false);
    }
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

  const getReactionUsers = (userIds: string[]) => {
    if (!currentChat?.participant_details) return [];
    return userIds
      .map(id => currentChat.participant_details?.find(p => p.id === id))
      .filter(Boolean);
  };

  const renderMessage = ({ item, index }: { item: Message; index: number }) => {
    const isMe = item.sender_id === user?.id;
    const prevMessage = index > 0 ? messages[chatId]?.[index - 1] : null;
    const nextMessage = index < (messages[chatId]?.length || 0) - 1 ? messages[chatId]?.[index + 1] : null;
    
    const showAvatar = !isMe && (!nextMessage || nextMessage.sender_id !== item.sender_id);
    const showName = !isMe && currentChat?.chat_type === 'group' && (!prevMessage || prevMessage.sender_id !== item.sender_id);
    const isFirstInGroup = !prevMessage || prevMessage.sender_id !== item.sender_id;
    const isLastInGroup = !nextMessage || nextMessage.sender_id !== item.sender_id;
    
    const messageTime = format(new Date(item.created_at), 'HH:mm');
    const hasReactions = item.reactions && Object.keys(item.reactions).length > 0;

    return (
      <View style={[
        styles.messageWrapper,
        isMe ? styles.messageWrapperMe : styles.messageWrapperOther,
        isFirstInGroup && styles.messageWrapperFirst,
        isLastInGroup && styles.messageWrapperLast,
      ]}>
        <View style={[styles.messageContainer, isMe ? styles.messageContainerMe : styles.messageContainerOther]}>
          {/* Avatar for group chats */}
          {!isMe && currentChat?.chat_type === 'group' && (
            <View style={styles.avatarContainer}>
              {showAvatar ? (
                <Avatar
                  uri={item.sender?.avatar}
                  name={item.sender?.display_name || 'User'}
                  size={32}
                />
              ) : (
                <View style={{ width: 32 }} />
              )}
            </View>
          )}
          
          <View style={[
            styles.messageBubble,
            isMe ? styles.messageBubbleMe : styles.messageBubbleOther,
            isFirstInGroup && (isMe ? styles.bubbleFirstMe : styles.bubbleFirstOther),
            isLastInGroup && (isMe ? styles.bubbleLastMe : styles.bubbleLastOther),
            !isFirstInGroup && !isLastInGroup && styles.bubbleMiddle,
          ]}>
            {/* Sender name for group chats */}
            {showName && (
              <Text style={styles.senderName}>{item.sender?.display_name}</Text>
            )}

            {/* Reply preview */}
            {item.reply_to && (
              <View style={styles.replyContainer}>
                <View style={[styles.replyBar, isMe ? styles.replyBarMe : styles.replyBarOther]} />
                <View style={styles.replyContent}>
                  <Text style={[styles.replyName, isMe ? styles.replyNameMe : styles.replyNameOther]}>
                    {item.reply_to === user?.id ? 'You' : 'Someone'}
                  </Text>
                  <Text style={[styles.replyText, isMe ? styles.replyTextMe : styles.replyTextOther]} numberOfLines={1}>
                    Reply message preview...
                  </Text>
                </View>
              </View>
            )}

            {/* Message content */}
            <Text style={[styles.messageText, isMe ? styles.messageTextMe : styles.messageTextOther]}>
              {item.content}
            </Text>

            {/* Reactions - INSIDE the bubble like Telegram */}
            {hasReactions && (
              <View style={styles.reactionsContainer}>
                {Object.entries(item.reactions).map(([emoji, userIds]) => {
                  const reactionUsers = getReactionUsers(userIds as string[]);
                  return (
                    <View key={emoji} style={[
                      styles.reactionBubble,
                      isMe ? styles.reactionBubbleMe : styles.reactionBubbleOther
                    ]}>
                      <Text style={styles.reactionEmoji}>{emoji}</Text>
                      <View style={styles.reactionAvatars}>
                        {reactionUsers.slice(0, 3).map((reactUser: any, idx) => (
                          <View
                            key={reactUser?.id || idx}
                            style={[
                              styles.reactionAvatar,
                              idx > 0 && styles.reactionAvatarOverlap
                            ]}
                          >
                            {reactUser?.avatar ? (
                              <Image 
                                source={{ uri: reactUser.avatar }} 
                                style={styles.reactionAvatarImage}
                              />
                            ) : (
                              <View style={[styles.reactionAvatarPlaceholder, { backgroundColor: getColorFromName(reactUser?.display_name || 'U') }]}>
                                <Text style={styles.reactionAvatarText}>
                                  {(reactUser?.display_name || 'U')[0].toUpperCase()}
                                </Text>
                              </View>
                            )}
                          </View>
                        ))}
                        {(userIds as string[]).length > 3 && (
                          <View style={[styles.reactionAvatar, styles.reactionAvatarOverlap, styles.reactionAvatarMore]}>
                            <Text style={styles.reactionAvatarMoreText}>
                              +{(userIds as string[]).length - 3}
                            </Text>
                          </View>
                        )}
                      </View>
                    </View>
                  );
                })}
              </View>
            )}

            {/* Message footer with time and status */}
            <View style={styles.messageFooter}>
              {item.edited && (
                <Text style={[styles.editedLabel, isMe ? styles.editedLabelMe : styles.editedLabelOther]}>
                  edited
                </Text>
              )}
              <Text style={[styles.messageTime, isMe ? styles.messageTimeMe : styles.messageTimeOther]}>
                {messageTime}
              </Text>
              {isMe && (
                <Ionicons
                  name={item.status === 'read' ? 'checkmark-done' : item.status === 'delivered' ? 'checkmark-done' : 'checkmark'}
                  size={16}
                  color={item.status === 'read' ? '#4FC3F7' : 'rgba(255, 255, 255, 0.7)'}
                  style={{ marginLeft: 4 }}
                />
              )}
            </View>
          </View>
        </View>
      </View>
    );
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={colors.primary} />
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
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color={colors.textLight} />
        </TouchableOpacity>
        
        <TouchableOpacity style={styles.headerCenter}>
          <Avatar
            uri={getChatAvatar()}
            name={getChatName()}
            size={40}
            online={getChatOnlineStatus()}
          />
          <View style={styles.headerText}>
            <Text style={styles.headerTitle}>{getChatName()}</Text>
            <Text style={styles.headerSubtitle}>
              {getChatOnlineStatus() ? 'Online' : 'Offline'}
            </Text>
          </View>
        </TouchableOpacity>

        <TouchableOpacity style={styles.headerButton}>
          <Ionicons name="call" size={20} color={colors.textLight} />
        </TouchableOpacity>
        <TouchableOpacity style={styles.headerButton}>
          <Ionicons name="ellipsis-vertical" size={20} color={colors.textLight} />
        </TouchableOpacity>
      </View>

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
      />

      {/* Input */}
      <View style={styles.inputContainer}>
        <TouchableOpacity style={styles.inputAction}>
          <Ionicons name="add-circle" size={28} color={colors.primary} />
        </TouchableOpacity>
        
        <TextInput
          style={styles.input}
          placeholder="Type a message..."
          placeholderTextColor={colors.textSecondary}
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
              <ActivityIndicator size="small" color={colors.textLight} />
            ) : (
              <Ionicons name="send" size={20} color={colors.textLight} />
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

// Helper function for avatar colors
const getColorFromName = (name: string): string => {
  const avatarColors = [
    '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
    '#DFE6E9', '#6C5CE7', '#A29BFE', '#FD79A8', '#FDCB6E',
  ];
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return avatarColors[Math.abs(hash) % avatarColors.length];
};

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
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
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
    marginTop: 2,
  },
  headerButton: {
    padding: 8,
    marginLeft: 4,
  },
  messagesList: {
    padding: 8,
    flexGrow: 1,
  },
  messageWrapper: {
    marginVertical: 1,
  },
  messageWrapperMe: {
    alignItems: 'flex-end',
  },
  messageWrapperOther: {
    alignItems: 'flex-start',
  },
  messageWrapperFirst: {
    marginTop: 8,
  },
  messageWrapperLast: {
    marginBottom: 8,
  },
  messageContainer: {
    flexDirection: 'row',
    maxWidth: '85%',
    alignItems: 'flex-end',
  },
  messageContainerMe: {
    justifyContent: 'flex-end',
  },
  messageContainerOther: {
    justifyContent: 'flex-start',
  },
  avatarContainer: {
    marginRight: 8,
    marginBottom: 2,
  },
  messageBubble: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    position: 'relative',
  },
  messageBubbleMe: {
    backgroundColor: colors.messageSent,
    borderRadius: 12,
  },
  messageBubbleOther: {
    backgroundColor: colors.messageReceived,
    borderRadius: 12,
  },
  // Message grouping styles - like Telegram
  bubbleFirstMe: {
    borderTopRightRadius: 18,
    borderBottomRightRadius: 4,
  },
  bubbleFirstOther: {
    borderTopLeftRadius: 18,
    borderBottomLeftRadius: 4,
  },
  bubbleLastMe: {
    borderTopRightRadius: 4,
    borderBottomRightRadius: 18,
  },
  bubbleLastOther: {
    borderTopLeftRadius: 4,
    borderBottomLeftRadius: 18,
  },
  bubbleMiddle: {
    borderRadius: 4,
  },
  senderName: {
    fontSize: 13,
    fontWeight: '600',
    color: colors.primary,
    marginBottom: 4,
  },
  // Reply preview styles - like Telegram
  replyContainer: {
    flexDirection: 'row',
    backgroundColor: 'rgba(0, 0, 0, 0.05)',
    borderRadius: 6,
    padding: 8,
    marginBottom: 6,
  },
  replyBar: {
    width: 3,
    borderRadius: 1.5,
    marginRight: 8,
  },
  replyBarMe: {
    backgroundColor: 'rgba(255, 255, 255, 0.5)',
  },
  replyBarOther: {
    backgroundColor: colors.primary,
  },
  replyContent: {
    flex: 1,
  },
  replyName: {
    fontSize: 13,
    fontWeight: '600',
    marginBottom: 2,
  },
  replyNameMe: {
    color: 'rgba(255, 255, 255, 0.9)',
  },
  replyNameOther: {
    color: colors.primary,
  },
  replyText: {
    fontSize: 13,
    opacity: 0.7,
  },
  replyTextMe: {
    color: 'rgba(255, 255, 255, 0.7)',
  },
  replyTextOther: {
    color: colors.textSecondary,
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
  // Reactions INSIDE bubble - Telegram style
  reactionsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    marginTop: 8,
  },
  reactionBubble: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 4,
    paddingLeft: 6,
    paddingRight: 8,
    borderRadius: 12,
    gap: 6,
  },
  reactionBubbleMe: {
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
  },
  reactionBubbleOther: {
    backgroundColor: 'rgba(108, 92, 231, 0.1)',
  },
  reactionEmoji: {
    fontSize: 16,
  },
  reactionAvatars: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  reactionAvatar: {
    width: 20,
    height: 20,
    borderRadius: 10,
    overflow: 'hidden',
    borderWidth: 1.5,
    borderColor: colors.background,
  },
  reactionAvatarOverlap: {
    marginLeft: -8,
  },
  reactionAvatarImage: {
    width: '100%',
    height: '100%',
  },
  reactionAvatarPlaceholder: {
    width: '100%',
    height: '100%',
    justifyContent: 'center',
    alignItems: 'center',
  },
  reactionAvatarText: {
    fontSize: 10,
    fontWeight: '600',
    color: colors.textLight,
  },
  reactionAvatarMore: {
    backgroundColor: colors.textSecondary,
    justifyContent: 'center',
    alignItems: 'center',
  },
  reactionAvatarMoreText: {
    fontSize: 8,
    fontWeight: '600',
    color: colors.textLight,
  },
  messageFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 4,
    alignSelf: 'flex-end',
  },
  editedLabel: {
    fontSize: 11,
    fontStyle: 'italic',
    marginRight: 4,
  },
  editedLabelMe: {
    color: 'rgba(255, 255, 255, 0.6)',
  },
  editedLabelOther: {
    color: colors.textMuted,
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
    borderWidth: 1,
    borderColor: colors.border,
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
});
