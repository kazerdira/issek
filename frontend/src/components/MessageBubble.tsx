import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Modal,
  Pressable,
  Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../theme/colors';
import { format, isToday, isYesterday } from 'date-fns';

export interface MessageBubbleProps {
  id: string;
  content: string;
  sender_id: string;
  sender_name: string;
  created_at: string;
  edited?: boolean;
  isOwn: boolean;
  reactions?: { [emoji: string]: string[] };
  reply_to_message?: {
    id: string;
    content: string;
    sender_name: string;
  };
  onReply?: (messageId: string, content: string) => void;
  onEdit?: (messageId: string, content: string) => void;
  onDelete?: (messageId: string) => void;
  onForward?: (messageId: string) => void;
  onReact?: (messageId: string, emoji: string) => void;
  onRemoveReaction?: (messageId: string, emoji: string) => void;
  currentUserId?: string;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  id,
  content,
  sender_name,
  created_at,
  edited = false,
  isOwn,
  reactions,
  reply_to_message,
  onReply,
  onEdit,
  onDelete,
  onForward,
  onReact,
  onRemoveReaction,
  currentUserId,
}) => {
  const [showActions, setShowActions] = useState(false);
  const [showReactions, setShowReactions] = useState(false);

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    if (isToday(date)) {
      return format(date, 'HH:mm');
    } else if (isYesterday(date)) {
      return `Yesterday ${format(date, 'HH:mm')}`;
    } else {
      return format(date, 'MMM dd, HH:mm');
    }
  };

  const handleLongPress = () => {
    setShowActions(true);
  };

  const handleReaction = (emoji: string) => {
    const userReacted = reactions?.[emoji]?.includes(currentUserId || '');
    if (userReacted) {
      onRemoveReaction?.(id, emoji);
    } else {
      onReact?.(id, emoji);
    }
    setShowReactions(false);
  };

  const quickReactions = ['👍', '❤️', '😂', '😮', '😢', '🙏'];

  const totalReactions = reactions
    ? Object.values(reactions).reduce((sum, users) => sum + users.length, 0)
    : 0;

  return (
    <>
      <View style={[styles.container, isOwn ? styles.ownContainer : styles.otherContainer]}>
        <TouchableOpacity
          onLongPress={handleLongPress}
          activeOpacity={0.7}
          style={styles.bubbleWrapper}
        >
          {/* Reply Preview */}
          {reply_to_message && (
            <View style={styles.replyPreview}>
              <View style={[styles.replyBorder, isOwn && styles.replyBorderOwn]} />
              <View style={styles.replyContent}>
                <Text style={styles.replySender}>{reply_to_message.sender_name}</Text>
                <Text style={styles.replyText} numberOfLines={1}>
                  {reply_to_message.content}
                </Text>
              </View>
            </View>
          )}

          {/* Message Bubble */}
          <View style={[styles.bubble, isOwn ? styles.ownBubble : styles.otherBubble]}>
            {!isOwn && (
              <Text style={styles.senderName}>{sender_name}</Text>
            )}
            <Text style={[styles.content, isOwn ? styles.ownContent : styles.otherContent]}>
              {content}
            </Text>
            <View style={styles.footer}>
              <Text style={[styles.time, isOwn ? styles.ownTime : styles.otherTime]}>
                {formatTime(created_at)}
              </Text>
              {edited && (
                <Text style={[styles.edited, isOwn ? styles.ownTime : styles.otherTime]}>
                  {' '}• edited
                </Text>
              )}
            </View>
          </View>

          {/* Reactions */}
          {totalReactions > 0 && (
            <View style={[styles.reactionsContainer, isOwn && styles.reactionsContainerOwn]}>
              {Object.entries(reactions || {}).map(([emoji, users]) => {
                const userReacted = users.includes(currentUserId || '');
                return (
                  <TouchableOpacity
                    key={emoji}
                    style={[styles.reactionBubble, userReacted && styles.reactionBubbleActive]}
                    onPress={() => handleReaction(emoji)}
                  >
                    <Text style={styles.reactionEmoji}>{emoji}</Text>
                    <Text style={styles.reactionCount}>{users.length}</Text>
                  </TouchableOpacity>
                );
              })}
            </View>
          )}
        </TouchableOpacity>
      </View>

      {/* Actions Modal */}
      <Modal
        visible={showActions}
        transparent
        animationType="fade"
        onRequestClose={() => setShowActions(false)}
      >
        <Pressable style={styles.modalOverlay} onPress={() => setShowActions(false)}>
          <View style={styles.actionsModal}>
            {/* Quick Reactions */}
            <View style={styles.quickReactions}>
              {quickReactions.map((emoji) => (
                <TouchableOpacity
                  key={emoji}
                  style={styles.quickReactionButton}
                  onPress={() => handleReaction(emoji)}
                >
                  <Text style={styles.quickReactionEmoji}>{emoji}</Text>
                </TouchableOpacity>
              ))}
            </View>

            {/* Action Buttons */}
            <View style={styles.actions}>
              <TouchableOpacity
                style={styles.actionButton}
                onPress={() => {
                  onReply?.(id, content);
                  setShowActions(false);
                }}
              >
                <Ionicons name="arrow-undo" size={20} color={colors.text} />
                <Text style={styles.actionText}>Reply</Text>
              </TouchableOpacity>

              {isOwn && (
                <TouchableOpacity
                  style={styles.actionButton}
                  onPress={() => {
                    onEdit?.(id, content);
                    setShowActions(false);
                  }}
                >
                  <Ionicons name="create-outline" size={20} color={colors.text} />
                  <Text style={styles.actionText}>Edit</Text>
                </TouchableOpacity>
              )}

              <TouchableOpacity
                style={styles.actionButton}
                onPress={() => {
                  onForward?.(id);
                  setShowActions(false);
                }}
              >
                <Ionicons name="arrow-redo" size={20} color={colors.text} />
                <Text style={styles.actionText}>Forward</Text>
              </TouchableOpacity>

              {isOwn && (
                <TouchableOpacity
                  style={[styles.actionButton, styles.deleteButton]}
                  onPress={() => {
                    onDelete?.(id);
                    setShowActions(false);
                  }}
                >
                  <Ionicons name="trash-outline" size={20} color={colors.error} />
                  <Text style={[styles.actionText, styles.deleteText]}>Delete</Text>
                </TouchableOpacity>
              )}
            </View>
          </View>
        </Pressable>
      </Modal>
    </>
  );
};

const styles = StyleSheet.create({
  container: {
    marginVertical: 4,
    marginHorizontal: 12,
    maxWidth: '80%',
  },
  ownContainer: {
    alignSelf: 'flex-end',
  },
  otherContainer: {
    alignSelf: 'flex-start',
  },
  bubbleWrapper: {
    position: 'relative',
  },
  bubble: {
    borderRadius: 16,
    paddingHorizontal: 12,
    paddingVertical: 8,
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.1,
        shadowRadius: 2,
      },
      android: {
        elevation: 2,
      },
    }),
  },
  ownBubble: {
    backgroundColor: colors.messageSent,
    borderBottomRightRadius: 4,
  },
  otherBubble: {
    backgroundColor: colors.messageReceived,
    borderBottomLeftRadius: 4,
  },
  senderName: {
    fontSize: 12,
    fontWeight: '600',
    color: colors.primary,
    marginBottom: 4,
  },
  content: {
    fontSize: 16,
    lineHeight: 20,
  },
  ownContent: {
    color: colors.textLight,
  },
  otherContent: {
    color: colors.text,
  },
  footer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 4,
  },
  time: {
    fontSize: 11,
  },
  ownTime: {
    color: 'rgba(255, 255, 255, 0.7)',
  },
  otherTime: {
    color: colors.textSecondary,
  },
  edited: {
    fontSize: 11,
    fontStyle: 'italic',
  },
  replyPreview: {
    flexDirection: 'row',
    backgroundColor: 'rgba(0, 0, 0, 0.05)',
    borderRadius: 8,
    padding: 8,
    marginBottom: 6,
  },
  replyBorder: {
    width: 3,
    backgroundColor: colors.primary,
    borderRadius: 2,
    marginRight: 8,
  },
  replyBorderOwn: {
    backgroundColor: 'rgba(255, 255, 255, 0.5)',
  },
  replyContent: {
    flex: 1,
  },
  replySender: {
    fontSize: 12,
    fontWeight: '600',
    color: colors.primary,
    marginBottom: 2,
  },
  replyText: {
    fontSize: 13,
    color: colors.textSecondary,
  },
  reactionsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: 4,
    gap: 4,
  },
  reactionsContainerOwn: {
    justifyContent: 'flex-end',
  },
  reactionBubble: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: 12,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderWidth: 1,
    borderColor: colors.border,
  },
  reactionBubbleActive: {
    backgroundColor: colors.primaryLight,
    borderColor: colors.primary,
  },
  reactionEmoji: {
    fontSize: 14,
    marginRight: 4,
  },
  reactionCount: {
    fontSize: 12,
    fontWeight: '600',
    color: colors.text,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  actionsModal: {
    backgroundColor: colors.background,
    borderRadius: 16,
    padding: 16,
    width: '85%',
    maxWidth: 400,
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.3,
        shadowRadius: 8,
      },
      android: {
        elevation: 8,
      },
    }),
  },
  quickReactions: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    marginBottom: 12,
  },
  quickReactionButton: {
    padding: 8,
  },
  quickReactionEmoji: {
    fontSize: 28,
  },
  actions: {
    gap: 8,
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    borderRadius: 8,
    backgroundColor: colors.surface,
  },
  actionText: {
    fontSize: 16,
    marginLeft: 12,
    color: colors.text,
  },
  deleteButton: {
    backgroundColor: 'rgba(255, 107, 107, 0.1)',
  },
  deleteText: {
    color: colors.error,
  },
});
