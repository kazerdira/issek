import React, { useEffect, useState, useRef, useCallback } from 'react';
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
  Alert,
  Modal,
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
import * as ImagePicker from 'expo-image-picker';
import * as DocumentPicker from 'expo-document-picker';

export default function ChatScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams();
  const chatId = typeof id === 'string' ? id : id[0];
  
  const { currentChat, setCurrentChat, messages, setMessages, addMessage } = useChatStore();
  const { user } = useAuthStore();
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [replyTo, setReplyTo] = useState<Message | null>(null);
  const [selectedMessage, setSelectedMessage] = useState<Message | null>(null);
  const [showReactions, setShowReactions] = useState(false);
  const flatListRef = useRef<FlatList>(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Subscribe to messages for this chat
  const chatMessages = messages[chatId] || [];

  useEffect(() => {
    console.log('Chat screen mounted for chatId:', chatId);
    loadChat();
    loadMessages();

    // Join the chat room via socket
    if (user) {
      console.log('Joining chat via socket');
      socketService.joinChat(chatId, user.id);
    }

    // Cleanup on unmount
    return () => {
      console.log('Chat screen unmounting');
      if (user) {
        socketService.leaveChat(chatId, user.id);
        socketService.sendTyping(chatId, user.id, false);
      }
    };
  }, [chatId, user]);

  // Auto-scroll when new messages arrive
  useEffect(() => {
    if (chatMessages.length > 0) {
      setTimeout(() => {
        flatListRef.current?.scrollToEnd({ animated: true });
      }, 100);
    }
  }, [chatMessages.length]);

  const loadChat = async () => {
    try {
      const response = await chatsAPI.getChat(chatId);
      setCurrentChat(response.data);
      console.log('Chat loaded:', response.data.id);
    } catch (error) {
      console.error('Error loading chat:', error);
      Alert.alert('Error', 'Failed to load chat');
    }
  };

  const loadMessages = async () => {
    try {
      console.log('Loading messages for chat:', chatId);
      const response = await chatsAPI.getMessages(chatId);
      setMessages(chatId, response.data);
      console.log(`Loaded ${response.data.length} messages`);
    } catch (error) {
      console.error('Error loading messages:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTyping = (text: string) => {
    setInputText(text);

    if (!user) return;

    // Clear existing timeout
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    // Send typing indicator
    socketService.sendTyping(chatId, user.id, true);

    // Stop typing after 2 seconds of inactivity
    typingTimeoutRef.current = setTimeout(() => {
      socketService.sendTyping(chatId, user.id, false);
    }, 2000);
  };

  const handleSend = async () => {
    if (!inputText.trim() || !user) return;

    const messageText = inputText.trim();
    setInputText('');
    const replyToId = replyTo?.id;
    setReplyTo(null);
    setSending(true);

    // Stop typing indicator
    socketService.sendTyping(chatId, user.id, false);
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    try {
      const response = await chatsAPI.sendMessage(chatId, {
        chat_id: chatId,
        sender_id: user.id,
        content: messageText,
        message_type: 'text',
        reply_to: replyToId,
      });

      console.log('Message sent successfully:', response.data.id);
      
      // The message should arrive via socket, but add it locally as backup
      const existingMessage = chatMessages.find(m => m.id === response.data.id);
      if (!existingMessage) {
        addMessage(chatId, response.data);
      }
      
      // Scroll to end
      setTimeout(() => {
        flatListRef.current?.scrollToEnd({ animated: true });
      }, 100);
    } catch (error: any) {
      console.error('Error sending message:', error);
      Alert.alert('Error', 'Failed to send message');
      // Restore the text if send failed
      setInputText(messageText);
    } finally {
      setSending(false);
    }
  };

  const handleImagePicker = async () => {
    try {
      const permissionResult = await ImagePicker.requestMediaLibraryPermissionsAsync();
      
      if (!permissionResult.granted) {
        Alert.alert('Permission required', 'Please allow access to your photo library');
        return;
      }

      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.All,
        allowsEditing: true,
        quality: 0.8,
        base64: true,
      });

      if (!result.canceled && result.assets[0]) {
        const asset = result.assets[0];
        await sendMediaMessage(asset);
      }
    } catch (error) {
      console.error('Error picking image:', error);
      Alert.alert('Error', 'Failed to pick image');
    }
  };

  const handleDocumentPicker = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: '*/*',
        copyToCacheDirectory: true,
      });

      if (result.type === 'success') {
        // Handle document upload
        Alert.alert('Document Selected', `File: ${result.name}`);
        // Implement file upload logic here
      }
    } catch (error) {
      console.error('Error picking document:', error);
    }
  };

  const sendMediaMessage = async (asset: any) => {
    if (!user) return;

    setSending(true);
    try {
      const messageType = asset.type === 'video' ? 'video' : 'image';
      const mediaUrl = `data:${asset.type};base64,${asset.base64}`;

      const response = await chatsAPI.sendMessage(chatId, {
        chat_id: chatId,
        sender_id: user.id,
        content: asset.fileName || 'Media',
        message_type: messageType,
        media_url: mediaUrl,
      });

      console.log('Media message sent:', response.data.id);
      addMessage(chatId, response.data);
    } catch (error) {
      console.error('Error sending media:', error);
      Alert.alert('Error', 'Failed to send media');
    } finally {
      setSending(false);
    }
  };

  const handleReaction = async (messageId: string, emoji: string) => {
    try {
      const message = chatMessages.find(m => m.id === messageId);
      if (!message || !user) return;

      const hasReacted = message.reactions[emoji]?.includes(user.id);

      if (hasReacted) {
        await chatsAPI.removeReaction(messageId, emoji);
      } else {
        await chatsAPI.addReaction(messageId, emoji);
      }

      setShowReactions(false);
      setSelectedMessage(null);
    } catch (error) {
      console.error('Error handling reaction:', error);
    }
  };

  const handleLongPress = (message: Message) => {
    if (message.sender_id !== user?.id) return;
    
    Alert.alert(
      'Message Options',
      '',
      [
        {
          text: 'Reply',
          onPress: () => setReplyTo(message),
        },
        {
          text: 'React',
          onPress: () => {
            setSelectedMessage(message);
            setShowReactions(true);
          },
        },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: () => handleDeleteMessage(message.id),
        },
        {
          text: 'Cancel',
          style: 'cancel',
        },
      ]
    );
  };

  const handleDeleteMessage = async (messageId: string) => {
    try {
      await chatsAPI.deleteMessage(messageId, true);
    } catch (error) {
      console.error('Error deleting message:', error);
      Alert.alert('Error', 'Failed to delete message');
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

  const renderReplyPreview = () => {
    if (!replyTo) return null;

    return (
      <View style={styles.replyPreview}>
        <View style={styles.replyLine} />
        <View style={styles.replyContent}>
          <Text style={styles.replyName}>{replyTo.sender?.display_name}</Text>
          <Text style={styles.replyText} numberOfLines={1}>
            {replyTo.content}
          </Text>
        </View>
        <TouchableOpacity onPress={() => setReplyTo(null)}>
          <Ionicons name="close" size={20} color={colors.textSecondary} />
        </TouchableOpacity>
      </View>
    );
  };

  const renderMessage = ({ item, index }: { item: Message; index: number }) => {
    const isMe = item.sender_id === user?.id;
    const showAvatar = !isMe && (index === 0 || chatMessages[index - 1]?.sender_id !== item.sender_id);
    const messageTime = format(new Date(item.created_at), 'HH:mm');

    const hasReactions = Object.keys(item.reactions).length > 0;
    const replyToMessage = item.reply_to 
      ? chatMessages.find(m => m.id === item.reply_to)
      : null;

    return (
      <TouchableOpacity
        onLongPress={() => handleLongPress(item)}
        style={[styles.messageContainer, isMe ? styles.messageContainerMe : styles.messageContainerOther]}
      >
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
          
          {replyToMessage && (
            <View style={styles.replyContainer}>
              <View style={styles.replyIndicator} />
              <View>
                <Text style={styles.replyToName}>{replyToMessage.sender?.display_name}</Text>
                <Text style={styles.replyToText} numberOfLines={1}>{replyToMessage.content}</Text>
              </View>
            </View>
          )}

          {item.media_url && (
            <Image
              source={{ uri: item.media_url }}
              style={styles.messageImage}
              resizeMode="cover"
            />
          )}
          
          <Text style={[styles.messageText, isMe ? styles.messageTextMe : styles.messageTextOther]}>
            {item.deleted ? '🚫 This message was deleted' : item.content}
          </Text>
          
          {hasReactions && (
            <View style={styles.reactionsContainer}>
              {Object.entries(item.reactions).map(([emoji, userIds]) => (
                <TouchableOpacity
                  key={emoji}
                  style={styles.reactionBubble}
                  onPress={() => handleReaction(item.id, emoji)}
                >
                  <Text style={styles.reactionEmoji}>{emoji}</Text>
                  <Text style={styles.reactionCount}>{userIds.length}</Text>
                </TouchableOpacity>
              ))}
            </View>
          )}
          
          <View style={styles.messageFooter}>
            <Text style={[styles.messageTime, isMe ? styles.messageTimeMe : styles.messageTimeOther]}>
              {messageTime}
              {item.edited && ' (edited)'}
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

  const quickReactions = ['👍', '❤️', '😂', '😮', '😢', '🙏'];

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={90}
    >
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity 
          onPress={() => router.back()} 
          style={styles.backButton}
        >
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
        data={chatMessages}
        renderItem={renderMessage}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.messagesList}
        onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: false })}
        ListEmptyComponent={
          <View style={styles.emptyState}>
            <Ionicons name="chatbubbles-outline" size={64} color={colors.textMuted} />
            <Text style={styles.emptyText}>No messages yet</Text>
            <Text style={styles.emptySubtext}>Start the conversation</Text>
          </View>
        }
      />

      {/* Reply Preview */}
      {renderReplyPreview()}

      {/* Input */}
      <View style={styles.inputContainer}>
        <TouchableOpacity 
          style={styles.inputAction}
          onPress={() => {
            Alert.alert(
              'Add Attachment',
              '',
              [
                { text: 'Photo/Video', onPress: handleImagePicker },
                { text: 'Document', onPress: handleDocumentPicker },
                { text: 'Cancel', style: 'cancel' },
              ]
            );
          }}
        >
          <Ionicons name="add-circle" size={28} color={colors.primary} />
        </TouchableOpacity>
        
        <TextInput
          style={styles.input}
          placeholder="Type a message..."
          value={inputText}
          onChangeText={handleTyping}
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

      {/* Reaction Modal */}
      <Modal
        visible={showReactions}
        transparent
        animationType="fade"
        onRequestClose={() => setShowReactions(false)}
      >
        <TouchableOpacity 
          style={styles.modalOverlay}
          activeOpacity={1}
          onPress={() => setShowReactions(false)}
        >
          <View style={styles.reactionsModal}>
            {quickReactions.map(emoji => (
              <TouchableOpacity
                key={emoji}
                style={styles.reactionButton}
                onPress={() => selectedMessage && handleReaction(selectedMessage.id, emoji)}
              >
                <Text style={styles.reactionButtonText}>{emoji}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </TouchableOpacity>
      </Modal>
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
  messageImage: {
    width: 200,
    height: 200,
    borderRadius: 8,
    marginBottom: 8,
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
  replyContainer: {
    flexDirection: 'row',
    backgroundColor: 'rgba(0, 0, 0, 0.1)',
    padding: 8,
    borderRadius: 8,
    marginBottom: 8,
  },
  replyIndicator: {
    width: 3,
    backgroundColor: colors.primary,
    marginRight: 8,
    borderRadius: 2,
  },
  replyToName: {
    fontSize: 12,
    fontWeight: '600',
    color: colors.primary,
  },
  replyToText: {
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: 2,
  },
  reactionsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: 4,
    gap: 4,
  },
  reactionBubble: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.1)',
    borderRadius: 12,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  reactionEmoji: {
    fontSize: 14,
  },
  reactionCount: {
    fontSize: 11,
    marginLeft: 2,
    color: colors.textSecondary,
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
  replyPreview: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surface,
    padding: 12,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  replyLine: {
    width: 3,
    height: '100%',
    backgroundColor: colors.primary,
    marginRight: 12,
    borderRadius: 2,
  },
  replyContent: {
    flex: 1,
  },
  replyName: {
    fontSize: 12,
    fontWeight: '600',
    color: colors.primary,
  },
  replyText: {
    fontSize: 14,
    color: colors.textSecondary,
    marginTop: 2,
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
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  reactionsModal: {
    flexDirection: 'row',
    backgroundColor: colors.card,
    borderRadius: 24,
    padding: 12,
    gap: 8,
  },
  reactionButton: {
    width: 48,
    height: 48,
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 24,
    backgroundColor: colors.surface,
  },
  reactionButtonText: {
    fontSize: 24,
  },
});
