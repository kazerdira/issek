# Voice Messaging Implementation Checklist

Follow this checklist to integrate the voice messaging feature into your chat app.

## 📦 Phase 1: Dependencies & Setup

### Step 1.1: Install Frontend Dependencies
```bash
cd frontend
npx expo install expo-av react-native-reanimated
```
- [ ] expo-av installed
- [ ] react-native-reanimated installed
- [ ] No installation errors

### Step 1.2: Update Babel Configuration
Edit `frontend/babel.config.js`:
```javascript
module.exports = function (api) {
  api.cache(true);
  return {
    presets: ['babel-preset-expo'],
    plugins: ['react-native-reanimated/plugin'], // ← Add this
  };
};
```
- [ ] Reanimated plugin added to babel.config.js

### Step 1.3: Add Permissions
Edit `frontend/app.json`:
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
- [ ] iOS microphone permission added
- [ ] Android RECORD_AUDIO permission added

## 🔧 Phase 2: Backend Integration

### Step 2.1: Add Media Routes File
```bash
cp routes_media.py backend/routes_media.py
```
- [ ] File copied to backend directory

### Step 2.2: Update Server Configuration
Edit `backend/server.py`, add these lines:

```python
# Add import (near top with other route imports)
from routes_media import router as media_router

# Add router (after other router includes)
api_router.include_router(media_router)
```
- [ ] Import added
- [ ] Router included
- [ ] No syntax errors

### Step 2.3: Restart Backend Server
```bash
cd backend
# Stop current server (Ctrl+C)
uvicorn server:app --reload
```
- [ ] Server restarted
- [ ] No startup errors
- [ ] `/api/media/upload-voice` endpoint available

## 🎨 Phase 3: Frontend Components

### Step 3.1: Copy Components
```bash
cd frontend/src/components

# Copy VoiceRecorder
cp ../../../VoiceRecorder.tsx ./VoiceRecorder.tsx

# Copy VoiceMessageBubble
cp ../../../VoiceMessageBubble.tsx ./VoiceMessageBubble.tsx
```
- [ ] VoiceRecorder.tsx in components folder
- [ ] VoiceMessageBubble.tsx in components folder

### Step 3.2: Copy Voice Service
```bash
cd frontend/src/services
cp ../../../voiceService.ts ./voiceService.ts
```
- [ ] voiceService.ts in services folder

### Step 3.3: Update Chat Screen
```bash
cd frontend/app/chat
# Backup current file
cp [id].tsx [id].tsx.backup

# Replace with new version
cp ../../../../chat_[id]_updated.tsx ./[id].tsx
```
- [ ] Original chat screen backed up
- [ ] New chat screen in place

### Step 3.4: Verify Imports
Check that these imports exist in your new chat screen:
```typescript
import { VoiceRecorder } from '../../src/components/VoiceRecorder';
import { VoiceMessageBubble } from '../../src/components/VoiceMessageBubble';
import { uploadVoiceMessage } from '../../src/services/voiceService';
```
- [ ] All imports present
- [ ] No TypeScript errors

## 🧪 Phase 4: Testing

### Step 4.1: Clear Cache & Restart
```bash
cd frontend
npx expo start -c
```
- [ ] Expo dev server started with cleared cache
- [ ] App loaded on device/simulator

### Step 4.2: Test Recording
1. Navigate to any chat
2. Tap and hold the microphone icon
3. Observe:
   - [ ] Timer starts counting
   - [ ] Red dot pulses
   - [ ] Progress bar appears
   - [ ] Haptic feedback on start

### Step 4.3: Test Cancel Gesture
1. Start recording (hold mic)
2. Slide finger to the left
3. Observe:
   - [ ] "Cancel" text appears
   - [ ] Recording cancels when sliding far enough
   - [ ] No message sent

### Step 4.4: Test Send
1. Start recording
2. Speak for a few seconds
3. Release finger
4. Observe:
   - [ ] Recording stops
   - [ ] Message uploads
   - [ ] Voice bubble appears in chat
   - [ ] Duration shows correctly

### Step 4.5: Test Playback
1. Tap play button on voice message
2. Observe:
   - [ ] Audio plays
   - [ ] Waveform animates
   - [ ] Progress indicator moves
   - [ ] Duration counts up
   - [ ] Pause button appears

### Step 4.6: Test Max Duration
1. Start recording
2. Wait 3 minutes
3. Observe:
   - [ ] Recording auto-stops at 3:00
   - [ ] Message sent automatically

### Step 4.7: Test on Real Device
- [ ] iOS: Test on real iPhone (mic permission)
- [ ] Android: Test on real device (mic permission)

## 🔍 Phase 5: Verification

### Step 5.1: Check Backend Logs
Look for:
```
Voice message uploaded for chat {chat_id}, size: X bytes
```
- [ ] Upload logs appearing
- [ ] No error messages

### Step 5.2: Check Database
Query messages collection:
```javascript
db.messages.find({ message_type: 'voice' })
```
Verify fields:
- [ ] message_type is 'voice'
- [ ] media_url is populated
- [ ] duration is set
- [ ] file_size is set

### Step 5.3: Check UI/UX
- [ ] Voice bubbles look good
- [ ] Colors match your theme
- [ ] Animations are smooth
- [ ] No layout issues
- [ ] Works in both portrait/landscape

## 🐛 Troubleshooting

### Issue: "Permission denied" error
**Solution:**
1. Check app.json has correct permissions
2. Reinstall app (permissions update)
3. Manually grant permission in device settings

### Issue: Reanimated errors
**Solution:**
```bash
# Clear all caches
npx expo start -c
# Rebuild
rm -rf node_modules
npm install
```

### Issue: Upload failing
**Solution:**
1. Check backend server is running
2. Verify media router is included
3. Check console for specific error
4. Test endpoint manually: `POST /api/media/upload-voice`

### Issue: Audio not playing
**Solution:**
1. Check media_url is valid
2. Verify Audio.setAudioModeAsync settings
3. Test on real device (not just simulator)
4. Check console for playback errors

### Issue: Waveform not animating
**Solution:**
1. Verify react-native-reanimated is installed
2. Check babel.config.js has reanimated plugin
3. Clear cache and rebuild

## ✅ Final Checklist

### Functionality
- [ ] Can record voice messages
- [ ] Can cancel recording (slide left)
- [ ] Can send voice messages
- [ ] Voice messages appear in chat
- [ ] Can play voice messages
- [ ] Playback controls work
- [ ] Progress tracking works
- [ ] Duration displays correctly

### UI/UX
- [ ] Recording UI looks professional
- [ ] Voice bubbles match app design
- [ ] Animations are smooth
- [ ] Colors are correct
- [ ] Responsive on all screen sizes

### Performance
- [ ] No lag during recording
- [ ] Upload completes quickly
- [ ] Playback is smooth
- [ ] No memory leaks
- [ ] Battery usage is reasonable

### Cross-Platform
- [ ] Works on iOS
- [ ] Works on Android
- [ ] Permissions granted properly
- [ ] Audio quality is good

## 🎉 Success!

Once all items are checked, your voice messaging feature is fully integrated!

## 📚 Next Steps

Consider these enhancements:
- [ ] Add lock recording feature (swipe up)
- [ ] Implement playback speed control
- [ ] Add voice-to-text transcription
- [ ] Integrate cloud storage (S3, GCS)
- [ ] Add audio compression
- [ ] Implement audio filters

## 📞 Need Help?

Refer to:
- `INTEGRATION_GUIDE.md` - Detailed technical guide
- `FEATURE_SUMMARY.md` - Feature overview and architecture
- Console logs - Check for specific errors
- Expo documentation - expo-av and permissions

---

**Congratulations on adding professional voice messaging to your chat app!** 🎤✨
