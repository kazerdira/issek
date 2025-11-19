import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  Animated,
  StyleSheet,
  PanResponder,
  Vibration,
} from 'react-native';
import { Audio } from 'expo-av';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../theme/colors';

interface VoiceRecorderProps {
  onSend: (uri: string, duration: number) => void;
  onCancel: () => void;
}

const MAX_DURATION = 180; // 3 minutes in seconds

export const VoiceRecorder: React.FC<VoiceRecorderProps> = ({ onSend, onCancel }) => {
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const [duration, setDuration] = useState(0);
  const [isRecording, setIsRecording] = useState(false);
  const slideAnim = useRef(new Animated.Value(0)).current;
  const scaleAnim = useRef(new Animated.Value(1)).current;
  const durationInterval = useRef<NodeJS.Timeout | null>(null);
  const recordingUri = useRef<string>('');

  useEffect(() => {
    startRecording();
    return () => {
      stopRecording(true);
    };
  }, []);

  useEffect(() => {
    // Auto-stop at max duration
    if (duration >= MAX_DURATION) {
      handleSend();
    }
  }, [duration]);

  const startRecording = async () => {
    try {
      const permission = await Audio.requestPermissionsAsync();
      if (permission.status !== 'granted') {
        alert('Permission to access microphone is required!');
        onCancel();
        return;
      }

      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      const { recording: newRecording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      
      setRecording(newRecording);
      setIsRecording(true);
      Vibration.vibrate(50);

      // Start duration counter
      durationInterval.current = setInterval(() => {
        setDuration((prev) => prev + 0.1);
      }, 100);

      // Pulse animation
      Animated.loop(
        Animated.sequence([
          Animated.timing(scaleAnim, {
            toValue: 1.2,
            duration: 1000,
            useNativeDriver: true,
          }),
          Animated.timing(scaleAnim, {
            toValue: 1,
            duration: 1000,
            useNativeDriver: true,
          }),
        ])
      ).start();
    } catch (err) {
      console.error('Failed to start recording', err);
      onCancel();
    }
  };

  const stopRecording = async (cancel = false) => {
    if (!recording) return;

    try {
      if (durationInterval.current) {
        clearInterval(durationInterval.current);
      }

      await recording.stopAndUnloadAsync();
      const uri = recording.getURI();
      
      if (uri && !cancel) {
        recordingUri.current = uri;
      }
      
      setRecording(null);
      setIsRecording(false);
    } catch (error) {
      console.error('Failed to stop recording', error);
    }
  };

  const handleSend = async () => {
    await stopRecording(false);
    Vibration.vibrate(50);
    if (recordingUri.current && duration >= 0.5) {
      onSend(recordingUri.current, Math.round(duration * 10) / 10);
    } else {
      onCancel();
    }
  };

  const handleCancel = async () => {
    await stopRecording(true);
    Vibration.vibrate([0, 50, 50, 50]);
    onCancel();
  };

  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: () => true,
      onPanResponderMove: (_, gestureState) => {
        const { dx, dy } = gestureState;
        
        // Slide left to cancel
        if (dx < -80) {
          slideAnim.setValue(dx);
        } else if (dx < 0) {
          slideAnim.setValue(dx / 2);
        }
        
        // Slide up to lock (optional feature)
        if (dy < -80) {
          // Could implement lock feature here
        }
      },
      onPanResponderRelease: (_, gestureState) => {
        const { dx } = gestureState;
        
        if (dx < -100) {
          // Cancel
          handleCancel();
        } else {
          // Send
          Animated.spring(slideAnim, {
            toValue: 0,
            useNativeDriver: true,
          }).start();
          handleSend();
        }
      },
    })
  ).current;

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const decimal = Math.floor((seconds % 1) * 10);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')},${decimal}`;
  };

  return (
    <View style={styles.container}>
      <Animated.View
        style={[
          styles.content,
          {
            transform: [{ translateX: slideAnim }],
          },
        ]}
        {...panResponder.panHandlers}
      >
        {/* Cancel text - appears when sliding left */}
        <Animated.View
          style={[
            styles.cancelContainer,
            {
              opacity: slideAnim.interpolate({
                inputRange: [-100, -50, 0],
                outputRange: [1, 0.5, 0],
              }),
            },
          ]}
        >
          <Text style={styles.cancelText}>Cancel</Text>
        </Animated.View>

        {/* Recording indicator and timer */}
        <View style={styles.recordingInfo}>
          <Animated.View
            style={[
              styles.recordingDot,
              {
                transform: [{ scale: scaleAnim }],
              },
            ]}
          />
          <Text style={styles.durationText}>{formatDuration(duration)}</Text>
        </View>

        {/* Instruction text */}
        <Text style={styles.instructionText}>
          ← Slide to cancel
        </Text>

        {/* Microphone button */}
        <View style={styles.micContainer}>
          <View style={styles.micButton}>
            <Ionicons name="mic" size={28} color={colors.textLight} />
          </View>
        </View>
      </Animated.View>

      {/* Progress bar */}
      <View style={styles.progressContainer}>
        <View 
          style={[
            styles.progressBar, 
            { width: `${(duration / MAX_DURATION) * 100}%` }
          ]} 
        />
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: colors.surface,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    paddingBottom: 8,
  },
  content: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  cancelContainer: {
    position: 'absolute',
    left: 16,
  },
  cancelText: {
    fontSize: 16,
    color: colors.error,
    fontWeight: '600',
  },
  recordingInfo: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  recordingDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: colors.error,
    marginRight: 8,
  },
  durationText: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
  },
  instructionText: {
    position: 'absolute',
    bottom: -20,
    alignSelf: 'center',
    fontSize: 12,
    color: colors.textSecondary,
  },
  micContainer: {
    position: 'absolute',
    right: 16,
  },
  micButton: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.primary,
    justifyContent: 'center',
    alignItems: 'center',
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
  },
  progressContainer: {
    height: 3,
    backgroundColor: colors.border,
    marginTop: 8,
  },
  progressBar: {
    height: '100%',
    backgroundColor: colors.primary,
  },
});
