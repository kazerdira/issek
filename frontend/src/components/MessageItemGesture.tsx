import React, { useState, useRef } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  TouchableOpacity, 
  Image,
  Animated,
  PanResponder,
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
const ICON_START_THRESHOLD = 20;

export const MessageItemGesture: React.FC<MessageItemProps> = ({
  message,
  isMe,
  showAvatar,
  onReply,
  onReact,
  onDelete,
  onLongPress,
}) => {
  const [showReactions, setShowReactions] = useState(false);
  const [swipeDirection, setSwipeDirection] = useState<'left' | 'right' | null>(null);
  const translateX = useRef(new Animated.Value(0)).current;
  const replyIconScale = useRef(new Animated.Value(0)).current;
  const replyIconOpacity = useRef(new Animated.Value(0)).current;
  const messageTime = format(new Date(message.created_at), 'HH:mm');

  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onStartShouldSetPanResponderCapture: () => false,
      onMoveShouldSetPanResponder: (_, gestureState) => {
        console.log('🔥 Move check - dx:', gestureState.dx, 'dy:', gestureState.dy);
        // Only activate swipe for horizontal movement
        return Math.abs(gestureState.dx) > 10 && Math.abs(gestureState.dx) > Math.abs(gestureState.dy);
      },
      onMoveShouldSetPanResponderCapture: (_, gestureState) => {
        // Capture horizontal swipes before TouchableOpacity
        return Math.abs(gestureState.dx) > 10 && Math.abs(gestureState.dx) > Math.abs(gestureState.dy);
      },
      onPanResponderGrant: () => {
        console.log('✅ PanResponder granted!');
        translateX.setOffset(0);
      },
      onPanResponderMove: (_, gestureState) => {
        const dx = gestureState.dx;
        const absDx = Math.abs(dx);
        
        // ANY message can be swiped in EITHER direction
        // Swipe RIGHT (dx > 0) = Reply
        // Swipe LEFT (dx < 0) = React
        if (absDx > 10) {
          const clampedDx = Math.min(absDx, MAX_SWIPE);
          
          // Track swipe direction for icon display
          setSwipeDirection(dx > 0 ? 'right' : 'left');
          
          // Set translation (keep original direction)
          translateX.setValue(dx > 0 ? clampedDx : -clampedDx);
          
          // Show icon starting from ICON_START_THRESHOLD
          if (absDx >= ICON_START_THRESHOLD) {
            const progress = Math.min((absDx - ICON_START_THRESHOLD) / (SWIPE_THRESHOLD - ICON_START_THRESHOLD), 1);
            replyIconScale.setValue(progress);
            replyIconOpacity.setValue(progress);
          } else {
            replyIconScale.setValue(0);
            replyIconOpacity.setValue(0);
          }
          
          // Haptic feedback at threshold
          if (absDx >= SWIPE_THRESHOLD && absDx < SWIPE_THRESHOLD + 5) {
            Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
          }
        } else {
          setSwipeDirection(null);
          translateX.setValue(0);
          replyIconScale.setValue(0);
          replyIconOpacity.setValue(0);
        }
      },
      onPanResponderRelease: (_, gestureState) => {
        const absDx = Math.abs(gestureState.dx);
        const dx = gestureState.dx;
        
        if (absDx >= SWIPE_THRESHOLD) {
          // Trigger action based on swipe direction
          // RIGHT = Reply, LEFT = React
          if (dx > 0) {
            // Swipe RIGHT = Reply
            onReply(message);
          } else {
            // Swipe LEFT = React
            setShowReactions(true);
          }
          
          // Bounce animation
          const direction = dx > 0 ? 1 : -1;
          Animated.sequence([
            Animated.timing(translateX, {
              toValue: (SWIPE_THRESHOLD + 15) * direction,
              duration: 80,
              useNativeDriver: true,
            }),
            Animated.spring(translateX, {
              toValue: 0,
              useNativeDriver: true,
              tension: 150,
              friction: 8,
            }),
          ]).start();
          
          Animated.timing(replyIconScale, {
            toValue: 0,
            duration: 200,
            useNativeDriver: true,
          }).start();
          
          Animated.timing(replyIconOpacity, {
            toValue: 0,
            duration: 200,
            useNativeDriver: true,
          }).start();
        } else {
          // Snap back faster and smoother
          Animated.spring(translateX, {
            toValue: 0,
            useNativeDriver: true,
            tension: 150,
            friction: 8,
          }).start();
          
          Animated.timing(replyIconScale, {
            toValue: 0,
            duration: 120,
            useNativeDriver: true,
          }).start();
          
          Animated.timing(replyIconOpacity, {
            toValue: 0,
            duration: 120,
            useNativeDriver: true,
          }).start();
        }
      },
    })
  ).current;

  const handleReaction = (emoji: string) => {
    onReact(message, emoji);
    setShowReactions(false);
  };

  return (
    <View style={styles.container}>
      {/* Reply Icon (RIGHT swipe) */}
      {swipeDirection === 'right' && (
        <Animated.View
          style={[
            styles.replyIconContainer,
            styles.replyIconLeft,
            {
              opacity: replyIconOpacity,
              transform: [{ scale: replyIconScale }],
            },
          ]}
        >
          <Ionicons 
            name="arrow-undo" 
            size={24} 
            color={colors.primary} 
          />
        </Animated.View>
      )}

      {/* React Icon (LEFT swipe) */}
      {swipeDirection === 'left' && (
        <Animated.View
          style={[
            styles.replyIconContainer,
            styles.replyIconRight,
            {
              opacity: replyIconOpacity,
              transform: [{ scale: replyIconScale }],
            },
          ]}
        >
          <Ionicons 
            name="happy" 
            size={24} 
            color={colors.warning} 
          />
        </Animated.View>
      )}

      {/* Message Content with Gesture */}
      <View style={styles.gestureContainer} {...panResponder.panHandlers}>
        <Animated.View
          style={[
            styles.messageWrapper,
            isMe ? styles.messageWrapperMe : styles.messageWrapperOther,
            { transform: [{ translateX }] },
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
                  {message.media_url && (
                    <Image 
                      source={{ uri: message.media_url }}
                      style={[
                        styles.messageImage,
                        !message.content && styles.mediaOnlyImage
                      ]}
                      resizeMode="cover"
                    />
                  )}

                  {message.content && (
                    <Text style={[
                      styles.messageText, 
                      isMe ? styles.messageTextMe : styles.messageTextOther,
                      message.media_url && styles.messageTextWithMedia
                    ]}>
                      {message.content}
                    </Text>
                  )}

                  <View style={[
                    styles.messageFooter,
                    !message.content && message.media_url && styles.mediaOnlyFooter
                  ]}>
                    <Text style={[
                      styles.messageTime, 
                      isMe ? styles.messageTimeMe : styles.messageTimeOther,
                      !message.content && message.media_url && styles.mediaOnlyTime
                    ]}>
                      {messageTime}
                    </Text>
                    {isMe && (
                      <Ionicons
                        name={message.status === 'read' ? 'checkmark-done' : 'checkmark'}
                        size={14}
                        color={
                          !message.content && message.media_url 
                            ? colors.textLight 
                            : (message.status === 'read' ? colors.primary : colors.textLight)
                        }
                        style={{ marginLeft: 4 }}
                      />
                    )}
                  </View>
                </>
              )}
            </TouchableOpacity>
          </View>
        </Animated.View>
      </View>

      {/* Quick Reactions Popup */}
      {showReactions && (
        <View style={[styles.quickReactionsContainer, isMe ? styles.reactionsRight : styles.reactionsLeft]}>
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
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginBottom: 12,
    position: 'relative',
    width: '100%',
  },
  replyIconContainer: {
    position: 'absolute',
    top: '50%',
    marginTop: -12,
    zIndex: 0,
  },
  replyIconLeft: {
    left: 8,
  },
  replyIconRight: {
    right: 8,
  },
  gestureContainer: {
    width: '100%',
  },
  messageWrapper: {
    zIndex: 1,
    paddingHorizontal: 8,
  },
  messageWrapperMe: {
    alignSelf: 'flex-end',
  },
  messageWrapperOther: {
    alignSelf: 'flex-start',
  },
  messageRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
  },
  messageBubble: {
    maxWidth: '75%',
    borderRadius: 18,
    padding: 12,
    marginLeft: 8,
  },
  messageBubbleMe: {
    backgroundColor: colors.primary,
  },
  messageBubbleOther: {
    backgroundColor: '#f0f0f0',
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
    marginBottom: 8,
  },
  mediaOnlyImage: {
    marginBottom: 0,
    borderRadius: 18,
  },
  messageText: {
    fontSize: 16,
    lineHeight: 22,
  },
  messageTextWithMedia: {
    marginTop: 4,
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
  mediaOnlyFooter: {
    position: 'absolute',
    bottom: 8,
    right: 8,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
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
  mediaOnlyTime: {
    color: colors.textLight,
  },
  quickReactionsContainer: {
    position: 'absolute',
    bottom: -40,
    flexDirection: 'row',
    backgroundColor: 'white',
    borderRadius: 25,
    padding: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
    zIndex: 1000,
  },
  reactionsRight: {
    right: 40,
  },
  reactionsLeft: {
    left: 40,
  },
  quickReactionButton: {
    padding: 8,
    marginHorizontal: 2,
  },
  quickReactionEmoji: {
    fontSize: 24,
  },
});
