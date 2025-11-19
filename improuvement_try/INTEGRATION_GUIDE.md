# Voice Messaging Feature - Integration Guide

This guide will help you integrate the professional voice messaging feature into your chat application.

## Overview

The voice messaging feature includes:
- ✅ Hold to record (max 3 minutes)
- ✅ Slide to cancel functionality
- ✅ Real-time duration display
- ✅ Voice message bubbles with waveform visualization
- ✅ Playback controls with progress tracking
- ✅ Professional UI matching your app colors
- ✅ Backend support for voice file uploads

## Files Provided

### Backend
- `routes_media.py` - Voice message upload endpoint

### Frontend
- `VoiceRecorder.tsx` - Recording component (place in `frontend/src/components/`)
- `VoiceMessageBubble.tsx` - Playback component (place in `frontend/src/components/`)
- `voiceService.ts` - Upload helper (place in `frontend/src/services/`)
- `chat_[id]_updated.tsx` - Updated chat screen (replace `frontend/app/chat/[id].tsx`)

## Installation Steps

### 1. Install Required Dependencies

```bash
cd frontend
npx expo install expo-av react-native-reanimated
```

### 2. Update Backend

#### Step 2.1: Add media routes to server
Edit `backend/server.py`:

```python
# Add this import at the top
from routes_media import router as media_router

# Add this line after other router includes (around line 30)
api_router.include_router(media_router)
```

#### Step 2.2: Copy the media route file
Copy `routes_media.py` to `backend/routes_media.py`

### 3. Update Frontend

#### Step 3.1: Copy components
```bash
# Copy to your frontend components directory
cp VoiceRecorder.tsx frontend/src/components/
cp VoiceMessageBubble.tsx frontend/src/components/
```

#### Step 3.2: Copy service
```bash
# Copy to your frontend services directory
cp voiceService.ts frontend/src/services/
```

#### Step 3.3: Update chat screen
```bash
# Replace your existing chat screen
cp chat_[id]_updated.tsx frontend/app/chat/[id].tsx
```

#### Step 3.4: Configure Reanimated
Add to `babel.config.js`:

```javascript
module.exports = function (api) {
  api.cache(true);
  return {
    presets: ['babel-preset-expo'],
    plugins: ['react-native-reanimated/plugin'], // Add this line
  };
};
```

#### Step 3.5: Update app.json for audio permissions
Add to `app.json`:

```json
{
  "expo": {
    "ios": {
      "infoPlist": {
        "NSMicrophoneUsageDescription": "This app needs access to the microphone to record voice messages."
      }
    },
    "android": {
      "permissions": ["RECORD_AUDIO"]
    }
  }
}
```

### 4. Update API Service

Add the media endpoint to `frontend/src/services/api.ts`:

```typescript
// Add at the end of the file
export { uploadVoiceMessage } from './voiceService';
```

## How to Use

### For Users

1. **Start Recording**: Tap and hold the microphone icon
2. **Cancel**: While holding, slide your finger to the left
3. **Send**: Release your finger to send the voice message
4. **Listen**: Tap the play button in voice message bubbles
5. **Progress**: See waveform animation and progress while playing

### Technical Details

#### Recording Format
- Format: M4A (AAC)
- Quality: High quality preset from Expo AV
- Max Duration: 180 seconds (3 minutes)
- Auto-stop at max duration

#### Storage
- Currently uses base64 encoding (good for development)
- For production: Replace with cloud storage (S3, Google Cloud Storage)
- File size limit: 10MB

#### UI Components

**VoiceRecorder**
- Real-time duration display
- Pulsing recording indicator
- Slide-to-cancel gesture
- Progress bar showing recording progress
- Haptic feedback

**VoiceMessageBubble**
- Animated waveform visualization (20 bars)
- Play/pause controls
- Progress indicator overlay
- Duration display
- Status indicators (sent/read)
- Adapts to sender/receiver styling

## Customization

### Colors
All colors are already configured to use your app's color scheme from `frontend/src/theme/colors.ts`:

- Primary: `colors.primary` - #6C5CE7
- Message sent: `colors.messageSent`
- Message received: `colors.messageReceived`
- Error/Cancel: `colors.error`

### Duration Limits
To change max recording duration, edit `VoiceRecorder.tsx`:

```typescript
const MAX_DURATION = 180; // Change to desired seconds
```

### Waveform Bars
To change number of waveform bars in playback, edit `VoiceMessageBubble.tsx`:

```typescript
{[...Array(20)].map((_, i) => ( // Change 20 to desired number
  <WaveformBar key={i} index={i} />
))}
```

## Backend Production Considerations

### Cloud Storage Integration

Replace base64 storage with cloud storage in `routes_media.py`:

```python
# Example with AWS S3
import boto3

s3_client = boto3.client('s3')

@router.post("/upload-voice")
async def upload_voice(...):
    # Upload to S3
    file_key = f"voice_messages/{uuid.uuid4()}.m4a"
    s3_client.upload_fileobj(
        file.file,
        'your-bucket-name',
        file_key,
        ExtraArgs={'ContentType': file.content_type}
    )
    
    # Generate URL
    media_url = f"https://your-bucket.s3.amazonaws.com/{file_key}"
    
    return {
        "media_url": media_url,
        "file_size": len(content),
        "content_type": file.content_type
    }
```

### Database Updates

The Message model already supports voice messages:
- `message_type`: 'voice'
- `media_url`: URL/base64 of audio
- `duration`: Length in seconds
- `file_size`: Size in bytes

## Testing Checklist

- [ ] Can record voice message (hold mic button)
- [ ] Recording shows timer and pulsing indicator
- [ ] Slide left cancels recording
- [ ] Release sends voice message
- [ ] Auto-stops at 3 minutes
- [ ] Voice messages appear in chat
- [ ] Can play/pause voice messages
- [ ] Waveform animates during playback
- [ ] Progress indicator updates
- [ ] Duration displays correctly
- [ ] Works on both iOS and Android

## Troubleshooting

### "Permission denied" error
- Ensure microphone permissions are added to app.json
- On Android: Check that RECORD_AUDIO permission is granted
- On iOS: Check NSMicrophoneUsageDescription is in Info.plist

### Reanimated errors
- Ensure babel plugin is added
- Clear cache: `npx expo start -c`
- Rebuild the app

### Audio not playing
- Check Audio.setAudioModeAsync settings
- Verify media_url is valid
- Check console for playback errors

### Upload failing
- Verify backend routes_media.py is imported in server.py
- Check file size limits
- Ensure multipart/form-data is supported

## Future Enhancements

Possible improvements:
- Lock recording (swipe up to lock)
- Speed playback (1.5x, 2x)
- Waveform from actual audio data
- Audio compression
- Voice-to-text transcription
- Audio filters/effects

## Support

If you encounter any issues:
1. Check console logs for errors
2. Verify all dependencies are installed
3. Ensure permissions are granted
4. Test on a real device (not just simulator)

---

**Note**: This implementation uses your app's existing color scheme and follows your design patterns for a professional, industrial-grade experience.
