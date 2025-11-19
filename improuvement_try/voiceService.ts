import { api } from './api';

export interface VoiceUploadResponse {
  mediaUrl: string;
  fileSize: number;
  contentType: string;
}

export const uploadVoiceMessage = async (
  fileUri: string,
  chatId: string
): Promise<VoiceUploadResponse> => {
  try {
    // Create form data
    const formData = new FormData();
    
    // Add the audio file
    const filename = fileUri.split('/').pop() || 'voice_message.m4a';
    const match = /\.(\w+)$/.exec(filename);
    const type = match ? `audio/${match[1]}` : 'audio/m4a';

    formData.append('file', {
      uri: fileUri,
      name: filename,
      type,
    } as any);

    formData.append('chat_id', chatId);

    // Upload to backend
    const response = await api.post('/media/upload-voice', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 60000, // 60 seconds for voice upload
    });

    return {
      mediaUrl: response.data.media_url,
      fileSize: response.data.file_size,
      contentType: response.data.content_type,
    };
  } catch (error) {
    console.error('Error uploading voice message:', error);
    throw new Error('Failed to upload voice message');
  }
};
