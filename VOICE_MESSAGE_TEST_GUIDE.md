# Voice Messaging Test Guide

## Test Checklist

### 1. Recording Test
- [ ] Open chat screen
- [ ] Click microphone button
- [ ] **Expected:** Red recording dot appears, timer starts
- [ ] **Check Console:** Should see "🎤 Recording started" or similar
- [ ] Record for 2-3 seconds
- [ ] **Expected:** Timer shows 00:02 or 00:03

### 2. Preview Test
- [ ] Click "Stop" button after recording
- [ ] **Expected:** Preview mode appears with play button
- [ ] **Check Console:** Should see "🎤 Recording stopped, URI: file://..."
- [ ] Click play button
- [ ] **Expected:** Your voice plays back
- [ ] **Check Console:** Audio playback status updates

### 3. Upload Test  
- [ ] Click "Send" button
- [ ] **Check Console - Should See:**
```
📨 Sending voice message: {uri: "file://...", duration: X.X}
📤 Starting voice upload: {fileUri: "file://...", chatId: "..."}
📁 File info: {exists: true, size: XXXXX, uri: "file://..."}
📨 Upload result: {status: 200, body: "{...}"}
✅ Voice upload successful: {media_url: "data:audio/...", ...}
Voice message sent successfully
```

- [ ] **If You See Network Error:**
  - Check `📁 File info:` - does `exists: true`?
  - Check `📨 Upload result:` - what is the status code?
  - Check backend console - did it receive the request?

### 4. Display Test
- [ ] After sending, voice message should appear in chat
- [ ] **Expected:** Blue bubble with waveform animation
- [ ] Click play button on the message
- [ ] **Expected:** Waveform animates, audio plays
- [ ] **Check:** Timer shows progress

### 5. Real-time Test
- [ ] Open chat on second device/browser
- [ ] Send voice message from first device
- [ ] **Expected:** Message appears immediately on second device
- [ ] Play message on second device
- [ ] **Expected:** Audio plays correctly

### 6. Multiple Send Test
- [ ] Send first voice message
- [ ] Wait for it to appear
- [ ] Click microphone button again
- [ ] Record second message
- [ ] Send it
- [ ] **Expected:** Both should work without issues

## Common Issues & Solutions

### Issue: "Network Error" with no response
**Possible Causes:**
1. File doesn't exist (`exists: false` in console)
2. Auth token missing
3. Backend not receiving request
4. CORS or network configuration

**Debug Steps:**
1. Check console for `📁 File info:` - verify `exists: true`
2. Check console for auth token (should not be null)
3. Check backend logs - did it receive POST to `/api/media/upload-voice`?
4. Try curl command to test backend directly:
```bash
curl -X POST http://192.168.1.44:8000/api/media/upload-voice \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/path/to/test.m4a" \
  -F "chat_id=test-chat-id"
```

### Issue: Upload succeeds but message doesn't appear
**Possible Causes:**
1. Socket not connected
2. Message not being sent to backend after upload
3. Backend not broadcasting to other clients

**Debug Steps:**
1. Check console after upload - should see "Voice message sent successfully"
2. Check if `chatsAPI.sendMessage` was called
3. Check backend logs - did it receive POST to `/api/chats/{id}/messages`?
4. Check socket connection status

### Issue: Can't send twice
**Possible Causes:**
1. `isRecordingVoice` state not resetting
2. `sending` state blocking
3. VoiceRecorder not unmounting properly

**Debug Steps:**
1. After first send, check if mic button is clickable
2. Check console - are there errors preventing second recording?
3. Try clicking cancel and then mic button again

### Issue: Waveform doesn't animate
**Not critical** - This is visual only. Audio should still play.

## Manual Backend Test

Test the backend endpoint directly:

```typescript
// Add this to your chat screen temporarily
const testUploadEndpoint = async () => {
  const testData = new FormData();
  testData.append('chat_id', chatId);
  testData.append('file', {
    uri: 'file:///path/to/test.m4a',
    name: 'test.m4a',
    type: 'audio/m4a',
  } as any);

  try {
    const response = await fetch('http://192.168.1.44:8000/api/media/upload-voice', {
      method: 'POST',
      headers: {
        'Authorization': api.defaults.headers.common['Authorization'] as string,
      },
      body: testData,
    });
    
    console.log('Test upload status:', response.status);
    const data = await response.json();
    console.log('Test upload response:', data);
  } catch (error) {
    console.error('Test upload error:', error);
  }
};

// Call it: testUploadEndpoint();
```

## Expected Console Flow (Success)

```
1. User clicks mic button:
   → "🎤 Starting recording..."
   
2. User records for 2 seconds:
   → Timer updates: 00:00, 00:01, 00:02
   
3. User clicks stop:
   → "🎤 Recording stopped, URI: file://..."
   → Preview mode activated
   
4. User clicks send:
   → "📨 Sending voice message: {uri, duration}"
   → "📤 Starting voice upload: {fileUri, chatId}"
   → "📁 File info: {exists: true, size: 50000, ...}"
   → "📨 Upload result: {status: 200, body: ...}"
   → "✅ Voice upload successful: {media_url, file_size, content_type}"
   → "Voice message sent successfully"
   → Message appears in chat with waveform
```

## Next Steps

After going through this checklist, report:
1. Which step failed?
2. What exactly did the console show?
3. Did the backend receive the request?
