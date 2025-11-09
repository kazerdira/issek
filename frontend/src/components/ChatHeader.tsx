import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Avatar } from './Avatar';
import { colors } from '../theme/colors';

interface ChatHeaderProps {
  name: string;
  avatar?: string;
  isOnline?: boolean;
  lastSeen?: string;
  isGroup?: boolean;
  participantCount?: number;
  onBack?: () => void;
  onCall?: () => void;
  onVideoCall?: () => void;
  onInfo?: () => void;
}

export const ChatHeader: React.FC<ChatHeaderProps> = ({
  name,
  avatar,
  isOnline,
  lastSeen,
  isGroup,
  participantCount,
  onBack,
  onCall,
  onVideoCall,
  onInfo,
}) => {
  const getStatusText = () => {
    if (isGroup) {
      return `${participantCount || 0} participants`;
    }
    if (isOnline) {
      return 'Online';
    }
    if (lastSeen) {
      return `Last seen ${lastSeen}`;
    }
    return 'Offline';
  };

  return (
    <View style={styles.container}>
      {/* Left Section - Back button and User info */}
      <View style={styles.leftSection}>
        <TouchableOpacity
          style={styles.backButton}
          onPress={onBack}
          hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
        >
          <Ionicons name="arrow-back" size={24} color={colors.text} />
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.userInfo}
          onPress={onInfo}
          activeOpacity={0.7}
        >
          <Avatar
            uri={avatar}
            name={name}
            size={40}
            online={isOnline && !isGroup}
          />
          <View style={styles.textContainer}>
            <Text style={styles.name} numberOfLines={1}>
              {name}
            </Text>
            <Text
              style={[
                styles.status,
                isOnline && !isGroup && styles.statusOnline,
              ]}
              numberOfLines={1}
            >
              {getStatusText()}
            </Text>
          </View>
        </TouchableOpacity>
      </View>

      {/* Right Section - Action buttons */}
      <View style={styles.rightSection}>
        {!isGroup && onCall && (
          <TouchableOpacity
            style={styles.actionButton}
            onPress={onCall}
            hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
          >
            <Ionicons name="call-outline" size={22} color={colors.primary} />
          </TouchableOpacity>
        )}

        {!isGroup && onVideoCall && (
          <TouchableOpacity
            style={styles.actionButton}
            onPress={onVideoCall}
            hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
          >
            <Ionicons name="videocam-outline" size={24} color={colors.primary} />
          </TouchableOpacity>
        )}

        {onInfo && (
          <TouchableOpacity
            style={styles.actionButton}
            onPress={onInfo}
            hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
          >
            <Ionicons name="information-circle-outline" size={24} color={colors.primary} />
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
    justifyContent: 'space-between',
    backgroundColor: colors.background,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.05,
        shadowRadius: 3,
      },
      android: {
        elevation: 3,
      },
    }),
  },
  leftSection: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
  },
  backButton: {
    padding: 4,
    marginRight: 8,
  },
  userInfo: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
  },
  textContainer: {
    flex: 1,
    marginLeft: 12,
  },
  name: {
    fontSize: 17,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 2,
  },
  status: {
    fontSize: 13,
    color: colors.textSecondary,
  },
  statusOnline: {
    color: colors.online,
    fontWeight: '500',
  },
  rightSection: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  actionButton: {
    padding: 4,
  },
});
