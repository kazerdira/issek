// frontend/src/components/MessageBubble.tsx
import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Animated } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../theme/colors';
import { Message } from '../store/chatStore';
import { format } from 'date-fns';

interface MessageBubbleProps {
  message: Message;
  isMe: boolean;
  showAvatar: boolean;
  onLongPress: () => void;
  onReply: () => void;
  onReact: (emoji: string) => void;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  isMe,
  showAvatar,
  onLongPress,
  onReply,
  onReact,
}) => {
  const [showQuickReactions, setShowQuickReactions] = useState(false);
  const quickReactions = ['❤️', '👍', '😂', '😮', '😢', '🙏'];

  const messageTime = format(new Date(message.created_at), 'HH:mm');

  return (
    <View style={styles.container}>
      {/* Reply indicator */}
      {message.reply_to && (
        <View style={styles.replyIndicator}>
          <View style={styles.replyBar} />
          <Text style={styles.replyText} numberOfLines={1}>
            Replying to: {message.reply_to_message?.content}
          </Text>
        </View>
      )}

      {/* Message bubble */}
      <TouchableOpacity
        onLongPress={onLongPress}
        onPress={() => setShowQuickReactions(!showQuickReactions)}
        style={[
          styles.bubble,
          isMe ? styles.bubbleMe : styles.bubbleOther,
        ]}
      >
        {/* Forwarded label */}
        {message.forwarded_from && (
          <View style={styles.forwardedBadge}>
            <Ionicons name="arrow-forward" size={10} color={colors.textSecondary} />
            <Text style={styles.forwardedText}>Forwarded</Text>
          </View>
        )}

        {/* Message content */}
        <Text style={[styles.messageText, isMe ? styles.textMe : styles.textOther]}>
          {message.deleted ? '🚫 This message was deleted' : message.content}
        </Text>

        {/* Message footer */}
        <View style={styles.footer}>
          {message.edited && !message.deleted && (
            <Text style={styles.editedLabel}>edited</Text>
          )}
          <Text style={[styles.time, isMe ? styles.timeMe : styles.timeOther]}>
            {messageTime}
          </Text>
          {isMe && !message.deleted && (
            <Ionicons
              name={message.status === 'read' ? 'checkmark-done' : 'checkmark'}
              size={14}
              color={message.status === 'read' ? colors.primary : 'rgba(255,255,255,0.7)'}
              style={{ marginLeft: 4 }}
            />
          )}
        </View>
      </TouchableOpacity>

      {/* Reactions */}
      {Object.keys(message.reactions).length > 0 && (
        <View style={styles.reactionsContainer}>
          {Object.entries(message.reactions).map(([emoji, users]) => (
            <TouchableOpacity
              key={emoji}
              style={styles.reactionBubble}
              onPress={() => onReact(emoji)}
            >
              <Text style={styles.reactionEmoji}>{emoji}</Text>
              <Text style={styles.reactionCount}>{users.length}</Text>
            </TouchableOpacity>
          ))}
        </View>
      )}

      {/* Quick reactions panel */}
      {showQuickReactions && (
        <Animated.View style={styles.quickReactionsPanel}>
          {quickReactions.map((emoji) => (
            <TouchableOpacity
              key={emoji}
              style={styles.quickReaction}
              onPress={() => {
                onReact(emoji);
                setShowQuickReactions(false);
              }}
            >
              <Text style={styles.quickReactionEmoji}>{emoji}</Text>
            </TouchableOpacity>
          ))}
        </Animated.View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginBottom: 8,
  },
  replyIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
    paddingLeft: 8,
  },
  replyBar: {
    width: 3,
    height: 30,
    backgroundColor: colors.primary,
    borderRadius: 2,
    marginRight: 8,
  },
  replyText: {
    fontSize: 12,
    color: colors.textSecondary,
    fontStyle: 'italic',
    flex: 1,
  },
  bubble: {
    maxWidth: '80%',
    padding: 12,
    borderRadius: 16,
    elevation: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
  },
  bubbleMe: {
    backgroundColor: colors.primary,
    borderBottomRightRadius: 4,
    alignSelf: 'flex-end',
  },
  bubbleOther: {
    backgroundColor: colors.messageReceived,
    borderBottomLeftRadius: 4,
    alignSelf: 'flex-start',
  },
  forwardedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  forwardedText: {
    fontSize: 10,
    fontStyle: 'italic',
    color: colors.textSecondary,
    marginLeft: 4,
  },
  messageText: {
    fontSize: 16,
    lineHeight: 22,
  },
  textMe: {
    color: colors.textLight,
  },
  textOther: {
    color: colors.text,
  },
  footer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 4,
    justifyContent: 'flex-end',
  },
  editedLabel: {
    fontSize: 10,
    fontStyle: 'italic',
    color: colors.textMuted,
    marginRight: 4,
  },
  time: {
    fontSize: 11,
  },
  timeMe: {
    color: 'rgba(255, 255, 255, 0.7)',
  },
  timeOther: {
    color: colors.textMuted,
  },
  reactionsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: 4,
  },
  reactionBubble: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: 12,
    paddingHorizontal: 8,
    paddingVertical: 4,
    marginRight: 4,
    borderWidth: 1,
    borderColor: colors.border,
  },
  reactionEmoji: {
    fontSize: 14,
  },
  reactionCount: {
    fontSize: 11,
    marginLeft: 4,
    color: colors.textSecondary,
    fontWeight: '600',
  },
  quickReactionsPanel: {
    flexDirection: 'row',
    backgroundColor: colors.surface,
    borderRadius: 24,
    padding: 8,
    marginTop: 8,
    alignSelf: 'flex-start',
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
  },
  quickReaction: {
    padding: 8,
  },
  quickReactionEmoji: {
    fontSize: 24,
  },
});

// frontend/src/components/TypingIndicator.tsx
import React, { useEffect, useRef } from 'react';
import { View, Text, StyleSheet, Animated } from 'react-native';
import { colors } from '../theme/colors';

interface TypingIndicatorProps {
  users: string[];
}

export const TypingIndicator: React.FC<TypingIndicatorProps> = ({ users }) => {
  const dot1 = useRef(new Animated.Value(0)).current;
  const dot2 = useRef(new Animated.Value(0)).current;
  const dot3 = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const animate = (dot: Animated.Value, delay: number) => {
      Animated.loop(
        Animated.sequence([
          Animated.delay(delay),
          Animated.timing(dot, {
            toValue: 1,
            duration: 400,
            useNativeDriver: true,
          }),
          Animated.timing(dot, {
            toValue: 0,
            duration: 400,
            useNativeDriver: true,
          }),
        ])
      ).start();
    };

    animate(dot1, 0);
    animate(dot2, 200);
    animate(dot3, 400);
  }, []);

  if (users.length === 0) return null;

  const typingText = users.length === 1 
    ? `${users[0]} is typing` 
    : `${users.length} people are typing`;

  return (
    <View style={styles.container}>
      <Text style={styles.text}>{typingText}</Text>
      <View style={styles.dotsContainer}>
        <Animated.View
          style={[
            styles.dot,
            {
              opacity: dot1,
              transform: [
                {
                  translateY: dot1.interpolate({
                    inputRange: [0, 1],
                    outputRange: [0, -5],
                  }),
                },
              ],
            },
          ]}
        />
        <Animated.View
          style={[
            styles.dot,
            {
              opacity: dot2,
              transform: [
                {
                  translateY: dot2.interpolate({
                    inputRange: [0, 1],
                    outputRange: [0, -5],
                  }),
                },
              ],
            },
          ]}
        />
        <Animated.View
          style={[
            styles.dot,
            {
              opacity: dot3,
              transform: [
                {
                  translateY: dot3.interpolate({
                    inputRange: [0, 1],
                    outputRange: [0, -5],
                  }),
                },
              ],
            },
          ]}
        />
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    backgroundColor: colors.surface,
  },
  text: {
    fontSize: 14,
    color: colors.textSecondary,
    fontStyle: 'italic',
    marginRight: 8,
  },
  dotsContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.primary,
    marginHorizontal: 2,
  },
});

// frontend/src/components/ChatHeader.tsx
import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../theme/colors';
import { Avatar } from './Avatar';

interface ChatHeaderProps {
  name: string;
  avatar?: string;
  isOnline: boolean;
  onBack: () => void;
  onCall?: () => void;
  onVideoCall?: () => void;
  onMore?: () => void;
}

export const ChatHeader: React.FC<ChatHeaderProps> = ({
  name,
  avatar,
  isOnline,
  onBack,
  onCall,
  onVideoCall,
  onMore,
}) => {
  return (
    <View style={styles.container}>
      <TouchableOpacity onPress={onBack} style={styles.backButton}>
        <Ionicons name="arrow-back" size={24} color={colors.textLight} />
      </TouchableOpacity>

      <TouchableOpacity style={styles.centerContent}>
        <Avatar uri={avatar} name={name} size={40} online={isOnline} />
        <View style={styles.info}>
          <Text style={styles.name}>{name}</Text>
          <Text style={styles.status}>
            {isOnline ? 'Online' : 'Offline'}
          </Text>
        </View>
      </TouchableOpacity>

      <View style={styles.actions}>
        {onCall && (
          <TouchableOpacity onPress={onCall} style={styles.actionButton}>
            <Ionicons name="call" size={20} color={colors.textLight} />
          </TouchableOpacity>
        )}
        {onVideoCall && (
          <TouchableOpacity onPress={onVideoCall} style={styles.actionButton}>
            <Ionicons name="videocam" size={20} color={colors.textLight} />
          </TouchableOpacity>
        )}
        {onMore && (
          <TouchableOpacity onPress={onMore} style={styles.actionButton}>
            <Ionicons name="ellipsis-vertical" size={20} color={colors.textLight} />
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 8,
    paddingTop: 48,
    backgroundColor: colors.primary,
  },
  backButton: {
    padding: 8,
  },
  centerContent: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    marginLeft: 8,
  },
  info: {
    marginLeft: 12,
  },
  name: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.textLight,
  },
  status: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.8)',
  },
  actions: {
    flexDirection: 'row',
  },
  actionButton: {
    padding: 8,
    marginLeft: 4,
  },
});

// frontend/src/components/LoadingSpinner.tsx
import React from 'react';
import { View, ActivityIndicator, StyleSheet } from 'react-native';
import { colors } from '../theme/colors';

interface LoadingSpinnerProps {
  size?: 'small' | 'large';
  color?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'large',
  color = colors.primary,
}) => {
  return (
    <View style={styles.container}>
      <ActivityIndicator size={size} color={color} />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
});
