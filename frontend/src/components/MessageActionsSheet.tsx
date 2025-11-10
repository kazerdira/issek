import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Modal,
  TouchableOpacity,
  ScrollView,
  TextInput,
  Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../theme/colors';
import { Message } from '../store/chatStore';

interface MessageActionsSheetProps {
  visible: boolean;
  message: Message | null;
  isMe: boolean;
  onClose: () => void;
  onReply: () => void;
  onEdit: () => void;
  onDelete: (forEveryone: boolean) => void;
  onCopy: () => void;
  onForward: () => void;
  onScheduleReminder: (minutes: number) => void;
  onChangeTone: (tone: string) => void;
}

const TONE_OPTIONS = [
  { label: 'Formal', icon: 'briefcase', tone: 'formal' },
  { label: 'Casual', icon: 'cafe', tone: 'casual' },
  { label: 'Funny', icon: 'happy', tone: 'funny' },
  { label: 'Professional', icon: 'business', tone: 'professional' },
  { label: 'Friendly', icon: 'heart', tone: 'friendly' },
];

const REMINDER_OPTIONS = [
  { label: '1 Hour', minutes: 60 },
  { label: '3 Hours', minutes: 180 },
  { label: 'Tomorrow', minutes: 1440 },
  { label: 'Next Week', minutes: 10080 },
];

export const MessageActionsSheet: React.FC<MessageActionsSheetProps> = ({
  visible,
  message,
  isMe,
  onClose,
  onReply,
  onEdit,
  onDelete,
  onCopy,
  onForward,
  onScheduleReminder,
  onChangeTone,
}) => {
  const [showToneOptions, setShowToneOptions] = useState(false);
  const [showReminderOptions, setShowReminderOptions] = useState(false);
  const [showDeleteOptions, setShowDeleteOptions] = useState(false);

  const handleToneChange = (tone: string) => {
    onChangeTone(tone);
    setShowToneOptions(false);
    onClose();
  };

  const handleReminder = (minutes: number) => {
    onScheduleReminder(minutes);
    setShowReminderOptions(false);
    onClose();
  };

  const handleDeleteOption = (forEveryone: boolean) => {
    onDelete(forEveryone);
    setShowDeleteOptions(false);
    onClose();
  };

  if (!message) return null;

  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onClose}
    >
      <TouchableOpacity
        style={styles.overlay}
        activeOpacity={1}
        onPress={onClose}
      >
        <View style={styles.container}>
          {/* Header */}
          <View style={styles.header}>
            <Text style={styles.headerTitle}>Message Actions</Text>
            <TouchableOpacity onPress={onClose}>
              <Ionicons name="close" size={24} color={colors.text} />
            </TouchableOpacity>
          </View>

          <ScrollView style={styles.content}>
            {/* Quick Actions */}
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>Quick Actions</Text>
              
              <TouchableOpacity style={styles.action} onPress={() => { onReply(); onClose(); }}>
                <View style={[styles.actionIcon, { backgroundColor: colors.primary + '20' }]}>
                  <Ionicons name="arrow-undo" size={20} color={colors.primary} />
                </View>
                <View style={styles.actionContent}>
                  <Text style={styles.actionTitle}>Reply</Text>
                  <Text style={styles.actionSubtitle}>Reply to this message</Text>
                </View>
              </TouchableOpacity>

              {isMe && (
                <TouchableOpacity style={styles.action} onPress={() => { onEdit(); onClose(); }}>
                  <View style={[styles.actionIcon, { backgroundColor: colors.secondary + '20' }]}>
                    <Ionicons name="create-outline" size={20} color={colors.secondary} />
                  </View>
                  <View style={styles.actionContent}>
                    <Text style={styles.actionTitle}>Edit</Text>
                    <Text style={styles.actionSubtitle}>Edit message content</Text>
                  </View>
                </TouchableOpacity>
              )}

              <TouchableOpacity style={styles.action} onPress={() => { onCopy(); onClose(); }}>
                <View style={[styles.actionIcon, { backgroundColor: colors.info + '20' }]}>
                  <Ionicons name="copy-outline" size={20} color={colors.info} />
                </View>
                <View style={styles.actionContent}>
                  <Text style={styles.actionTitle}>Copy</Text>
                  <Text style={styles.actionSubtitle}>Copy to clipboard</Text>
                </View>
              </TouchableOpacity>

              <TouchableOpacity style={styles.action} onPress={() => { onForward(); onClose(); }}>
                <View style={[styles.actionIcon, { backgroundColor: colors.warning + '20' }]}>
                  <Ionicons name="arrow-forward" size={20} color={colors.warning} />
                </View>
                <View style={styles.actionContent}>
                  <Text style={styles.actionTitle}>Forward</Text>
                  <Text style={styles.actionSubtitle}>Share with others</Text>
                </View>
              </TouchableOpacity>
            </View>

            {/* Special Actions */}
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>🎨 Special Features</Text>

              {isMe && !showToneOptions && (
                <TouchableOpacity 
                  style={styles.action}
                  onPress={() => setShowToneOptions(true)}
                >
                  <View style={[styles.actionIcon, { backgroundColor: '#FF6B9D20' }]}>
                    <Ionicons name="sparkles" size={20} color="#FF6B9D" />
                  </View>
                  <View style={styles.actionContent}>
                    <Text style={styles.actionTitle}>Change Tone</Text>
                    <Text style={styles.actionSubtitle}>Rewrite in different style</Text>
                  </View>
                  <Ionicons name="chevron-forward" size={20} color={colors.textSecondary} />
                </TouchableOpacity>
              )}

              {showToneOptions && (
                <View style={styles.subOptions}>
                  {TONE_OPTIONS.map((option) => (
                    <TouchableOpacity
                      key={option.tone}
                      style={styles.subOption}
                      onPress={() => handleToneChange(option.tone)}
                    >
                      <Ionicons name={option.icon as any} size={18} color={colors.primary} />
                      <Text style={styles.subOptionText}>{option.label}</Text>
                    </TouchableOpacity>
                  ))}
                  <TouchableOpacity
                    style={styles.subOptionCancel}
                    onPress={() => setShowToneOptions(false)}
                  >
                    <Text style={styles.subOptionCancelText}>Cancel</Text>
                  </TouchableOpacity>
                </View>
              )}

              {!showReminderOptions && (
                <TouchableOpacity 
                  style={styles.action}
                  onPress={() => setShowReminderOptions(true)}
                >
                  <View style={[styles.actionIcon, { backgroundColor: '#FFA50020' }]}>
                    <Ionicons name="alarm" size={20} color="#FFA500" />
                  </View>
                  <View style={styles.actionContent}>
                    <Text style={styles.actionTitle}>Schedule Reminder</Text>
                    <Text style={styles.actionSubtitle}>Get notified later</Text>
                  </View>
                  <Ionicons name="chevron-forward" size={20} color={colors.textSecondary} />
                </TouchableOpacity>
              )}

              {showReminderOptions && (
                <View style={styles.subOptions}>
                  {REMINDER_OPTIONS.map((option) => (
                    <TouchableOpacity
                      key={option.label}
                      style={styles.subOption}
                      onPress={() => handleReminder(option.minutes)}
                    >
                      <Ionicons name="time" size={18} color={colors.primary} />
                      <Text style={styles.subOptionText}>{option.label}</Text>
                    </TouchableOpacity>
                  ))}
                  <TouchableOpacity
                    style={styles.subOptionCancel}
                    onPress={() => setShowReminderOptions(false)}
                  >
                    <Text style={styles.subOptionCancelText}>Cancel</Text>
                  </TouchableOpacity>
                </View>
              )}

              <TouchableOpacity style={styles.action}>
                <View style={[styles.actionIcon, { backgroundColor: '#9B59B620' }]}>
                  <Ionicons name="bookmark" size={20} color="#9B59B6" />
                </View>
                <View style={styles.actionContent}>
                  <Text style={styles.actionTitle}>Bookmark</Text>
                  <Text style={styles.actionSubtitle}>Save for later</Text>
                </View>
              </TouchableOpacity>

              <TouchableOpacity style={styles.action}>
                <View style={[styles.actionIcon, { backgroundColor: '#3498DB20' }]}>
                  <Ionicons name="share-social" size={20} color="#3498DB" />
                </View>
                <View style={styles.actionContent}>
                  <Text style={styles.actionTitle}>Share Link</Text>
                  <Text style={styles.actionSubtitle}>Generate shareable link</Text>
                </View>
              </TouchableOpacity>

              <TouchableOpacity style={styles.action}>
                <View style={[styles.actionIcon, { backgroundColor: '#1ABC9C20' }]}>
                  <Ionicons name="language" size={20} color="#1ABC9C" />
                </View>
                <View style={styles.actionContent}>
                  <Text style={styles.actionTitle}>Translate</Text>
                  <Text style={styles.actionSubtitle}>Auto-translate message</Text>
                </View>
              </TouchableOpacity>
            </View>

            {/* Delete Section */}
            {isMe && (
              <View style={styles.section}>
                {!showDeleteOptions && (
                  <TouchableOpacity 
                    style={[styles.action, styles.actionDanger]}
                    onPress={() => setShowDeleteOptions(true)}
                  >
                    <View style={[styles.actionIcon, { backgroundColor: colors.error + '20' }]}>
                      <Ionicons name="trash-outline" size={20} color={colors.error} />
                    </View>
                    <View style={styles.actionContent}>
                      <Text style={[styles.actionTitle, styles.textDanger]}>Delete</Text>
                      <Text style={styles.actionSubtitle}>Remove this message</Text>
                    </View>
                    <Ionicons name="chevron-forward" size={20} color={colors.error} />
                  </TouchableOpacity>
                )}

                {showDeleteOptions && (
                  <View style={styles.deleteOptions}>
                    <Text style={styles.deleteWarning}>Choose delete option:</Text>
                    <TouchableOpacity
                      style={styles.deleteOption}
                      onPress={() => handleDeleteOption(false)}
                    >
                      <Ionicons name="eye-off" size={20} color={colors.textSecondary} />
                      <View style={styles.deleteOptionContent}>
                        <Text style={styles.deleteOptionTitle}>Delete for Me</Text>
                        <Text style={styles.deleteOptionSubtitle}>Only removes from your view</Text>
                      </View>
                    </TouchableOpacity>
                    <TouchableOpacity
                      style={styles.deleteOption}
                      onPress={() => handleDeleteOption(true)}
                    >
                      <Ionicons name="trash" size={20} color={colors.error} />
                      <View style={styles.deleteOptionContent}>
                        <Text style={[styles.deleteOptionTitle, styles.textDanger]}>Delete for Everyone</Text>
                        <Text style={styles.deleteOptionSubtitle}>Removes for all participants</Text>
                      </View>
                    </TouchableOpacity>
                    <TouchableOpacity
                      style={styles.subOptionCancel}
                      onPress={() => setShowDeleteOptions(false)}
                    >
                      <Text style={styles.subOptionCancelText}>Cancel</Text>
                    </TouchableOpacity>
                  </View>
                )}
              </View>
            )}
          </ScrollView>
        </View>
      </TouchableOpacity>
    </Modal>
  );
};

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'flex-end',
  },
  container: {
    backgroundColor: colors.background,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    maxHeight: '85%',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: colors.text,
  },
  content: {
    padding: 20,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: colors.textSecondary,
    marginBottom: 12,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  action: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 4,
    marginBottom: 8,
  },
  actionIcon: {
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
  },
  actionContent: {
    flex: 1,
    marginLeft: 16,
  },
  actionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 2,
  },
  actionSubtitle: {
    fontSize: 13,
    color: colors.textSecondary,
  },
  actionDanger: {
    marginTop: 8,
  },
  textDanger: {
    color: colors.error,
  },
  subOptions: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: 12,
    marginTop: 8,
    marginBottom: 12,
  },
  subOption: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 8,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  subOptionText: {
    fontSize: 15,
    color: colors.text,
    marginLeft: 12,
  },
  subOptionCancel: {
    paddingVertical: 12,
    alignItems: 'center',
    marginTop: 8,
  },
  subOptionCancelText: {
    fontSize: 15,
    fontWeight: '600',
    color: colors.textSecondary,
  },
  deleteOptions: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: 16,
    marginTop: 8,
  },
  deleteWarning: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 12,
  },
  deleteOption: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 8,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  deleteOptionContent: {
    flex: 1,
    marginLeft: 12,
  },
  deleteOptionTitle: {
    fontSize: 15,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 2,
  },
  deleteOptionSubtitle: {
    fontSize: 12,
    color: colors.textSecondary,
  },
});
