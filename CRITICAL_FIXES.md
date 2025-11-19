# Critical Missing Features - Quick Reference

## 🔥 CRITICAL (Fix Immediately)

### 1. Socket Notifications for Friend/Group Events
**Files to Edit:**
- `backend/routes_friends.py` - Add socket notifications after accept/reject
- `backend/routes_chat.py` - Add notifications for add/remove participants
- `frontend/src/services/socket.ts` - Add listeners for friend_request events

**Why Critical:** Users don't see friend requests or group invites until app restart

### 2. Chat last_message Update
**File:** `backend/routes_chat.py` - `send_message()` function
**Why Critical:** Chat list shows wrong/outdated message previews

### 3. media_metadata Field Missing
**File:** `backend/models.py` - Message class
**Why Critical:** Voice messages break (duration not saved)

---

## ⚠️ HIGH PRIORITY (Fix This Week)

### 4. Delete For Me Logic
**File:** `backend/routes_chat.py` - `delete_message()` function
**Current:** Only supports "delete for everyone"
**Needed:** Support "delete for me" using `deleted_for` array

### 5. Direct Chat from Contacts
**File:** `frontend/app/(tabs)/contacts.tsx`
**Missing:** "Message" button to start chat with friend
**Current:** Must go to create chat screen

### 6. Socket: chat_created Event
**Files:**
- `backend/routes_chat.py` - Emit after creating chat
- `frontend/src/services/socket.ts` - Listen for new chats
**Impact:** New chats don't appear in other users' lists

---

## 📝 MEDIUM PRIORITY (Nice to Have)

### 7. Group Avatar Upload
**File:** `frontend/app/chat/info.tsx`
**Status:** Button exists but not functional

### 8. Real-time Participant Count
**Files:** Need socket notification when members added/removed

### 9. Channel Default Rules
**File:** `backend/routes_chat.py` - Enforce only_admins_can_post for channels

---

## ✅ WHAT'S COMPLETE

- ✅ Friend request workflow (send/accept/reject)
- ✅ Block/Unblock users
- ✅ Search with autocomplete
- ✅ Group/Channel creation
- ✅ Admin promotion/demotion
- ✅ Channel posting restrictions (UI-side)
- ✅ Message reactions
- ✅ Reply to messages
- ✅ Typing indicators
- ✅ Voice messages
- ✅ Read receipts
- ✅ Online status

---

## 🎯 Estimated Fix Time

| Priority | Items | Total Time |
|----------|-------|------------|
| CRITICAL | 3 items | ~50 minutes |
| HIGH | 3 items | ~65 minutes |
| MEDIUM | 3 items | ~55 minutes |
| **TOTAL** | **9 items** | **~3 hours** |

---

## 🚀 Recommended Fix Order

1. **Add media_metadata field** (5 min) - Prevents voice message bugs
2. **Update chat.last_message** (15 min) - Fixes chat list display
3. **Add friend request socket events** (30 min) - Core UX improvement
4. **Add group event socket notifications** (30 min) - Core UX improvement
5. **Add socket listeners in frontend** (20 min) - Receive the notifications
6. **Implement delete for me** (20 min) - Privacy feature
7. **Add Message Friend button** (15 min) - UX improvement
8. **Implement chat_created socket** (20 min) - Real-time chat list
9. **Add group avatar upload** (30 min) - Polish feature

---

## 📌 Notes

- System is **functional** for basic messaging
- Missing features are mainly **real-time notifications** and **UX polish**
- Core chat, friend, and group logic is **solid**
- No security vulnerabilities identified
- Database schema is **complete**
- API endpoints are **well-structured**
