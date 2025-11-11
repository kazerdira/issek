import { uploadVoiceMessage } from '../voiceService';
import * as FileSystem from 'expo-file-system';
import { api } from '../api';

// Mock dependencies
jest.mock('expo-file-system');
jest.mock('../api');

describe('Voice Service', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Set a mock auth token
    api.defaults.headers.common['Authorization'] = 'Bearer test-token';
    api.defaults.baseURL = 'http://192.168.1.44:8000/api';
  });

  it('should upload voice message successfully', async () => {
    const mockFileUri = 'file:///path/to/voice.m4a';
    const mockChatId = 'test-chat-id';

    // Mock FileSystem.getInfoAsync
    (FileSystem.getInfoAsync as jest.Mock).mockResolvedValue({
      exists: true,
      size: 50000,
      uri: mockFileUri,
    });

    // Mock FileSystem.uploadAsync
    (FileSystem.uploadAsync as jest.Mock).mockResolvedValue({
      status: 200,
      body: JSON.stringify({
        media_url: 'data:audio/m4a;base64,mockbase64data',
        file_size: 50000,
        content_type: 'audio/m4a',
      }),
    });

    const result = await uploadVoiceMessage(mockFileUri, mockChatId);

    expect(result).toEqual({
      mediaUrl: 'data:audio/m4a;base64,mockbase64data',
      fileSize: 50000,
      contentType: 'audio/m4a',
    });

    expect(FileSystem.uploadAsync).toHaveBeenCalledWith(
      'http://192.168.1.44:8000/api/media/upload-voice',
      mockFileUri,
      expect.objectContaining({
        fieldName: 'file',
        httpMethod: 'POST',
        parameters: { chat_id: mockChatId },
      })
    );
  });

  it('should throw error if file does not exist', async () => {
    const mockFileUri = 'file:///path/to/nonexistent.m4a';
    const mockChatId = 'test-chat-id';

    (FileSystem.getInfoAsync as jest.Mock).mockResolvedValue({
      exists: false,
    });

    await expect(uploadVoiceMessage(mockFileUri, mockChatId)).rejects.toThrow(
      'File does not exist'
    );
  });

  it('should throw error if no auth token', async () => {
    const mockFileUri = 'file:///path/to/voice.m4a';
    const mockChatId = 'test-chat-id';

    // Remove auth token
    delete api.defaults.headers.common['Authorization'];

    await expect(uploadVoiceMessage(mockFileUri, mockChatId)).rejects.toThrow(
      'No auth token found'
    );
  });

  it('should handle upload failure', async () => {
    const mockFileUri = 'file:///path/to/voice.m4a';
    const mockChatId = 'test-chat-id';

    (FileSystem.getInfoAsync as jest.Mock).mockResolvedValue({
      exists: true,
      size: 50000,
    });

    (FileSystem.uploadAsync as jest.Mock).mockResolvedValue({
      status: 400,
      body: JSON.stringify({
        detail: 'File too large',
      }),
    });

    await expect(uploadVoiceMessage(mockFileUri, mockChatId)).rejects.toThrow(
      'File too large'
    );
  });
});
