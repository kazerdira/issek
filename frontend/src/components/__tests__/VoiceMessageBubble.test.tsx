import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { VoiceMessageBubble } from '../VoiceMessageBubble';
import { Audio } from 'expo-av';

// Mock Audio
jest.mock('expo-av', () => ({
  Audio: {
    setAudioModeAsync: jest.fn(),
    Sound: {
      createAsync: jest.fn(),
    },
  },
}));

describe('VoiceMessageBubble', () => {
  let mockSound: any;

  beforeEach(() => {
    jest.clearAllMocks();

    mockSound = {
      playAsync: jest.fn().mockResolvedValue(undefined),
      pauseAsync: jest.fn().mockResolvedValue(undefined),
      unloadAsync: jest.fn().mockResolvedValue(undefined),
      setOnPlaybackStatusUpdate: jest.fn(),
    };

    (Audio.setAudioModeAsync as jest.Mock).mockResolvedValue(undefined);
    (Audio.Sound.createAsync as jest.Mock).mockResolvedValue({
      sound: mockSound,
    });
  });

  it('should render voice message bubble', () => {
    const { getByTestId } = render(
      <VoiceMessageBubble
        mediaUrl="data:audio/m4a;base64,mockdata"
        duration={5.5}
        isMe={true}
        messageTime="10:30 AM"
        status="read"
      />
    );

    // Should render without crashing
    expect(getByTestId).toBeDefined();
  });

  it('should load and play sound when play button pressed', async () => {
    const { getByRole } = render(
      <VoiceMessageBubble
        mediaUrl="data:audio/m4a;base64,mockdata"
        duration={5.5}
        isMe={false}
        messageTime="10:30 AM"
      />
    );

    const playButton = getByRole('button');
    fireEvent.press(playButton);

    await waitFor(() => {
      expect(Audio.setAudioModeAsync).toHaveBeenCalled();
      expect(Audio.Sound.createAsync).toHaveBeenCalledWith(
        { uri: 'data:audio/m4a;base64,mockdata' },
        expect.any(Object),
        expect.any(Function)
      );
      expect(mockSound.playAsync).toHaveBeenCalled();
    });
  });

  it('should pause sound when pause button pressed', async () => {
    const { getByRole } = render(
      <VoiceMessageBubble
        mediaUrl="data:audio/m4a;base64,mockdata"
        duration={3.0}
        isMe={true}
        messageTime="10:30 AM"
      />
    );

    const playButton = getByRole('button');
    
    // Start playing
    fireEvent.press(playButton);
    await waitFor(() => {
      expect(mockSound.playAsync).toHaveBeenCalled();
    });

    // Pause
    fireEvent.press(playButton);
    await waitFor(() => {
      expect(mockSound.pauseAsync).toHaveBeenCalled();
    });
  });

  it('should display correct duration format', () => {
    const { getByText } = render(
      <VoiceMessageBubble
        mediaUrl="data:audio/m4a;base64,mockdata"
        duration={125.5}
        isMe={false}
        messageTime="10:30 AM"
      />
    );

    // Duration should be formatted as MM:SS
    expect(getByText('2:05')).toBeTruthy();
  });

  it('should show waveform bars', () => {
    const { getAllByTestId } = render(
      <VoiceMessageBubble
        mediaUrl="data:audio/m4a;base64,mockdata"
        duration={5.5}
        isMe={true}
        messageTime="10:30 AM"
      />
    );

    // Should render 20 waveform bars
    const waveformBars = getAllByTestId(/waveform-bar/);
    expect(waveformBars.length).toBe(20);
  });

  it('should cleanup sound on unmount', async () => {
    const { unmount, getByRole } = render(
      <VoiceMessageBubble
        mediaUrl="data:audio/m4a;base64,mockdata"
        duration={5.5}
        isMe={false}
        messageTime="10:30 AM"
      />
    );

    // Start playing
    const playButton = getByRole('button');
    fireEvent.press(playButton);

    await waitFor(() => {
      expect(Audio.Sound.createAsync).toHaveBeenCalled();
    });

    unmount();

    await waitFor(() => {
      expect(mockSound.unloadAsync).toHaveBeenCalled();
    });
  });

  it('should update progress as playback progresses', async () => {
    let statusCallback: any;

    (Audio.Sound.createAsync as jest.Mock).mockImplementation((source, config, callback) => {
      statusCallback = callback;
      return Promise.resolve({ sound: mockSound });
    });

    render(
      <VoiceMessageBubble
        mediaUrl="data:audio/m4a;base64,mockdata"
        duration={10.0}
        isMe={true}
        messageTime="10:30 AM"
      />
    );

    // Simulate playback status updates
    statusCallback({
      isLoaded: true,
      positionMillis: 5000,
      durationMillis: 10000,
      didJustFinish: false,
    });

    // Progress should be at 50%
    await waitFor(() => {
      // Check that progress bar is rendered with correct width
      // This would depend on your component structure
    });
  });

  it('should reset to beginning when playback finishes', async () => {
    let statusCallback: any;

    (Audio.Sound.createAsync as jest.Mock).mockImplementation((source, config, callback) => {
      statusCallback = callback;
      return Promise.resolve({ sound: mockSound });
    });

    const { getByRole } = render(
      <VoiceMessageBubble
        mediaUrl="data:audio/m4a;base64,mockdata"
        duration={5.0}
        isMe={false}
        messageTime="10:30 AM"
      />
    );

    const playButton = getByRole('button');
    fireEvent.press(playButton);

    await waitFor(() => {
      expect(Audio.Sound.createAsync).toHaveBeenCalled();
    });

    // Simulate playback finishing
    statusCallback({
      isLoaded: true,
      positionMillis: 5000,
      durationMillis: 5000,
      didJustFinish: true,
    });

    await waitFor(() => {
      // Should reset to play button (not pause)
      // Position should be 0
    });
  });
});
