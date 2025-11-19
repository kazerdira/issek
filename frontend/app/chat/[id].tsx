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
  Keyboard,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { useChatStore, Message } from '../../src/store/chatStore';
import { useAuthStore } from '../../src/store/authStore';
import { chatsAPI } from '../../src/services/api';
import { socketService } from '../../src/services/socket';
import { Avatar } from '../../src/components/Avatar';
import { TypingIndicator } from '../../src/components/TypingIndicator';
import { MessageItemGesture } from '../../src/components/MessageItemGesture';
import { MessageActionsSheet } from '../../src/components/MessageActionsSheet';
import { ImagePickerModal } from '../../src/components/ImagePickerModal';
import { VoiceRecorder } from '../../src/components/VoiceRecorder';
import { VoiceMessageBubble } from '../../src/components/VoiceMessageBubble';
import { uploadVoiceMessage } from '../../src/services/voiceService';
import { colors } from '../../src/theme/colors';
import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import * as DocumentPicker from 'expo-document-picker';
import * as Clipboard from 'expo-clipboard';
import { format } from 'date-fns';

// ✅ TELEGRAM: Helper to determine if timestamp should be shown above message
const shouldShowTimestamp = (currentMsg: Message, prevMsg: Message | null): boolean => {
  if (!prevMsg) return true;
  
  const currentTime = new Date(currentMsg.created_at);
  const prevTime = new Date(prevMsg.created_at);
  
  // Show timestamp if messages are more than 10 minutes apart
  const diffMinutes = (currentTime.getTime() - prevTime.getTime()) / (1000 * 60);
  return diffMinutes > 10;
};

export default function ChatScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams();
  const chatId = typeof id === 'string' ? id : id[0];
  
  const { currentChat, setCurrentChat, messages, setMessages, addMessage, typingUsers, resetChatUnreadCount } = useChatStore();
  const { user } = useAuthStore();
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [replyTo, setReplyTo] = useState<Message | null>(null);
  const [selectedMessage, setSelectedMessage] = useState<Message | null>(null);
  const [showReactions, setShowReactions] = useState(false);
  const [showActionsSheet, setShowActionsSheet] = useState(false);
  const [imageModalVisible, setImageModalVisible] = useState(false);
  const [isRecordingVoice, setIsRecordingVoice] = useState(false);
  const flatListRef = useRef<FlatList>(null);
  const messageInputRef = useRef<TextInput>(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const sendingRef = useRef(false); // Synchronous lock to prevent race conditions

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
      
      // Reset unread count when entering chat
      resetChatUnreadCount(chatId);
      console.log(`Reset unread count for chat ${chatId}`);
    }

    // Cleanup on unmount
    return () => {
      console.log('Chat screen unmounting');
      if (user) {
        socketService.leaveChat(chatId, user.id);
        socketService.sendTyping(chatId, user.id, false);
      }
      // Clear typing timeout to prevent memory leaks
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
        typingTimeoutRef.current = null;
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

  // ✅ Keyboard listener to scroll FlatList when keyboard appears
  useEffect(() => {
    const keyboardWillShow = Keyboard.addListener(
      Platform.OS === 'ios' ? 'keyboardWillShow' : 'keyboardDidShow',
      () => {
        setTimeout(() => {
          flatListRef.current?.scrollToEnd({ animated: true });
        }, 100);
      }
    );

    return () => {
      keyboardWillShow.remove();
    };
  }, []);

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
      
      // Filter out messages deleted by current user ("delete for me")
      const filteredMessages = user 
        ? response.data.filter((msg: any) => !msg.deleted_for?.includes(user.id))
        : response.data;
      
      setMessages(chatId, filteredMessages);
      console.log(`Loaded ${filteredMessages.length} messages (${response.data.length - filteredMessages.length} hidden)`);
      
      // Mark all unread messages as read
      if (user) {
        const unreadMessages = filteredMessages.filter(
          (msg: Message) => msg.sender_id !== user.id && msg.status !== 'read'
        );
        
        if (unreadMessages.length > 0) {
          console.log(`Marking ${unreadMessages.length} messages as read`);
          for (const msg of unreadMessages) {
            try {
              await chatsAPI.markAsRead(msg.id);
            } catch (error) {
              console.error('Error marking message as read:', error);
            }
          }
        }
      }
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
    // Check ref FIRST (synchronous) to prevent race conditions
    if (!inputText.trim() || !user || sending || sendingRef.current) return;
    
    // Set BOTH locks immediately
    sendingRef.current = true;
    setSending(true);

    const messageText = inputText.trim();
    setInputText('');
    const replyToId = replyTo?.id;
    setReplyTo(null);

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
      // Release BOTH locks
      sendingRef.current = false;
      setSending(false);
    }
  };

  const handleImagePicker = () => {
    setImageModalVisible(true);
  };

  const handleImageSelected = async (imageUri: string) => {
    try {
      // Convert URI to base64
      const response = await fetch(imageUri);
      const blob = await response.blob();
      const reader = new FileReader();
      
      reader.onloadend = async () => {
        const base64data = reader.result as string;
        const base64 = base64data.split(',')[1]; // Remove data:image/jpeg;base64, prefix
        
        await sendMediaMessage({
          uri: imageUri,
          type: 'image',
          base64: base64,
        });
      };
      
      reader.readAsDataURL(blob);
    } catch (error) {
      console.error('Error processing image:', error);
      Alert.alert('Error', 'Failed to process image');
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

  // ✅ Voice Recording Handlers
  const handleStartRecording = () => {
    setIsRecordingVoice(true);
  };

  const handleVoiceSend = async (uri: string, duration: number) => {
    setIsRecordingVoice(false);
    
    if (!user) return;

    try {
      setSending(true);
      
      // Upload voice message
      console.log('Uploading voice message...');
      const { mediaUrl } = await uploadVoiceMessage(uri, chatId);
      
      // Send message with voice media
      const response = await chatsAPI.sendMessage(chatId, {
        chat_id: chatId,
        sender_id: user.id,
        content: '', // No text content for voice messages
        message_type: 'voice',
        media_url: mediaUrl,
        media_metadata: {
          duration: duration,
        },
      });

      console.log('Voice message sent successfully');
      
      // Add message locally
      const existingMessage = chatMessages.find(m => m.id === response.data.id);
      if (!existingMessage) {
        addMessage(chatId, response.data);
      }
      
      // Scroll to end
      setTimeout(() => {
        flatListRef.current?.scrollToEnd({ animated: true });
      }, 100);
    } catch (error) {
      console.error('Error sending voice message:', error);
      Alert.alert('Error', 'Failed to send voice message');
    } finally {
      setSending(false);
    }
  };

  const handleVoiceCancel = () => {
    setIsRecordingVoice(false);
  };

  const sendMediaMessage = async (asset: any) => {
    // Check ref FIRST (synchronous) to prevent race conditions
    if (!user || sending || sendingRef.current) return;
    
    // Set BOTH locks immediately
    sendingRef.current = true;
    setSending(true);
    try {
      const messageType = asset.type === 'video' ? 'video' : 'image';
      const mediaUrl = `data:${asset.type};base64,${asset.base64}`;

      const response = await chatsAPI.sendMessage(chatId, {
        chat_id: chatId,
        sender_id: user.id,
        content: '',  // Send empty string for media-only messages
        message_type: messageType,
        media_url: mediaUrl,
      });

      console.log('Media message sent:', response.data.id);
      addMessage(chatId, response.data);
    } catch (error) {
      console.error('Error sending media:', error);
      Alert.alert('Error', 'Failed to send media');
    } finally {
      // Release BOTH locks
      sendingRef.current = false;
      setSending(false);
    }
  };

  const handleReaction = async (messageId: string, emoji: string) => {
    try {
      if (!user) return;

      // Backend now handles toggle logic automatically:
      // - If user already has this emoji → removes it (toggle off)
      // - If user has different emoji → replaces it
      // - If user has no reaction → adds it
      await chatsAPI.addReaction(messageId, emoji);

      setShowReactions(false);
      setSelectedMessage(null);
    } catch (error) {
      console.error('Error handling reaction:', error);
    }
  };

  // New gesture handlers
  const handleReply = (message: Message) => {
    setReplyTo(message);
    messageInputRef.current?.focus();
  };

  const handleReact = async (message: Message, emoji: string) => {
    try {
      // Backend handles toggle logic automatically (single reaction per user)
      await chatsAPI.addReaction(message.id, emoji);
    } catch (error) {
      console.error('Error adding reaction:', error);
      Alert.alert('Error', 'Failed to add reaction');
    }
  };

  const handleDelete = async (message: Message, forEveryone: boolean) => {
    try {
      await chatsAPI.deleteMessage(message.id, forEveryone);
      // Message will be updated via socket
    } catch (error: any) {
      console.error('Error deleting message:', error);
      const errorMessage = error.response?.data?.detail || 'Failed to delete message';
      Alert.alert('Error', errorMessage);
    }
  };

  const handleMessageLongPress = (message: Message) => {
    setSelectedMessage(message);
    setShowActionsSheet(true);
  };

  const handleCopy = async (message: Message) => {
    try {
      await Clipboard.setStringAsync(message.content);
      Alert.alert('Copied', 'Message copied to clipboard');
      setShowActionsSheet(false);
    } catch (error) {
      console.error('Error copying message:', error);
      Alert.alert('Error', 'Failed to copy message');
    }
  };

  const handleForward = (message: Message) => {
    // TODO: Implement forward functionality
    Alert.alert('Forward', 'Forward functionality coming soon!');
    setShowActionsSheet(false);
  };

  const handleEdit = (message: Message) => {
    // TODO: Implement edit functionality
    Alert.alert('Edit', 'Edit functionality coming soon!');
    setShowActionsSheet(false);
  };

  const handleScheduleReminder = (minutes: number) => {
    // TODO: Implement reminder functionality
    Alert.alert('Reminder', `Reminder set for ${minutes} minutes - coming soon!`);
    setShowActionsSheet(false);
  };

  const handleChangeTone = (tone: string) => {
    // TODO: Implement tone change (requires AI)
    Alert.alert('Change Tone', `Change to ${tone} tone - coming soon!`);
    setShowActionsSheet(false);
  };

  const handleDeleteMessage = async (messageId: string) => {
    try {
      await chatsAPI.deleteMessage(messageId);
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

  const getTypingStatus = () => {
    const typingInChat = typingUsers[chatId] || [];
    // Filter out current user (don't show yourself typing)
    const othersTyping = typingInChat.filter(id => id !== user?.id);
    
    if (othersTyping.length === 0) return null;
    
    if (currentChat?.chat_type === 'group') {
      return othersTyping.length === 1 ? '1 person typing...' : `${othersTyping.length} people typing...`;
    }
    
    return 'typing...';
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
          <TypingIndicator size={6} dotColor={colors.textSecondary} />
        </View>
      </View>
    );
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
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
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
              {getTypingStatus() || (getChatOnlineStatus() ? 'Online' : 'Offline')}
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
        style={styles.flatList}
        data={chatMessages}
        renderItem={({ item, index }) => {
          const isMe = item.sender_id === user?.id;
          const showAvatar = !isMe && (index === 0 || chatMessages[index - 1]?.sender_id !== item.sender_id);
          
          // Find the replied-to message if this is a reply
          const repliedToMessage = item.reply_to 
            ? chatMessages.find(msg => msg.id === item.reply_to)
            : null;

          // ✅ TELEGRAM: Check if timestamp should be shown above this message
          const prevMsg = index > 0 ? chatMessages[index - 1] : null;
          const showTimestamp = shouldShowTimestamp(item, prevMsg);
          
          return (
            <>
              {/* ✅ TELEGRAM: Timestamp ABOVE message group */}
              {showTimestamp && (
                <View style={styles.timestampContainer}>
                  <Text style={styles.timestampText}>
                    {format(new Date(item.created_at), 'HH:mm')}
                  </Text>
                </View>
              )}
              
              {/* Render Voice Message or Regular Message */}
              {item.message_type === 'voice' ? (
                <View style={[
                  styles.voiceMessageContainer,
                  isMe ? styles.voiceMessageMe : styles.voiceMessageOther
                ]}>
                  <VoiceMessageBubble
                    mediaUrl={item.media_url || ''}
                    duration={item.media_metadata?.duration || 0}
                    isMe={isMe}
                    messageTime={format(new Date(item.created_at), 'HH:mm')}
                    status={item.status as any}
                  />
                </View>
              ) : (
                <MessageItemGesture
                  message={item}
                  isMe={isMe}
                  showAvatar={showAvatar}
                  userId={user?.id}
                  participantDetails={currentChat?.participant_details || []}
                  repliedToMessage={repliedToMessage}
                  onReply={handleReply}
                  onReact={handleReact}
                  onDelete={handleDelete}
                  onLongPress={handleMessageLongPress}
                />
              )}
            </>
          );
        }}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.messagesList}
        ListFooterComponent={renderTypingIndicator}
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
          onPress={handleImagePicker}
        >
          <Ionicons name="add-circle" size={28} color={colors.primary} />
        </TouchableOpacity>
        
        <TextInput
          ref={messageInputRef}
          style={styles.input}
          placeholder="Type a message..."
          value={inputText}
          onChangeText={handleTyping}
          onFocus={() => {
            setTimeout(() => {
              flatListRef.current?.scrollToEnd({ animated: true });
            }, 300);
          }}
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
          <TouchableOpacity 
            style={styles.inputAction}
            onPress={handleStartRecording}
          >
            <Ionicons name="mic" size={24} color={colors.primary} />
          </TouchableOpacity>
        )}
      </View>

      {/* Voice Recorder */}
      {isRecordingVoice && (
        <VoiceRecorder
          onSend={handleVoiceSend}
          onCancel={handleVoiceCancel}
        />
      )}

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

      {/* Message Actions Sheet */}
      {selectedMessage && (
        <MessageActionsSheet
          visible={showActionsSheet}
          message={selectedMessage}
          isMe={selectedMessage.sender_id === user?.id}
          onClose={() => setShowActionsSheet(false)}
          onReply={() => {
            handleReply(selectedMessage);
            setShowActionsSheet(false);
          }}
          onEdit={() => {
            handleEdit(selectedMessage);
          }}
          onDelete={(forEveryone: boolean) => {
            handleDelete(selectedMessage, forEveryone);
            setShowActionsSheet(false);
          }}
          onCopy={() => {
            handleCopy(selectedMessage);
          }}
          onForward={() => {
            handleForward(selectedMessage);
          }}
          onScheduleReminder={handleScheduleReminder}
          onChangeTone={handleChangeTone}
        />
      )}

      {/* Image Picker Modal */}
      <ImagePickerModal
        visible={imageModalVisible}
        onClose={() => setImageModalVisible(false)}
        onImageSelected={handleImageSelected}
      />
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
  flatList: {
    flex: 1,
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
  // ✅ TELEGRAM: Timestamp above message groups
  timestampContainer: {
    alignItems: 'center',
    marginVertical: 12,
  },
  timestampText: {
    fontSize: 12,
    color: colors.textMuted,
    backgroundColor: 'rgba(0, 0, 0, 0.05)',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },
  messagesList: {
    padding: 16,
    paddingHorizontal: 0,  // ✅ Remove horizontal padding (MessageItemGesture handles it)
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
  mediaBubble: {
    backgroundColor: 'transparent',
    padding: 0,
    margin: 0,
    maxWidth: '80%',
    borderRadius: 0,
  },
  senderName: {
    fontSize: 12,
    fontWeight: '600',
    color: colors.primary,
    marginBottom: 4,
  },
  messageImage: {
    width: 220,
    height: 220,
    borderRadius: 12,
    marginBottom: 0,
  },
  mediaMessageFooter: {
    position: 'absolute',
    bottom: 8,
    right: 8,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    flexDirection: 'row',
    alignItems: 'center',
  },
  mediaMessageTime: {
    color: colors.textLight,
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
    borderRadius: 20,
    paddingHorizontal: 8,
    paddingVertical: 6,
    gap: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 8,
    elevation: 5,
  },
  reactionButton: {
    width: 40,
    height: 40,
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 20,
    backgroundColor: colors.surface,
  },
  reactionButtonText: {
    fontSize: 22,
  },
  voiceMessageContainer: {
    marginBottom: 8,
    paddingHorizontal: 16,
  },
  voiceMessageMe: {
    alignItems: 'flex-end',
  },
  voiceMessageOther: {
    alignItems: 'flex-start',
  },
  typingContainer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    marginVertical: 8,
    paddingHorizontal: 16,
  },
  typingBubble: {
    backgroundColor: colors.surface,
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 12,
    marginLeft: 8,
    minWidth: 60,
    justifyContent: 'center',
    alignItems: 'center',
  },
  replyPreview: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    paddingHorizontal: 16,
    paddingVertical: 12,
    gap: 12,
  },
  replyLine: {
    width: 3,
    height: '100%',
    backgroundColor: colors.primary,
    borderRadius: 1.5,
  },
  replyContent: {
    flex: 1,
  },
  replyName: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.primary,
    marginBottom: 2,
  },
  replyText: {
    fontSize: 14,
    color: colors.textSecondary,
  },
});
