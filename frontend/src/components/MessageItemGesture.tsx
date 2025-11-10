import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Image } from 'react-native';
import { GestureDetector, Gesture } from 'react-native-gesture-handler';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
  interpolate,
  interpolateColor,
  runOnJS,
} from 'react-native-reanimated';
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

export const MessageItemGesture: React.FC<MessageItemProps> = ({
  message,
  isMe,
  showAvatar,
  onReply,
  onReact,
  onDelete,
  onLongPress,
}) => {
  console.log('🎯 MessageItemGesture (Gesture Handler) rendering:', message.id.substring(0, 8));
  
  const [showReactions, setShowReactions] = useState(false);
  const translateX = useSharedValue(0);
  const messageTime = format(new Date(message.created_at), 'HH:mm');

  const triggerHaptic = () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
  };

  const triggerReply = () => {
    onReply(message);
  };

  const triggerReactions = () => {
    setShowReactions(true);
  };

  // Pan gesture for swipe
  const panGesture = Gesture.Pan()
    .onUpdate((event) => {
      if (isMe) {
        // Swipe left for reactions
        if (event.translationX < 0) {
          translateX.value = Math.max(event.translationX, -MAX_SWIPE);
          
          // Haptic at threshold
          if (Math.abs(event.translationX) > SWIPE_THRESHOLD && Math.abs(event.translationX) < SWIPE_THRESHOLD + 10) {
            runOnJS(triggerHaptic)();
          }
        }
      } else {
        // Swipe right for reply
        if (event.translationX > 0) {
          translateX.value = Math.min(event.translationX, MAX_SWIPE);
          
          // Haptic at threshold
          if (event.translationX > SWIPE_THRESHOLD && event.translationX < SWIPE_THRESHOLD + 10) {
            runOnJS(triggerHaptic)();
          }
        }
      }
    })
    .onEnd((event) => {
      if (isMe && event.translationX < -SWIPE_THRESHOLD) {
        // Trigger reactions
        runOnJS(triggerReactions)();
      } else if (!isMe && event.translationX > SWIPE_THRESHOLD) {
        // Trigger reply
        runOnJS(triggerReply)();
      }
      
      // Animate back
      translateX.value = withSpring(0);
    });

  // Animated styles
  const animatedStyle = useAnimatedStyle(() => {
    const backgroundColor = isMe
      ? interpolateColor(
          translateX.value,
          [-MAX_SWIPE, 0],
          ['rgba(255, 235, 59, 0.3)', 'transparent']
        )
      : interpolateColor(
          translateX.value,
          [0, MAX_SWIPE],
          ['transparent', 'rgba(33, 150, 243, 0.3)']
        );

    return {
      transform: [{ translateX: translateX.value }],
      backgroundColor,
    };
  });

  const iconOpacity = useAnimatedStyle(() => {
    const opacity = isMe
      ? interpolate(
          translateX.value,
          [-MAX_SWIPE, -SWIPE_THRESHOLD, 0],
          [1, 0.5, 0]
        )
      : interpolate(
          translateX.value,
          [0, SWIPE_THRESHOLD, MAX_SWIPE],
          [0, 0.5, 1]
        );

    return { opacity };
  });

  const handleReaction = (emoji: string) => {
    onReact(message, emoji);
    setShowReactions(false);
  };

  return (
    <View style={[styles.container, isMe ? styles.containerMe : styles.containerOther]}>
      {/* Swipe Icons */}
      {!isMe && (
        <Animated.View style={[styles.swipeIconLeft, iconOpacity]}>
          <Ionicons name="arrow-undo" size={24} color={colors.primary} />
        </Animated.View>
      )}

      {isMe && (
        <Animated.View style={[styles.swipeIconRight, iconOpacity]}>
          <Ionicons name="happy" size={24} color={colors.warning} />
        </Animated.View>
      )}

      <GestureDetector gesture={panGesture}>
        <Animated.View style={[styles.messageWrapper, animatedStyle]}>
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
      </GestureDetector>

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
    width: '100%',
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
