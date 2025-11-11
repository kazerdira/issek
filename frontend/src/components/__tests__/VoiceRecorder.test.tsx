import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { VoiceRecorder } from '../VoiceRecorder';
import { Audio } from 'expo-av';

// Mock Audio
jest.mock('expo-av', () => ({
  Audio: {
    requestPermissionsAsync: jest.fn(),
    setAudioModeAsync: jest.fn(),
    Recording: {
      createAsync: jest.fn(),
    },
  },
}));

// Mock Vibration
jest.mock('react-native/Libraries/Vibration/Vibration', () => ({
  vibrate: jest.fn(),
}));

describe('VoiceRecorder', () => {
  const mockOnSend = jest.fn();
  const mockOnCancel = jest.fn();
  
  let mockRecording: any;

  beforeEach(() => {
    jest.clearAllMocks();
    
    mockRecording = {
      stopAndUnloadAsync: jest.fn().mockResolvedValue(undefined),
      getURI: jest.fn().mockReturnValue('file:///path/to/recording.m4a'),
      getStatusAsync: jest.fn().mockResolvedValue({
        isRecording: true,
        durationMillis: 5000,
      }),
    };

    // Mock permissions
    (Audio.requestPermissionsAsync as jest.Mock).mockResolvedValue({
      status: 'granted',
      granted: true,
    });

    // Mock audio mode
    (Audio.setAudioModeAsync as jest.Mock).mockResolvedValue(undefined);

    // Mock recording creation
    (Audio.Recording.createAsync as jest.Mock).mockResolvedValue({
      recording: mockRecording,
    });
  });

  it('should start recording on mount', async () => {
    render(<VoiceRecorder onSend={mockOnSend} onCancel={mockOnCancel} />);

    await waitFor(() => {
      expect(Audio.requestPermissionsAsync).toHaveBeenCalled();
      expect(Audio.setAudioModeAsync).toHaveBeenCalled();
      expect(Audio.Recording.createAsync).toHaveBeenCalled();
    });
  });

  it('should stop recording and show preview when stop button clicked', async () => {
    const { getByText } = render(
      <VoiceRecorder onSend={mockOnSend} onCancel={mockOnCancel} />
    );

    // Wait for recording to start
    await waitFor(() => {
      expect(Audio.Recording.createAsync).toHaveBeenCalled();
    });

    // Find and click stop/preview button
    const stopButton = getByText('Stop');
    fireEvent.press(stopButton);

    await waitFor(() => {
      expect(mockRecording.stopAndUnloadAsync).toHaveBeenCalled();
      expect(mockRecording.getURI).toHaveBeenCalled();
    });
  });

  it('should call onSend with URI and duration when send button clicked', async () => {
    const { getByText } = render(
      <VoiceRecorder onSend={mockOnSend} onCancel={mockOnCancel} />
    );

    // Wait for recording to start
    await waitFor(() => {
      expect(Audio.Recording.createAsync).toHaveBeenCalled();
    });

    // Stop recording first
    const stopButton = getByText('Stop');
    fireEvent.press(stopButton);

    await waitFor(() => {
      expect(mockRecording.stopAndUnloadAsync).toHaveBeenCalled();
    });

    // Now in preview mode, click send
    const sendButton = getByText('Send');
    fireEvent.press(sendButton);

    await waitFor(() => {
      expect(mockOnSend).toHaveBeenCalledWith(
        'file:///path/to/recording.m4a',
        expect.any(Number)
      );
    });
  });

  it('should call onCancel when cancel button clicked', async () => {
    const { getByText } = render(
      <VoiceRecorder onSend={mockOnSend} onCancel={mockOnCancel} />
    );

    await waitFor(() => {
      expect(Audio.Recording.createAsync).toHaveBeenCalled();
    });

    const cancelButton = getByText('Cancel');
    fireEvent.press(cancelButton);

    await waitFor(() => {
      expect(mockOnCancel).toHaveBeenCalled();
    });
  });

  it('should handle permission denial gracefully', async () => {
    (Audio.requestPermissionsAsync as jest.Mock).mockResolvedValue({
      status: 'denied',
      granted: false,
    });

    render(<VoiceRecorder onSend={mockOnSend} onCancel={mockOnCancel} />);

    await waitFor(() => {
      expect(mockOnCancel).toHaveBeenCalled();
    });
  });

  it('should not send if recording is too short (< 0.5s)', async () => {
    mockRecording.getStatusAsync.mockResolvedValue({
      isRecording: true,
      durationMillis: 300, // 0.3 seconds
    });

    const { getByText } = render(
      <VoiceRecorder onSend={mockOnSend} onCancel={mockOnCancel} />
    );

    await waitFor(() => {
      expect(Audio.Recording.createAsync).toHaveBeenCalled();
    });

    const sendButton = getByText('Send');
    fireEvent.press(sendButton);

    await waitFor(() => {
      expect(mockOnSend).not.toHaveBeenCalled();
      expect(mockOnCancel).toHaveBeenCalled();
    });
  });

  it('should cleanup recording on unmount', async () => {
    const { unmount } = render(
      <VoiceRecorder onSend={mockOnSend} onCancel={mockOnCancel} />
    );

    await waitFor(() => {
      expect(Audio.Recording.createAsync).toHaveBeenCalled();
    });

    unmount();

    await waitFor(() => {
      expect(mockRecording.stopAndUnloadAsync).toHaveBeenCalled();
    });
  });
});
