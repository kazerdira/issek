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
  
  const { currentChat, setCurrentChat, messages, setMessages, addMessage, typingUsers } = useChatStore();
  const { user } = useAuthStore();
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
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
        // Stop typing when leaving chat
        socketService.sendTyping(chatId, user.id, false);
      }
    };
  }, [chatId]);

  // Auto-scroll when new messages arrive
  useEffect(() => {
    if (messages[chatId]?.length > 0) {
      setTimeout(() => {
        flatListRef.current?.scrollToEnd({ animated: true });
      }, 100);
    }
  }, [messages[chatId]?.length]);

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
      // Send message - socket will handle adding it to the store
      await chatsAPI.sendMessage(chatId, {
        chat_id: chatId,
        sender_id: user.id,
        content: messageText,
        message_type: 'text',
      });

      // Stop typing indicator after sending
      socketService.sendTyping(chatId, user.id, false);
    } catch (error) {
      console.error('Error sending message:', error);
      setInputText(messageText);
    } finally {
      setSending(false);
    }
  };

  const handleTextChange = (text: string) => {
    setInputText(text);
    
    if (!user) return;

    // Send typing indicator
    if (text.length > 0) {
      socketService.sendTyping(chatId, user.id, true);
      
      // Clear existing timeout
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
      
      // Stop typing after 3 seconds of inactivity
      typingTimeoutRef.current = setTimeout(() => {
        socketService.sendTyping(chatId, user.id, false);
      }, 3000);
    } else {
      socketService.sendTyping(chatId, user.id, false);
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

  const getTypingUsers = () => {
    if (!typingUsers[chatId]) return [];
    return typingUsers[chatId].filter(userId => userId !== user?.id);
  };

  const renderTypingIndicator = () => {
    const typing = getTypingUsers();
    if (typing.length === 0) return null;

    const otherUser = currentChat?.participant_details?.find((p) => typing.includes(p.id));
    const name = otherUser?.display_name || 'Someone';

    return (
      <View style={styles.typingContainer}>
        <Avatar
          uri={otherUser?.avatar}
          name={name}
          size={32}
        />
        <View style={styles.typingBubble}>
          <View style={styles.typingDots}>
            <View style={[styles.typingDot, styles.typingDot1]} />
            <View style={[styles.typingDot, styles.typingDot2]} />
            <View style={[styles.typingDot, styles.typingDot3]} />
          </View>
        </View>
      </View>
    );
  };

  const renderMessage = ({ item, index }: { item: Message; index: number }) => {
    const isMe = item.sender_id === user?.id;
    const showAvatar = !isMe && (index === 0 || messages[chatId]?.[index - 1]?.sender_id !== item.sender_id);
    const messageTime = format(new Date(item.created_at), 'HH:mm');

    // Check if message is an image
    const isImage = item.message_type === 'image' || item.media_url;

    return (
      <View style={[styles.messageContainer, isMe ? styles.messageContainerMe : styles.messageContainerOther]}>
        {showAvatar && !isMe && (
          <Avatar
            uri={item.sender?.avatar}
            name={item.sender?.display_name || 'User'}
            size={32}
          />
        )}
        {!showAvatar && !isMe && <View style={{ width: 32 }} />}
        
        <View style={[styles.messageBubble, isMe ? styles.messageBubbleMe : styles.messageBubbleOther]}>
          {!isMe && showAvatar && (
            <Text style={styles.senderName}>{item.sender?.display_name}</Text>
          )}
          
          {isImage && item.media_url ? (
            <View style={styles.imageContainer}>
              <Image
                source={{ uri: item.media_url }}
                style={styles.messageImage}
                resizeMode="cover"
              />
              {item.content && item.content !== item.media_url && (
                <Text style={[styles.messageText, isMe ? styles.messageTextMe : styles.messageTextOther, styles.imageCaption]}>
                  {item.content}
                </Text>
              )}
            </View>
          ) : (
            <Text style={[styles.messageText, isMe ? styles.messageTextMe : styles.messageTextOther]}>
              {item.content}
            </Text>
          )}
          
          <View style={styles.messageFooter}>
            <Text style={[styles.messageTime, isMe ? styles.messageTimeMe : styles.messageTimeOther]}>
              {messageTime}
            </Text>
            {isMe && (
              <Ionicons
                name={item.status === 'read' ? 'checkmark-done' : 'checkmark'}
                size={14}
                color={item.status === 'read' ? colors.primary : colors.textLight}
                style={{ marginLeft: 4 }}
              />
            )}
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
              {getTypingUsers().length > 0 
                ? 'typing...' 
                : getChatOnlineStatus() 
                  ? 'Online' 
                  : 'Offline'}
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
        ListFooterComponent={renderTypingIndicator}
      />

      {/* Input */}
      <View style={styles.inputContainer}>
        <TouchableOpacity style={styles.inputAction}>
          <Ionicons name="add-circle" size={28} color={colors.primary} />
        </TouchableOpacity>
        
        <TextInput
          style={styles.input}
          placeholder="Type a message..."
          value={inputText}
          onChangeText={handleTextChange}
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
  imageContainer: {
    overflow: 'hidden',
    borderRadius: 8,
  },
  messageImage: {
    width: 200,
    height: 200,
    borderRadius: 8,
    marginBottom: 4,
  },
  imageCaption: {
    marginTop: 8,
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
  typingContainer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    marginBottom: 12,
    marginTop: 8,
  },
  typingBubble: {
    backgroundColor: colors.messageReceived,
    borderRadius: 16,
    borderBottomLeftRadius: 4,
    padding: 12,
    marginLeft: 8,
    minWidth: 60,
  },
  typingDots: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  typingDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.textSecondary,
    marginHorizontal: 2,
  },
  typingDot1: {
    animation: 'typing 1.4s infinite',
  },
  typingDot2: {
    animation: 'typing 1.4s infinite 0.2s',
  },
  typingDot3: {
    animation: 'typing 1.4s infinite 0.4s',
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
});
