import React from 'react';
import { View, Text, Image, StyleSheet } from 'react-native';
import { colors } from '../theme/colors';

interface AvatarProps {
  uri?: string;
  name: string;
  size?: number;
  online?: boolean;
}

export const Avatar: React.FC<AvatarProps> = ({ uri, name, size = 48, online }) => {
  const initials = name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);

  const backgroundColor = getColorFromName(name);

  return (
    <View style={[styles.container, { width: size, height: size }]}>
      {uri ? (
        <Image
          source={{ uri }}
          style={[styles.image, { width: size, height: size, borderRadius: size / 2 }]}
        />
      ) : (
        <View
          style={[
            styles.placeholder,
            {
              width: size,
              height: size,
              borderRadius: size / 2,
              backgroundColor,
            },
          ]}
        >
          <Text style={[styles.initials, { fontSize: size * 0.4 }]}>{initials}</Text>
        </View>
      )}
      {online && (
        <View
          style={[
            styles.onlineIndicator,
            {
              width: size * 0.25,
              height: size * 0.25,
              borderRadius: size * 0.125,
              borderWidth: size * 0.05,
            },
          ]}
        />
      )}
    </View>
  );
};

const getColorFromName = (name: string): string => {
  const avatarColors = [
    '#FF6B6B',
    '#4ECDC4',
    '#45B7D1',
    '#96CEB4',
    '#FFEAA7',
    '#DFE6E9',
    '#6C5CE7',
    '#A29BFE',
    '#FD79A8',
    '#FDCB6E',
  ];

  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return avatarColors[Math.abs(hash) % avatarColors.length];
};

const styles = StyleSheet.create({
  container: {
    position: 'relative',
  },
  image: {
    resizeMode: 'cover',
  },
  placeholder: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  initials: {
    color: colors.textLight,
    fontWeight: '600',
  },
  onlineIndicator: {
    position: 'absolute',
    bottom: 0,
    right: 0,
    backgroundColor: colors.online,
    borderColor: colors.background,
  },
});
