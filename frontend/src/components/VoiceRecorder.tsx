import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  Animated,
  StyleSheet,
  Vibration,
  TouchableOpacity,
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
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackPosition, setPlaybackPosition] = useState(0);
  const [showPreview, setShowPreview] = useState(false);
  const scaleAnim = useRef(new Animated.Value(1)).current;
  const durationInterval = useRef<NodeJS.Timeout | null>(null);
  const recordingUri = useRef<string>('');
  const isMounted = useRef(true);
  const soundRef = useRef<Audio.Sound | null>(null);
  const playbackInterval = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    isMounted.current = true;
    startRecording();
    
    return () => {
      isMounted.current = false;
      cleanup();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    // Auto-stop at max duration
    if (duration >= MAX_DURATION && recording) {
      handleStopRecording();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [duration, recording]);

  const cleanup = async () => {
    if (durationInterval.current) {
      clearInterval(durationInterval.current);
      durationInterval.current = null;
    }
    
    if (playbackInterval.current) {
      clearInterval(playbackInterval.current);
      playbackInterval.current = null;
    }
    
    if (recording) {
      try {
        await recording.stopAndUnloadAsync();
      } catch (error) {
        console.log('Error cleaning up recording:', error);
      }
    }
    
    if (soundRef.current) {
      try {
        await soundRef.current.unloadAsync();
      } catch (error) {
        console.log('Error cleaning up sound:', error);
      }
      soundRef.current = null;
    }
  };

  const startRecording = async () => {
    try {
      // Check permission
      const permission = await Audio.requestPermissionsAsync();
      if (permission.status !== 'granted') {
        alert('Permission to access microphone is required!');
        onCancel();
        return;
      }

      // Set audio mode
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
        staysActiveInBackground: false,
      });

      // Create recording
      const { recording: newRecording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      
      if (!isMounted.current) {
        await newRecording.stopAndUnloadAsync();
        return;
      }
      
      setRecording(newRecording);
      Vibration.vibrate(50);

      // Start duration counter
      durationInterval.current = setInterval(() => {
        if (isMounted.current) {
          setDuration((prev) => prev + 0.1);
        }
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
        durationInterval.current = null;
      }

      await recording.stopAndUnloadAsync();
      const uri = recording.getURI();
      
      console.log('🎤 Recording stopped, URI:', uri);
      
      if (uri && !cancel) {
        recordingUri.current = uri;
        // Show preview instead of immediately sending
        setShowPreview(true);
      }
      
      setRecording(null);
    } catch (error) {
      console.error('Failed to stop recording', error);
    }
  };

  const handleStopRecording = async () => {
    await stopRecording(false);
    Vibration.vibrate(50);
  };

  const handleSend = async () => {
    // Clean up sound if playing
    if (soundRef.current) {
      await soundRef.current.unloadAsync();
      soundRef.current = null;
    }
    
    Vibration.vibrate(50);
    
    console.log('📨 Sending voice message:', {
      uri: recordingUri.current,
      duration: duration,
      isLongEnough: duration >= 0.5,
    });
    
    if (recordingUri.current && duration >= 0.5) {
      onSend(recordingUri.current, Math.round(duration * 10) / 10);
    } else {
      console.log('❌ Voice message too short or no URI');
      onCancel();
    }
  };

  const handleCancel = async () => {
    if (recording) {
      await stopRecording(true);
    }
    Vibration.vibrate([0, 50, 50, 50]);
    onCancel();
  };

  const handlePlayPause = async () => {
    if (!recordingUri.current) return;

    try {
      if (isPlaying) {
        // Pause
        if (soundRef.current) {
          await soundRef.current.pauseAsync();
        }
        if (playbackInterval.current) {
          clearInterval(playbackInterval.current);
          playbackInterval.current = null;
        }
        setIsPlaying(false);
      } else {
        // Play
        if (!soundRef.current) {
          const { sound } = await Audio.Sound.createAsync(
            { uri: recordingUri.current },
            { shouldPlay: true },
            (status) => {
              if (status.isLoaded && status.didJustFinish) {
                setIsPlaying(false);
                setPlaybackPosition(0);
                if (playbackInterval.current) {
                  clearInterval(playbackInterval.current);
                  playbackInterval.current = null;
                }
              }
            }
          );
          soundRef.current = sound;
        } else {
          await soundRef.current.playAsync();
        }

        setIsPlaying(true);

        // Update playback position
        playbackInterval.current = setInterval(async () => {
          if (soundRef.current) {
            const status = await soundRef.current.getStatusAsync();
            if (status.isLoaded) {
              setPlaybackPosition(status.positionMillis / 1000);
            }
          }
        }, 100);
      }
    } catch (error) {
      console.error('Playback error:', error);
      setIsPlaying(false);
    }
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const decimal = Math.floor((seconds % 1) * 10);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')},${decimal}`;
  };

  if (showPreview) {
    // Preview mode - show playback controls
    return (
      <View style={styles.container}>
        <View style={styles.previewContent}>
          {/* Cancel Button */}
          <TouchableOpacity
            style={styles.cancelButton}
            onPress={handleCancel}
          >
            <Ionicons name="close" size={24} color={colors.error} />
            <Text style={styles.cancelText}>Cancel</Text>
          </TouchableOpacity>

          {/* Preview info with play button */}
          <View style={styles.previewInfo}>
            <TouchableOpacity
              style={styles.playButton}
              onPress={handlePlayPause}
            >
              <Ionicons 
                name={isPlaying ? "pause" : "play"} 
                size={24} 
                color={colors.textLight} 
              />
            </TouchableOpacity>
            <View style={styles.previewTimeContainer}>
              <Text style={styles.previewLabel}>Voice Message</Text>
              <Text style={styles.previewTime}>
                {formatDuration(isPlaying ? playbackPosition : duration)}
              </Text>
            </View>
          </View>

          {/* Send Button */}
          <TouchableOpacity
            style={styles.sendButton}
            onPress={handleSend}
          >
            <Ionicons name="send" size={20} color={colors.textLight} />
            <Text style={styles.sendText}>Send</Text>
          </TouchableOpacity>
        </View>

        {/* Progress bar for playback */}
        {isPlaying && (
          <View style={styles.progressContainer}>
            <View 
              style={[
                styles.progressBar, 
                { width: `${(playbackPosition / duration) * 100}%` }
              ]} 
            />
          </View>
        )}
      </View>
    );
  }

  // Recording mode
  return (
    <View style={styles.container}>
      <View style={styles.content}>
        {/* Cancel Button */}
        <TouchableOpacity
          style={styles.cancelButton}
          onPress={handleCancel}
        >
          <Ionicons name="close" size={24} color={colors.error} />
          <Text style={styles.cancelText}>Cancel</Text>
        </TouchableOpacity>

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

        {/* Stop Button */}
        <TouchableOpacity
          style={styles.stopButton}
          onPress={handleStopRecording}
        >
          <Ionicons name="stop" size={20} color={colors.textLight} />
          <Text style={styles.stopText}>Stop</Text>
        </TouchableOpacity>
      </View>

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
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  cancelButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingVertical: 8,
    paddingHorizontal: 12,
    backgroundColor: colors.background,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.error,
  },
  cancelText: {
    fontSize: 14,
    color: colors.error,
    fontWeight: '600',
  },
  recordingInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  recordingDot: {
    width: 16,
    height: 16,
    borderRadius: 8,
    backgroundColor: colors.error,
  },
  durationText: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
    fontVariant: ['tabular-nums'],
  },
  sendButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingVertical: 8,
    paddingHorizontal: 16,
    backgroundColor: colors.primary,
    borderRadius: 20,
  },
  sendText: {
    color: colors.textLight,
    fontSize: 14,
    fontWeight: '600',
  },
  stopButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingVertical: 8,
    paddingHorizontal: 16,
    backgroundColor: colors.error,
    borderRadius: 20,
  },
  stopText: {
    color: colors.textLight,
    fontSize: 14,
    fontWeight: '600',
  },
  previewContent: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  previewInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  playButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.primary,
    justifyContent: 'center',
    alignItems: 'center',
  },
  previewTimeContainer: {
    flexDirection: 'column',
    gap: 2,
  },
  previewLabel: {
    fontSize: 12,
    color: colors.textSecondary,
    fontWeight: '500',
  },
  previewTime: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
    fontVariant: ['tabular-nums'],
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
