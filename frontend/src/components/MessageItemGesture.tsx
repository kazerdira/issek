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
const SWIPE_THRESHOLD = 70;
const MAX_SWIPE = 100;

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
        console.log('👆 Swipe dx:', gestureState.dx, 'isMe:', isMe);
        
        // Swipe RIGHT on other messages for reply
        // Swipe LEFT on my messages for reactions
        const direction = isMe ? -1 : 1;
        const dx = gestureState.dx * direction;
        
        if (dx > 0) {
          const clampedDx = Math.min(dx, MAX_SWIPE);
          translateX.setValue(clampedDx * direction);
          
          // Animate reply/reaction icon
          const progress = Math.min(clampedDx / SWIPE_THRESHOLD, 1);
          replyIconScale.setValue(progress);
          replyIconOpacity.setValue(progress);
          
          // Haptic feedback at threshold
          if (clampedDx >= SWIPE_THRESHOLD && clampedDx < SWIPE_THRESHOLD + 5) {
            Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
          }
        } else {
          translateX.setValue(0);
          replyIconScale.setValue(0);
          replyIconOpacity.setValue(0);
        }
      },
      onPanResponderRelease: (_, gestureState) => {
        const direction = isMe ? -1 : 1;
        const dx = Math.abs(gestureState.dx);
        
        if (dx >= SWIPE_THRESHOLD) {
          console.log('✅ Swipe threshold reached!', isMe ? 'reactions' : 'reply');
          
          // Trigger action
          if (isMe) {
            setShowReactions(true);
          } else {
            onReply(message);
          }
          
          // Animate back with bounce
          Animated.sequence([
            Animated.timing(translateX, {
              toValue: (SWIPE_THRESHOLD + 10) * direction,
              duration: 100,
              useNativeDriver: true,
            }),
            Animated.spring(translateX, {
              toValue: 0,
              useNativeDriver: true,
              tension: 100,
              friction: 10,
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
          // Snap back
          Animated.spring(translateX, {
            toValue: 0,
            useNativeDriver: true,
            tension: 100,
            friction: 10,
          }).start();
          
          Animated.timing(replyIconScale, {
            toValue: 0,
            duration: 150,
            useNativeDriver: true,
          }).start();
          
          Animated.timing(replyIconOpacity, {
            toValue: 0,
            duration: 150,
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
    <View style={[styles.container, isMe ? styles.containerMe : styles.containerOther]}>
      {/* Reply/React Icon - positioned behind the message */}
      <Animated.View
        style={[
          styles.replyIconContainer,
          isMe ? styles.replyIconRight : styles.replyIconLeft,
          {
            opacity: replyIconOpacity,
            transform: [{ scale: replyIconScale }],
          },
        ]}
      >
        <Ionicons 
          name={isMe ? "happy" : "arrow-undo"} 
          size={24} 
          color={isMe ? colors.warning : colors.primary} 
        />
      </Animated.View>

      {/* Message Content with Gesture */}
      <View style={styles.gestureContainer} {...panResponder.panHandlers}>
        <Animated.View
          style={[
            styles.messageWrapper,
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
                      style={styles.messageImage}
                      resizeMode="cover"
                    />
                  )}

                  {message.content && (
                    <Text style={[styles.messageText, isMe ? styles.messageTextMe : styles.messageTextOther]}>
                      {message.content}
                    </Text>
                  )}
                </>
              )}

              <View style={styles.messageFooter}>
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
  },
  containerMe: {
    alignItems: 'flex-end',
  },
  containerOther: {
    alignItems: 'flex-start',
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
  },
  messageRow: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    alignItems: 'flex-end',
  },
  messageBubble: {
    maxWidth: '70%',
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
    width: 250,
    height: 250,
    borderRadius: 12,
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
  messageTime: {
    fontSize: 11,
  },
  messageTimeMe: {
    color: 'rgba(255, 255, 255, 0.7)',
  },
  messageTimeOther: {
    color: colors.textMuted,
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
