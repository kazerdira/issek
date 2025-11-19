import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { Audio } from 'expo-av';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../theme/colors';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withTiming,
  withSequence,
  Easing,
} from 'react-native-reanimated';

interface VoiceMessageBubbleProps {
  mediaUrl: string;
  duration: number;
  isMe: boolean;
  messageTime: string;
  status?: 'sent' | 'delivered' | 'read';
}

export const VoiceMessageBubble: React.FC<VoiceMessageBubbleProps> = ({
  mediaUrl,
  duration,
  isMe,
  messageTime,
  status,
}) => {
  const [sound, setSound] = useState<Audio.Sound | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [playbackPosition, setPlaybackPosition] = useState(0);
  const [playbackDuration, setPlaybackDuration] = useState(duration * 1000);
  const animationValue = useSharedValue(0);

  useEffect(() => {
    return () => {
      if (sound) {
        sound.unloadAsync();
      }
    };
  }, [sound]);

  useEffect(() => {
    if (isPlaying) {
      animationValue.value = withRepeat(
        withTiming(1, { duration: 1000, easing: Easing.linear }),
        -1,
        false
      );
    } else {
      animationValue.value = 0;
    }
  }, [isPlaying]);

  const loadAndPlaySound = async () => {
    try {
      setIsLoading(true);

      // Unload previous sound if exists
      if (sound) {
        await sound.unloadAsync();
      }

      await Audio.setAudioModeAsync({
        allowsRecordingIOS: false,
        playsInSilentModeIOS: true,
        shouldDuckAndroid: true,
        playThroughEarpieceAndroid: false,
      });

      const { sound: newSound } = await Audio.Sound.createAsync(
        { uri: mediaUrl },
        { shouldPlay: true, progressUpdateIntervalMillis: 100 },
        onPlaybackStatusUpdate
      );

      setSound(newSound);
      setIsPlaying(true);
    } catch (error) {
      console.error('Error loading sound:', error);
      alert('Failed to play voice message');
    } finally {
      setIsLoading(false);
    }
  };

  const onPlaybackStatusUpdate = (status: any) => {
    if (status.isLoaded) {
      setPlaybackPosition(status.positionMillis);
      setPlaybackDuration(status.durationMillis || duration * 1000);

      if (status.didJustFinish) {
        setIsPlaying(false);
        setPlaybackPosition(0);
      }
    }
  };

  const handlePlayPause = async () => {
    if (isLoading) return;

    if (!sound) {
      await loadAndPlaySound();
    } else {
      if (isPlaying) {
        await sound.pauseAsync();
        setIsPlaying(false);
      } else {
        await sound.playAsync();
        setIsPlaying(true);
      }
    }
  };

  const formatTime = (millis: number) => {
    const totalSeconds = Math.floor(millis / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const progress = playbackDuration > 0 ? playbackPosition / playbackDuration : 0;

  // Animated waveform bars
  const WaveformBar = ({ index }: { index: number }) => {
    const animatedStyle = useAnimatedStyle(() => {
      const delay = index * 0.1;
      const scale = withSequence(
        withTiming(0.3, { duration: 300 }),
        withRepeat(
          withTiming(1, { duration: 600, easing: Easing.inOut(Easing.ease) }),
          -1,
          true
        )
      );

      return {
        transform: [
          {
            scaleY: isPlaying
              ? scale
              : 0.3 + Math.random() * 0.7,
          },
        ],
      };
    });

    return (
      <Animated.View
        style={[
          styles.waveformBar,
          {
            backgroundColor: isMe ? 'rgba(255,255,255,0.6)' : colors.primary,
          },
          animatedStyle,
        ]}
      />
    );
  };

  return (
    <View style={[styles.container, isMe ? styles.containerMe : styles.containerOther]}>
      {/* Play/Pause Button */}
      <TouchableOpacity
        style={[styles.playButton, isMe ? styles.playButtonMe : styles.playButtonOther]}
        onPress={handlePlayPause}
        disabled={isLoading}
      >
        {isLoading ? (
          <ActivityIndicator size="small" color={isMe ? colors.textLight : colors.primary} />
        ) : (
          <Ionicons
            name={isPlaying ? 'pause' : 'play'}
            size={24}
            color={isMe ? colors.textLight : colors.primary}
          />
        )}
      </TouchableOpacity>

      {/* Waveform and Progress */}
      <View style={styles.contentContainer}>
        <View style={styles.waveformContainer}>
          {/* Waveform bars */}
          <View style={styles.waveform}>
            {[...Array(20)].map((_, i) => (
              <WaveformBar key={i} index={i} />
            ))}
          </View>

          {/* Progress overlay */}
          <View
            style={[
              styles.progressOverlay,
              { width: `${progress * 100}%` },
              { backgroundColor: isMe ? 'rgba(255,255,255,0.3)' : 'rgba(108,92,231,0.2)' },
            ]}
          />
        </View>

        {/* Duration */}
        <View style={styles.footer}>
          <Text style={[styles.durationText, isMe ? styles.textMe : styles.textOther]}>
            {isPlaying ? formatTime(playbackPosition) : formatTime(duration * 1000)}
          </Text>
          
          {/* Message time and status */}
          <View style={styles.messageInfo}>
            <Text style={[styles.timeText, isMe ? styles.textMe : styles.textOther]}>
              {messageTime}
            </Text>
            {isMe && status && (
              <Ionicons
                name={status === 'read' ? 'checkmark-done' : 'checkmark'}
                size={14}
                color={status === 'read' ? colors.primary : 'rgba(255,255,255,0.7)'}
                style={{ marginLeft: 4 }}
              />
            )}
          </View>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 8,
    borderRadius: 16,
    minWidth: 200,
    maxWidth: 280,
  },
  containerMe: {
    backgroundColor: colors.messageSent,
  },
  containerOther: {
    backgroundColor: colors.messageReceived,
  },
  playButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 8,
  },
  playButtonMe: {
    backgroundColor: 'rgba(255,255,255,0.2)',
  },
  playButtonOther: {
    backgroundColor: 'rgba(108,92,231,0.1)',
  },
  contentContainer: {
    flex: 1,
  },
  waveformContainer: {
    position: 'relative',
    height: 32,
    justifyContent: 'center',
  },
  waveform: {
    flexDirection: 'row',
    alignItems: 'center',
    height: 32,
    gap: 2,
  },
  waveformBar: {
    width: 2,
    height: 32,
    borderRadius: 1,
  },
  progressOverlay: {
    position: 'absolute',
    left: 0,
    top: 0,
    bottom: 0,
    borderRadius: 4,
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 4,
  },
  durationText: {
    fontSize: 12,
    fontWeight: '600',
  },
  messageInfo: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  timeText: {
    fontSize: 11,
  },
  textMe: {
    color: 'rgba(255,255,255,0.9)',
  },
  textOther: {
    color: colors.textSecondary,
  },
});
