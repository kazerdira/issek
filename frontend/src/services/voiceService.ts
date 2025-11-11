import { api } from './api';
import Constants from 'expo-constants';

const API_URL = Constants.expoConfig?.extra?.EXPO_PUBLIC_BACKEND_URL || process.env.EXPO_PUBLIC_BACKEND_URL;

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
    console.log('📤 Starting voice upload:', { fileUri, chatId });

    // Get auth token from api defaults
    const authToken = api.defaults.headers.common['Authorization'];
    if (!authToken) {
      throw new Error('No auth token found');
    }

    console.log('📁 Preparing FormData for upload...');

    // Create FormData for multipart upload
    const formData = new FormData();
    
    // Extract filename from URI
    const filename = fileUri.split('/').pop() || 'voice_message.m4a';
    
    // Add the file to FormData - React Native format
    // @ts-ignore - React Native FormData accepts this format
    formData.append('file', {
      uri: fileUri,
      name: filename,
      type: 'audio/m4a',
    });
    
    formData.append('chat_id', chatId);

    console.log('📤 Uploading to:', `${API_URL}/api/media/upload-voice`);

    // Use native fetch with FormData - works reliably in React Native
    const response = await fetch(`${API_URL}/api/media/upload-voice`, {
      method: 'POST',
      headers: {
        'Authorization': authToken as string,
        // Don't set Content-Type - browser sets it automatically with boundary
      },
      body: formData,
    });

    console.log('📨 Upload response status:', response.status);

    if (!response.ok) {
      const errorText = await response.text();
      let errorData;
      try {
        errorData = JSON.parse(errorText);
      } catch {
        errorData = { detail: errorText };
      }
      console.error('❌ Upload failed:', { status: response.status, error: errorData });
      throw new Error(`Upload failed: ${errorData.detail || response.statusText}`);
    }

    const data = await response.json();
    console.log('✅ Voice upload successful:', data);

    return {
      mediaUrl: data.media_url,
      fileSize: data.file_size,
      contentType: data.content_type,
    };
  } catch (error: any) {
    console.error('❌ Error uploading voice message:', {
      message: error.message,
      name: error.name,
    });
    throw new Error(`Failed to upload voice message: ${error.message}`);
  }
};
