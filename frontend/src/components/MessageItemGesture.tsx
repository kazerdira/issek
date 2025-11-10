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
  userId?: string; // For checking user's reactions
  repliedToMessage?: Message | null; // The actual message being replied to
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
  userId,
  repliedToMessage,
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

  // Render reply preview if message is a reply - TELEGRAM STYLE (AT TOP OF BUBBLE)
  const renderReplyPreview = () => {
    if (!message.reply_to) return null;

    // Use backend-populated message first, then fallback to passed prop
    const replied = message.reply_to_message || repliedToMessage;
    if (!replied) return null;

    // ✅ TELEGRAM: Very light, subtle backgrounds
    const bgColor = isMe 
      ? 'rgba(255, 255, 255, 0.08)'  // ✅ Very subtle
      : 'rgba(0, 0, 0, 0.03)';       // ✅ Barely visible

    const textColor = isMe
      ? 'rgba(255, 255, 255, 0.9)'
      : 'rgba(0, 0, 0, 0.7)';

    const borderColor = isMe 
      ? 'rgba(255, 255, 255, 0.5)'
      : colors.primary;

    // Truncate content for compact preview
    const truncateText = (text: string, maxLength = 30) => {
      if (!text) return '';
      if (text.length <= maxLength) return text;
      return text.slice(0, maxLength) + '...';
    };

    return (
      <TouchableOpacity 
        style={[
          styles.replyPreviewContainer, 
          { 
            backgroundColor: bgColor,
            borderLeftColor: borderColor,
          }
        ]}
        onPress={() => {
          // TODO: Jump to original message
          Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
        }}
        activeOpacity={0.7}
      >
        <Text style={[
          styles.replySenderName,
          { color: textColor }
        ]} numberOfLines={1}>
          {replied.sender?.display_name || 'Someone'}
        </Text>
        <Text style={[
          styles.replyMessagePreview,
          { color: textColor, opacity: 0.7 }
        ]} numberOfLines={1}>
          {truncateText(replied.content || (replied.media_url ? '📷 Photo' : 'Message'))}
        </Text>
      </TouchableOpacity>
    );
  };

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
      <View style={styles.gestureContainer}>
        <View
          style={[
            styles.messageWrapper,
            isMe ? styles.messageWrapperMe : styles.messageWrapperOther,
          ]}
        >
          <View style={styles.messageRow}>
              {showAvatar && !isMe && (
                <Avatar uri={message.sender?.avatar} name={message.sender?.display_name || 'User'} size={32} />
              )}
              {!showAvatar && !isMe && <View style={{ width: 32 }} />}

              {/* ✅ Bubble + Reactions Container with Gesture (ONLY on bubble) */}
              <Animated.View 
                style={[
                  styles.bubbleWithReactions,
                  { transform: [{ translateX }] },
                ]} 
                {...panResponder.panHandlers}
              >
                <TouchableOpacity
                  activeOpacity={0.9}
                  onLongPress={() => {
                    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
                    onLongPress(message);
                  }}
                  style={[
                    styles.messageBubble, 
                    isMe ? styles.messageBubbleMe : styles.messageBubbleOther,
                    message.reply_to && { paddingTop: 0 },  // ✅ No top padding when reply
                    !message.reply_to && { paddingTop: 10 },  // ✅ Normal top padding without reply
                    !message.content && message.media_url && {
                      paddingHorizontal: 0,  // ✅ No horizontal padding for media-only
                      paddingTop: 0,         // ✅ No top padding for media-only
                      paddingBottom: 0,      // ✅ CRITICAL: Remove ALL padding
                      overflow: 'hidden',    // ✅ Ensure image respects border radius
                    }
                  ]}
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
                  {/* Reply Preview */}
                  {renderReplyPreview()}

                  {/* ✅ Wrapper for actual content with margin after reply */}
                  <View style={message.reply_to && styles.actualMessageContent}>
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
                  </View>

                  {/* ✅ TELEGRAM: Timestamp ONLY for media-only messages */}
                  {!message.content && message.media_url && (
                    <View style={styles.mediaOnlyFooter}>
                      <Text style={styles.mediaOnlyTime}>
                        {messageTime}
                      </Text>
                      {isMe && (
                        <Ionicons
                          name={message.status === 'read' ? 'checkmark-done' : 'checkmark'}
                          size={14}
                          color={colors.textLight}
                          style={{ marginLeft: 4 }}
                        />
                      )}
                    </View>
                  )}
                </>
              )}
                </TouchableOpacity>

                {/* Display Existing Reactions - INSIDE bubbleWithReactions */}
                {message.reactions && Object.keys(message.reactions).length > 0 && (
                  <View style={[styles.reactionsDisplay, isMe ? styles.reactionsDisplayMe : styles.reactionsDisplayOther]}>
                    {Object.entries(message.reactions).map(([emoji, userIds]) => {
                      if (!userIds || userIds.length === 0) return null;
                      return (
                        <TouchableOpacity
                          key={emoji}
                          style={styles.reactionBadge}
                          onPress={() => onReact(message, emoji)}
                        >
                          <Text style={styles.reactionBadgeEmoji}>{emoji}</Text>
                          <Text style={styles.reactionBadgeCount}>{userIds.length}</Text>
                        </TouchableOpacity>
                      );
                    })}
                  </View>
                )}
              </Animated.View>
          </View>
        </View>
      </View>

      {/* Quick Reactions Popup */}
      {showReactions && (
        <View style={[styles.quickReactionsContainer, isMe ? styles.reactionsRight : styles.reactionsLeft]}>
          {QUICK_REACTIONS.map((emoji) => {
            // Check if user already has this reaction
            const userHasThisReaction = userId && message.reactions?.[emoji]?.includes(userId);
            
            return (
              <TouchableOpacity
                key={emoji}
                style={[
                  styles.quickReactionButton,
                  userHasThisReaction && styles.quickReactionButtonActive
                ]}
                onPress={() => handleReaction(emoji)}
                activeOpacity={0.7}
              >
                <Text style={styles.quickReactionEmoji}>{emoji}</Text>
              </TouchableOpacity>
            );
          })}
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
    marginBottom: 2,      // ✅ TELEGRAM: Tighter spacing
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
    paddingHorizontal: 8,    // ✅ TELEGRAM: Reduced from 12
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
  bubbleWithReactions: {
    position: 'relative',
    marginBottom: 10,
  },
  messageBubble: {
    maxWidth: '75%',
    paddingHorizontal: 10,   // ✅ TELEGRAM: Tighter (was 12)
    paddingVertical: 8,      // ✅ TELEGRAM: Consistent vertical padding
    marginLeft: 8,
    position: 'relative',
    overflow: 'hidden',
    elevation: 0,            // ✅ TELEGRAM: No shadow (flat design)
    shadowOpacity: 0,        // ✅ TELEGRAM: No shadow
  },
  messageBubbleMe: {
    backgroundColor: colors.primary,
    borderTopLeftRadius: 18,
    borderTopRightRadius: 18,
    borderBottomLeftRadius: 18,
    borderBottomRightRadius: 4,  // Tail on sent
  },
  messageBubbleOther: {
    backgroundColor: '#F1F3F4',  // ✅ TELEGRAM: Light gray
    borderTopLeftRadius: 18,
    borderTopRightRadius: 18,
    borderBottomLeftRadius: 4,   // Tail on received
    borderBottomRightRadius: 18,
  },
  senderName: {
    fontSize: 12,
    fontWeight: '600',
    color: colors.primary,
    marginBottom: 4,
  },
  messageImage: {
    width: 240,
    height: 240,
    borderRadius: 12,
    marginBottom: 0,
  },
  mediaOnlyImage: {
    marginBottom: 0,
    width: 280,        // ✅ TELEGRAM: Larger for media-only
    height: 280,
    borderRadius: 0,   // ✅ Bubble handles radius
  },
  messageText: {
    fontSize: 16,
    lineHeight: 21,      // ✅ TELEGRAM: Tighter line height
    flexWrap: 'wrap',
    flexShrink: 1,
  },
  messageTextWithMedia: {
    marginTop: 4,
  },
  messageTextMe: {
    color: '#FFFFFF',
  },
  messageTextOther: {
    color: colors.text,
  },
  deletedText: {
    fontStyle: 'italic',
    opacity: 0.7,
  },
  // ✅ TELEGRAM: Removed - No longer used for regular messages
  // Only used for media-only (see mediaOnlyFooter below)
  // ✅ TELEGRAM: Only for media-only messages
  mediaOnlyFooter: {
    position: 'absolute',
    bottom: 8,
    right: 8,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    flexDirection: 'row',
    alignItems: 'center',
  },
  mediaOnlyTime: {
    color: colors.textLight,
    fontSize: 11,
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
    borderRadius: 20,
    backgroundColor: 'transparent',
  },
  quickReactionButtonActive: {
    backgroundColor: colors.primaryLight,
    transform: [{ scale: 1.1 }],
  },
  quickReactionEmoji: {
    fontSize: 24,
  },
  // Reaction Display Badges - ✅ TELEGRAM: Stick to bubble
  reactionsDisplay: {
    position: 'absolute',
    bottom: -6,          // ✅ CLOSER overlap (was -8)
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 4,              // ✅ Tighter spacing (was 6)
    zIndex: 10,
    maxWidth: '85%',     // ✅ Prevent going too wide
  },
  reactionsDisplayMe: {
    right: 6,            // ✅ Stick closer to edge (was 8)
  },
  reactionsDisplayOther: {
    left: 40,            // ✅ Stay aligned (was 44)
  },
  reactionBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderRadius: 10,
    paddingHorizontal: 6,
    paddingVertical: 2,    // ✅ TELEGRAM: Even tighter
    gap: 3,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.12,
    shadowRadius: 3,
    elevation: 2,
    borderWidth: 0.5,
    borderColor: 'rgba(0,0,0,0.08)',
  },
  reactionBadgeEmoji: {
    fontSize: 13,          // ✅ TELEGRAM: Smaller
  },
  reactionBadgeCount: {
    fontSize: 10,          // ✅ TELEGRAM: Smaller
    color: colors.text,
    fontWeight: '600',
  },
  // ✅ TELEGRAM: Compact Reply Preview
  replyPreviewContainer: {
    paddingVertical: 4,    // ✅ Very compact
    paddingHorizontal: 8,
    paddingLeft: 8,
    borderLeftWidth: 2,    // ✅ Thinner line (was 3)
    marginBottom: 6,
    width: '100%',
  },
  actualMessageContent: {
    marginTop: 2,          // ✅ Very small gap
  },
  replySenderName: {
    fontSize: 13,            // ✅ Back to 13px (was 14)
    fontWeight: '600',
    marginBottom: 1,         // ✅ Tighter (was 2)
    // Color set inline
  },
  replyMessagePreview: {
    fontSize: 13,            // ✅ Back to 13px (was 14)
    lineHeight: 16,          // ✅ Tighter (was 18)
    // Color set inline
  },
});
