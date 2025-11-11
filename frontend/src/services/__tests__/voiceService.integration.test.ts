import * as FileSystem from 'expo-file-system';
import { uploadVoiceMessage } from '../voiceService';
import { api } from '../api';

// Mock dependencies
jest.mock('expo-file-system');
jest.mock('../api');

describe('Voice Message Integration Tests', () => {
  const mockChatId = 'test-chat-123';
  const mockFileUri = 'file:///data/cache/recording-abc.m4a';
  const mockAuthToken = 'Bearer test-token-xyz';

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Setup API defaults
    api.defaults = {
      baseURL: 'http://192.168.1.44:8000/api',
      headers: {
        common: {
          'Authorization': mockAuthToken,
        },
      },
    } as any;
  });

  describe('File System Check', () => {
    it('should verify file exists before upload', async () => {
      (FileSystem.getInfoAsync as jest.Mock).mockResolvedValue({
        exists: true,
        size: 45000,
        uri: mockFileUri,
        isDirectory: false,
      });

      (FileSystem.uploadAsync as jest.Mock).mockResolvedValue({
        status: 200,
        body: JSON.stringify({
          media_url: 'data:audio/m4a;base64,mockdata',
          file_size: 45000,
          content_type: 'audio/m4a',
        }),
      });

      await uploadVoiceMessage(mockFileUri, mockChatId);

      expect(FileSystem.getInfoAsync).toHaveBeenCalledWith(mockFileUri);
    });

    it('should throw error if file does not exist', async () => {
      (FileSystem.getInfoAsync as jest.Mock).mockResolvedValue({
        exists: false,
      });

      await expect(
        uploadVoiceMessage(mockFileUri, mockChatId)
      ).rejects.toThrow('File does not exist');

      expect(FileSystem.uploadAsync).not.toHaveBeenCalled();
    });
  });

  describe('Upload Request', () => {
    beforeEach(() => {
      (FileSystem.getInfoAsync as jest.Mock).mockResolvedValue({
        exists: true,
        size: 50000,
        uri: mockFileUri,
      });
    });

    it('should send correct parameters to backend', async () => {
      (FileSystem.uploadAsync as jest.Mock).mockResolvedValue({
        status: 200,
        body: JSON.stringify({
          media_url: 'data:audio/m4a;base64,test',
          file_size: 50000,
          content_type: 'audio/m4a',
        }),
      });

      await uploadVoiceMessage(mockFileUri, mockChatId);

      expect(FileSystem.uploadAsync).toHaveBeenCalledWith(
        'http://192.168.1.44:8000/api/media/upload-voice',
        mockFileUri,
        {
          fieldName: 'file',
          httpMethod: 'POST',
          uploadType: 0,
          parameters: {
            chat_id: mockChatId,
          },
          headers: {
            'Authorization': mockAuthToken,
          },
        }
      );
    });

    it('should include auth token in request', async () => {
      (FileSystem.uploadAsync as jest.Mock).mockResolvedValue({
        status: 200,
        body: JSON.stringify({
          media_url: 'data:audio/m4a;base64,test',
          file_size: 50000,
          content_type: 'audio/m4a',
        }),
      });

      await uploadVoiceMessage(mockFileUri, mockChatId);

      const uploadCall = (FileSystem.uploadAsync as jest.Mock).mock.calls[0];
      expect(uploadCall[2].headers.Authorization).toBe(mockAuthToken);
    });

    it('should throw error if no auth token', async () => {
      delete api.defaults.headers.common['Authorization'];

      await expect(
        uploadVoiceMessage(mockFileUri, mockChatId)
      ).rejects.toThrow('No auth token found');

      expect(FileSystem.uploadAsync).not.toHaveBeenCalled();
    });
  });

  describe('Backend Response Handling', () => {
    beforeEach(() => {
      (FileSystem.getInfoAsync as jest.Mock).mockResolvedValue({
        exists: true,
        size: 50000,
      });
    });

    it('should handle successful upload (200)', async () => {
      const mockResponse = {
        media_url: 'data:audio/m4a;base64,successdata',
        file_size: 50000,
        content_type: 'audio/m4a',
      };

      (FileSystem.uploadAsync as jest.Mock).mockResolvedValue({
        status: 200,
        body: JSON.stringify(mockResponse),
      });

      const result = await uploadVoiceMessage(mockFileUri, mockChatId);

      expect(result).toEqual({
        mediaUrl: mockResponse.media_url,
        fileSize: mockResponse.file_size,
        contentType: mockResponse.content_type,
      });
    });

    it('should handle 400 error (file too large)', async () => {
      (FileSystem.uploadAsync as jest.Mock).mockResolvedValue({
        status: 400,
        body: JSON.stringify({
          detail: 'Voice message too large. Maximum size is 10MB',
        }),
      });

      await expect(
        uploadVoiceMessage(mockFileUri, mockChatId)
      ).rejects.toThrow('Voice message too large. Maximum size is 10MB');
    });

    it('should handle 403 error (not in chat)', async () => {
      (FileSystem.uploadAsync as jest.Mock).mockResolvedValue({
        status: 403,
        body: JSON.stringify({
          detail: 'Not a participant of this chat',
        }),
      });

      await expect(
        uploadVoiceMessage(mockFileUri, mockChatId)
      ).rejects.toThrow('Not a participant of this chat');
    });

    it('should handle 404 error (chat not found)', async () => {
      (FileSystem.uploadAsync as jest.Mock).mockResolvedValue({
        status: 404,
        body: JSON.stringify({
          detail: 'Chat not found',
        }),
      });

      await expect(
        uploadVoiceMessage(mockFileUri, mockChatId)
      ).rejects.toThrow('Chat not found');
    });

    it('should handle network error', async () => {
      (FileSystem.uploadAsync as jest.Mock).mockRejectedValue(
        new Error('Network request failed')
      );

      await expect(
        uploadVoiceMessage(mockFileUri, mockChatId)
      ).rejects.toThrow('Network request failed');
    });
  });

  describe('Real-time Message Display', () => {
    it('should return base64 media URL for immediate display', async () => {
      const base64Data = 'data:audio/m4a;base64,SGVsbG8gV29ybGQ=';
      
      (FileSystem.getInfoAsync as jest.Mock).mockResolvedValue({
        exists: true,
        size: 30000,
      });

      (FileSystem.uploadAsync as jest.Mock).mockResolvedValue({
        status: 200,
        body: JSON.stringify({
          media_url: base64Data,
          file_size: 30000,
          content_type: 'audio/m4a',
        }),
      });

      const result = await uploadVoiceMessage(mockFileUri, mockChatId);

      // Media URL should be base64 for immediate playback
      expect(result.mediaUrl).toContain('data:audio/m4a;base64,');
      expect(result.mediaUrl).toBe(base64Data);
    });
  });

  describe('File Size Validation', () => {
    it('should accept files under 10MB', async () => {
      const fileSize = 9 * 1024 * 1024; // 9MB
      
      (FileSystem.getInfoAsync as jest.Mock).mockResolvedValue({
        exists: true,
        size: fileSize,
      });

      (FileSystem.uploadAsync as jest.Mock).mockResolvedValue({
        status: 200,
        body: JSON.stringify({
          media_url: 'data:audio/m4a;base64,test',
          file_size: fileSize,
          content_type: 'audio/m4a',
        }),
      });

      const result = await uploadVoiceMessage(mockFileUri, mockChatId);

      expect(result.fileSize).toBe(fileSize);
    });

    it('should reject files over 10MB', async () => {
      const fileSize = 11 * 1024 * 1024; // 11MB
      
      (FileSystem.getInfoAsync as jest.Mock).mockResolvedValue({
        exists: true,
        size: fileSize,
      });

      (FileSystem.uploadAsync as jest.Mock).mockResolvedValue({
        status: 400,
        body: JSON.stringify({
          detail: 'Voice message too large. Maximum size is 10MB',
        }),
      });

      await expect(
        uploadVoiceMessage(mockFileUri, mockChatId)
      ).rejects.toThrow('Voice message too large');
    });
  });
});
