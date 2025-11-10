import React, { useRef, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Animated,
  PanResponder,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { format } from 'date-fns';
import { Avatar } from './Avatar';
import { colors } from '../theme/colors';
import { Message } from '../store/chatStore';
import * as Haptics from 'expo-haptics';

interface MessageItemProps {
  message: Message;
  isMe: boolean;
  showAvatar: boolean;
  onReply: (message: Message) => void;
  onReact: (message: Message, emoji: string) => void;
  onDelete: (message: Message, forEveryone: boolean) => void;
  onLongPress: (message: Message) => void;
}

const QUICK_REACTIONS = ['👍', '❤️', '😂', '😮', '😢', '🙏'];
const SWIPE_THRESHOLD = 50;
const MAX_SWIPE = 100;

export const MessageItem: React.FC<MessageItemProps> = ({
  message,
  isMe,
  showAvatar,
  onReply,
  onReact,
  onDelete,
  onLongPress,
}) => {
  const translateX = useRef(new Animated.Value(0)).current;
  const [showReactions, setShowReactions] = useState(false);
  const messageTime = format(new Date(message.created_at), 'HH:mm');

  // Swipe gesture handler
  const panResponder = useRef(
    PanResponder.create({
      onMoveShouldSetPanResponder: (_, gestureState) => {
        // Only respond to horizontal swipes
        return Math.abs(gestureState.dx) > Math.abs(gestureState.dy) && Math.abs(gestureState.dx) > 10;
      },
      onPanResponderGrant: () => {
        translateX.setOffset(0);
      },
      onPanResponderMove: (_, gestureState) => {
        if (isMe) {
          // Swipe left for reactions
          if (gestureState.dx < 0) {
            const clampedValue = Math.max(gestureState.dx, -MAX_SWIPE);
            translateX.setValue(clampedValue);
            
            // Haptic feedback at threshold
            if (Math.abs(gestureState.dx) > SWIPE_THRESHOLD && Math.abs(gestureState.dx) < SWIPE_THRESHOLD + 5) {
              Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
            }
          }
        } else {
          // Swipe right for reply
          if (gestureState.dx > 0) {
            const clampedValue = Math.min(gestureState.dx, MAX_SWIPE);
            translateX.setValue(clampedValue);
            
            // Haptic feedback at threshold
            if (gestureState.dx > SWIPE_THRESHOLD && gestureState.dx < SWIPE_THRESHOLD + 5) {
              Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
            }
          }
        }
      },
      onPanResponderRelease: (_, gestureState) => {
        if (isMe && gestureState.dx < -SWIPE_THRESHOLD) {
          // Trigger reactions
          Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
          setShowReactions(true);
          
          // Animate back
          Animated.spring(translateX, {
            toValue: 0,
            useNativeDriver: true,
            tension: 80,
            friction: 10,
          }).start();
        } else if (!isMe && gestureState.dx > SWIPE_THRESHOLD) {
          // Trigger reply
          Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
          onReply(message);
          
          // Animate back
          Animated.spring(translateX, {
            toValue: 0,
            useNativeDriver: true,
            tension: 80,
            friction: 10,
          }).start();
        } else {
          // Cancel - animate back
          Animated.spring(translateX, {
            toValue: 0,
            useNativeDriver: true,
            tension: 80,
            friction: 10,
          }).start();
        }
      },
    })
  ).current;

  const handleReaction = (emoji: string) => {
    onReact(message, emoji);
    setShowReactions(false);
  };

  const handleDeletePress = () => {
    Alert.alert(
      'Delete Message',
      'Choose delete option',
      [
        {
          text: 'Cancel',
          style: 'cancel',
        },
        {
          text: 'Delete for Me',
          onPress: () => onDelete(message, false),
        },
        ...(isMe
          ? [
              {
                text: 'Delete for Everyone',
                onPress: () => onDelete(message, true),
                style: 'destructive' as const,
              },
            ]
          : []),
      ],
      { cancelable: true }
    );
  };

  // Calculate background color based on swipe progress
  const backgroundColor = translateX.interpolate({
    inputRange: isMe ? [-MAX_SWIPE, 0] : [0, MAX_SWIPE],
    outputRange: isMe ? ['rgba(255, 235, 59, 0.3)', 'transparent'] : ['rgba(33, 150, 243, 0.3)', 'transparent'],
    extrapolate: 'clamp',
  });

  // Icon opacity based on swipe progress
  const iconOpacity = translateX.interpolate({
    inputRange: isMe ? [-MAX_SWIPE, -SWIPE_THRESHOLD, 0] : [0, SWIPE_THRESHOLD, MAX_SWIPE],
    outputRange: [1, 0.5, 0],
    extrapolate: 'clamp',
  });

  const renderReactions = () => {
    const reactions = message.reactions || {};
    const reactionEntries = Object.entries(reactions);

    if (reactionEntries.length === 0) return null;

    return (
      <View style={styles.reactionsContainer}>
        {reactionEntries.map(([emoji, users]) => (
          <View key={emoji} style={styles.reactionBubble}>
            <Text style={styles.reactionEmoji}>{emoji}</Text>
            {users.length > 1 && (
              <Text style={styles.reactionCount}>{users.length}</Text>
            )}
          </View>
        ))}
      </View>
    );
  };

  return (
    <View style={[styles.container, isMe ? styles.containerMe : styles.containerOther]}>
      <Animated.View
        style={[
          styles.swipeBackground,
          {
            backgroundColor,
          },
        ]}
      />

      {/* Swipe Icons */}
      {!isMe && (
        <Animated.View
          style={[
            styles.swipeIconLeft,
            {
              opacity: iconOpacity,
            },
          ]}
        >
          <Ionicons name="arrow-undo" size={24} color={colors.primary} />
        </Animated.View>
      )}

      {isMe && (
        <Animated.View
          style={[
            styles.swipeIconRight,
            {
              opacity: iconOpacity,
            },
          ]}
        >
          <Ionicons name="happy" size={24} color={colors.warning} />
        </Animated.View>
      )}

      <Animated.View
        {...panResponder.panHandlers}
        style={[
          styles.messageWrapper,
          {
            transform: [{ translateX }],
          },
        ]}
      >
        <View style={styles.messageRow}>
          {showAvatar && !isMe && (
            <Avatar uri={message.sender?.avatar} name={message.sender?.display_name || 'User'} size={32} />
          )}
          {!showAvatar && !isMe && <View style={{ width: 32 }} />}

          <TouchableOpacity
            activeOpacity={0.9}
            onLongPress={() => {
              Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
              onLongPress(message);
            }}
            style={[styles.messageBubble, isMe ? styles.messageBubbleMe : styles.messageBubbleOther]}
          >
            {!isMe && showAvatar && (
              <Text style={styles.senderName}>{message.sender?.display_name}</Text>
            )}

            {message.deleted ? (
              <Text style={[styles.deletedText, isMe ? styles.messageTextMe : styles.messageTextOther]}>
                🚫 This message was deleted
              </Text>
            ) : (
              <>
                {message.reply_to && (
                  <View style={styles.replyContainer}>
                    <View style={styles.replyBar} />
                    <Text style={styles.replyText} numberOfLines={2}>
                      Replying to message...
                    </Text>
                  </View>
                )}

                <Text style={[styles.messageText, isMe ? styles.messageTextMe : styles.messageTextOther]}>
                  {message.content}
                </Text>
              </>
            )}

            <View style={styles.messageFooter}>
              {message.edited && <Text style={styles.editedText}>edited</Text>}
              <Text style={[styles.messageTime, isMe ? styles.messageTimeMe : styles.messageTimeOther]}>
                {messageTime}
              </Text>
              {isMe && (
                <Ionicons
                  name={message.status === 'read' ? 'checkmark-done' : 'checkmark'}
                  size={14}
                  color={message.status === 'read' ? colors.primary : colors.textLight}
                  style={{ marginLeft: 4 }}
                />
              )}
            </View>

            {renderReactions()}
          </TouchableOpacity>
        </View>
      </Animated.View>

      {/* Quick Reactions Popup */}
      {showReactions && (
        <Animated.View style={[styles.quickReactionsContainer, isMe ? styles.reactionsRight : styles.reactionsLeft]}>
          {QUICK_REACTIONS.map((emoji) => (
            <TouchableOpacity
              key={emoji}
              style={styles.quickReactionButton}
              onPress={() => handleReaction(emoji)}
            >
              <Text style={styles.quickReactionEmoji}>{emoji}</Text>
            </TouchableOpacity>
          ))}
          <TouchableOpacity
            style={styles.quickReactionButton}
            onPress={() => setShowReactions(false)}
          >
            <Ionicons name="close" size={20} color={colors.textSecondary} />
          </TouchableOpacity>
        </Animated.View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginBottom: 12,
    position: 'relative',
  },
  containerMe: {
    alignItems: 'flex-end',
  },
  containerOther: {
    alignItems: 'flex-start',
  },
  swipeBackground: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    left: 0,
    right: 0,
    borderRadius: 16,
  },
  swipeIconLeft: {
    position: 'absolute',
    left: 16,
    top: '50%',
    marginTop: -12,
    zIndex: 1,
  },
  swipeIconRight: {
    position: 'absolute',
    right: 16,
    top: '50%',
    marginTop: -12,
    zIndex: 1,
  },
  messageWrapper: {
    maxWidth: '85%',
  },
  messageRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
  },
  messageBubble: {
    maxWidth: '100%',
    padding: 12,
    borderRadius: 16,
    marginLeft: 8,
    position: 'relative',
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
  deletedText: {
    fontStyle: 'italic',
    opacity: 0.7,
  },
  messageFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 4,
    justifyContent: 'flex-end',
  },
  editedText: {
    fontSize: 10,
    color: colors.textMuted,
    marginRight: 4,
    fontStyle: 'italic',
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
    borderRadius: 8,
    padding: 8,
    marginBottom: 8,
  },
  replyBar: {
    width: 3,
    backgroundColor: colors.primary,
    borderRadius: 2,
    marginRight: 8,
  },
  replyText: {
    flex: 1,
    fontSize: 13,
    color: colors.textSecondary,
    fontStyle: 'italic',
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
    backgroundColor: 'rgba(0, 0, 0, 0.05)',
    borderRadius: 12,
    paddingHorizontal: 8,
    paddingVertical: 2,
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
  quickReactionsContainer: {
    position: 'absolute',
    bottom: -50,
    flexDirection: 'row',
    backgroundColor: colors.surface,
    borderRadius: 24,
    padding: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
    zIndex: 1000,
  },
  reactionsLeft: {
    left: 40,
  },
  reactionsRight: {
    right: 40,
  },
  quickReactionButton: {
    padding: 8,
    marginHorizontal: 2,
  },
  quickReactionEmoji: {
    fontSize: 24,
  },
});
