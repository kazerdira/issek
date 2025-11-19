# 🚀 Implementation Checklist - Fix Priority Order

## ⚡ PHASE 1: Critical Fixes (3-4 hours) - DO THESE FIRST

### ✅ 1. Add media_metadata Field (5 minutes)
**File:** `backend/models.py`
```python
# In Message class, add:
media_metadata: Optional[Dict[str, Any]] = None
```
**Why:** Voice messages currently break without this field

---

### ✅ 2. Update Chat's last_message (15 minutes)
**File:** `backend/routes_chat.py` - `send_message()` function

Add after `await create_message(message_dict)`:
```python
# Update chat's last_message
db = Database.get_db()
await db.chats.update_one(
    {'id': chat_id},
    {
        '$set': {
            'last_message': {
                'id': message_id,
                'content': message_dict['content'],
                'message_type': message_dict['message_type'],
                'sender_id': current_user['id'],
                'created_at': message_dict['created_at']
            },
            'updated_at': utc_now()
        }
    }
)
```
**Why:** Chat list shows wrong/outdated message previews

---

### ✅ 3. Add Friend Request Socket Notifications (30 minutes)

**File:** `backend/routes_friends.py`

#### In `send_friend_request()` - after creating request:
```python
from socket_manager import socket_manager

# Notify receiver
await socket_manager.send_message_to_user(
    user_id, 
    'friend_request_received', 
    {
        'request_id': request_id,
        'sender': {
            'id': current_user['id'],
            'username': current_user['username'],
            'display_name': current_user['display_name'],
            'avatar': current_user.get('avatar')
        }
    }
)
```

#### In `accept_friend_request()` - after updating friends:
```python
# Notify sender
sender = await get_user_by_id(sender_id)
await socket_manager.send_message_to_user(
    sender_id,
    'friend_request_accepted',
    {
        'user': {
            'id': current_user['id'],
            'username': current_user['username'],
            'display_name': current_user['display_name'],
            'avatar': current_user.get('avatar')
        }
    }
)
```

#### In `reject_friend_request()` - after updating status:
```python
# Notify sender
await socket_manager.send_message_to_user(
    request['sender_id'],
    'friend_request_rejected',
    {
        'user_id': current_user['id']
    }
)
```

**Why:** Users don't see friend requests until app restart

---

### ✅ 4. Add Group Event Socket Notifications (30 minutes)

**File:** `backend/routes_chat.py`

#### In `create_new_chat()` - after creating chat:
```python
# Notify all participants
for participant_id in chat_data.participants:
    if participant_id != current_user['id']:
        await socket_manager.send_message_to_user(
            participant_id,
            'chat_created',
            {
                'chat': response.dict()
            }
        )
```

#### In `add_participants()` - after adding:
```python
# Notify new participants
for user_id in valid_user_ids:
    await socket_manager.send_message_to_user(
        user_id,
        'added_to_chat',
        {
            'chat': updated_chat
        }
    )

# Notify existing members
for participant_id in chat['participants']:
    if participant_id not in valid_user_ids:
        await socket_manager.send_message_to_user(
            participant_id,
            'participants_added',
            {
                'chat_id': chat_id,
                'new_participants': valid_user_ids
            }
        )
```

#### In `remove_participant()` - after removing:
```python
# Notify removed user
await socket_manager.send_message_to_user(
    user_id,
    'removed_from_chat',
    {
        'chat_id': chat_id
    }
)

# Notify remaining members
for participant_id in updated_chat['participants']:
    await socket_manager.send_message_to_user(
        participant_id,
        'participant_removed',
        {
            'chat_id': chat_id,
            'user_id': user_id
        }
    )
```

**Why:** Group members don't see real-time updates

---

### ✅ 5. Add Socket Listeners in Frontend (20 minutes)

**File:** `frontend/src/services/socket.ts`

Add to `setupListeners()`:
```typescript
// Friend request events
this.socket.on('friend_request_received', (data) => {
  console.log('Friend request received:', data);
  const { loadReceivedRequests } = useFriendStore.getState();
  loadReceivedRequests();
  // TODO: Show in-app notification
});

this.socket.on('friend_request_accepted', (data) => {
  console.log('Friend request accepted:', data);
  const { loadFriends } = useFriendStore.getState();
  loadFriends();
  // TODO: Show in-app notification
});

this.socket.on('friend_request_rejected', (data) => {
  console.log('Friend request rejected:', data);
  // TODO: Show in-app notification
});

// Chat events
this.socket.on('chat_created', (data) => {
  console.log('New chat created:', data);
  const { addChat } = useChatStore.getState();
  addChat(data.chat);
});

this.socket.on('added_to_chat', (data) => {
  console.log('Added to chat:', data);
  const { addChat } = useChatStore.getState();
  addChat(data.chat);
});

this.socket.on('removed_from_chat', (data) => {
  console.log('Removed from chat:', data);
  const { chats, setChats } = useChatStore.getState();
  setChats(chats.filter(c => c.id !== data.chat_id));
});

this.socket.on('participants_added', (data) => {
  console.log('Participants added:', data);
  const { updateChat } = useChatStore.getState();
  // Reload chat details
});

this.socket.on('participant_removed', (data) => {
  console.log('Participant removed:', data);
  const { updateChat } = useChatStore.getState();
  // Reload chat details
});
```

**Why:** Frontend needs to listen for the events backend now sends

---

## 🔥 PHASE 2: High Priority (2-3 hours) - DO NEXT

### ✅ 6. Implement "Delete For Me" (20 minutes)

**File:** `backend/routes_chat.py` - `delete_message()`

Replace the current logic:
```python
@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: str,
    for_everyone: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """Delete a message"""
    message = await get_message_by_id(message_id)
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    if message['sender_id'] != current_user['id'] and for_everyone:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only delete your own messages for everyone"
        )
    
    if for_everyone:
        # Delete for everyone
        await update_message(message_id, {
            'deleted': True, 
            'content': 'This message was deleted'
        })
        
        # Broadcast deletion
        await socket_manager.broadcast_message_deleted(
            message['chat_id'], 
            message_id
        )
    else:
        # Delete for me only
        deleted_for = message.get('deleted_for', [])
        if current_user['id'] not in deleted_for:
            deleted_for.append(current_user['id'])
            await update_message(message_id, {'deleted_for': deleted_for})
    
    return {"message": "Message deleted"}
```

**Why:** Privacy - users should be able to remove messages from their view

---

### ✅ 7. Add "Message Friend" Button (15 minutes)

**File:** `frontend/app/(tabs)/contacts.tsx`

Add function:
```typescript
const handleMessageFriend = async (friendId: string) => {
  try {
    // Check if direct chat exists
    const existingChat = chats.find(
      chat => chat.chat_type === 'direct' && 
      chat.participants.includes(friendId)
    );
    
    if (existingChat) {
      router.push(`/chat/${existingChat.id}`);
    } else {
      // Create direct chat
      const response = await chatsAPI.createChat({
        chat_type: 'direct',
        participants: [friendId],
      });
      router.push(`/chat/${response.data.id}`);
    }
  } catch (error) {
    console.error('Error creating chat:', error);
  }
};
```

Update `renderFriendItem`:
```tsx
<TouchableOpacity onPress={() => handleMessageFriend(item.id)}>
  <Ionicons name="chatbubble-outline" size={24} color={colors.primary} />
</TouchableOpacity>
```

**Why:** UX improvement - direct access to chat

---

### ✅ 8. Add Chat Sorting by Last Message (10 minutes)

**File:** `frontend/app/(tabs)/chats.tsx`

After `loadChats()`:
```typescript
const loadChats = async () => {
  try {
    const response = await chatsAPI.getChats();
    
    // Sort by last message timestamp
    const sortedChats = response.data.sort((a, b) => {
      const aTime = a.last_message?.created_at || a.created_at;
      const bTime = b.last_message?.created_at || b.created_at;
      return new Date(bTime).getTime() - new Date(aTime).getTime();
    });
    
    setChats(sortedChats);
    console.log(`Loaded ${sortedChats.length} chats`);
  } catch (error) {
    console.error('Error loading chats:', error);
  } finally {
    setLoading(false);
    setRefreshing(false);
  }
};
```

**Why:** Most recent chats should appear first

---

## 💎 PHASE 3: Polish (4-6 hours) - OPTIONAL

### ✅ 9. Implement Edit Message UI (30 minutes)
- Add edit button in MessageActionsSheet
- Add inline edit input
- Call existing backend endpoint

### ✅ 10. Implement Forward Message UI (30 minutes)
- Add chat picker modal
- Connect to existing backend endpoint

### ✅ 11. Implement Pin Message UI (40 minutes)
- Add pin button
- Show pinned messages bar
- Connect to existing backend endpoints

### ✅ 12. Add Group Avatar Upload (30 minutes)
- Connect ImagePicker to change avatar button
- Upload to backend

### ✅ 13. Add User Profile Screen (1 hour)
- View profile screen
- Edit profile screen

### ✅ 14. Add Message Search (2 hours)
- Backend: Search endpoint
- Frontend: Search UI

### ✅ 15. Add Media Gallery (2 hours)
- View all media in chat
- Grid layout

---

## 🧪 TESTING CHECKLIST

After implementing Phase 1 & 2, test these scenarios:

### Friend System:
- [ ] Send friend request → Receiver sees notification
- [ ] Accept friend request → Sender sees notification
- [ ] Reject friend request → Sender gets notified
- [ ] Block user → User disappears from search
- [ ] Unblock user → User reappears

### Group System:
- [ ] Create group → All members see new chat
- [ ] Add member → New member sees chat, others notified
- [ ] Remove member → Member loses access, others notified
- [ ] Promote admin → User gets admin powers
- [ ] Channel restriction → Non-admins can't post

### Messaging:
- [ ] Send message → Chat list updates last message
- [ ] Delete for everyone → Message deleted for all
- [ ] Delete for me → Message deleted for you only
- [ ] Voice message → Duration displays correctly
- [ ] React to message → Toggle works

### Real-time:
- [ ] Friend request arrives without refresh
- [ ] New group appears without refresh
- [ ] Message arrives in real-time
- [ ] Online status updates

---

## 📝 Code Quality Checklist

Before marking complete:
- [ ] All console.log statements reviewed
- [ ] Error handling added
- [ ] Loading states added
- [ ] Success feedback added
- [ ] TypeScript errors resolved
- [ ] ESLint warnings checked

---

## 🎯 Success Criteria

**Phase 1 Complete When:**
- ✅ Friend requests work without app refresh
- ✅ Group invites appear in real-time
- ✅ Chat list shows correct last message
- ✅ Voice messages save duration
- ✅ All socket events are listened to

**Phase 2 Complete When:**
- ✅ Delete for me works
- ✅ Can message friend from contacts
- ✅ Chat list sorted by recent activity

**Ready for Production When:**
- ✅ All Phase 1 & 2 complete
- ✅ All testing scenarios pass
- ✅ No critical bugs
- ✅ Error logging added
- ✅ Rate limiting added

---

## 📊 Progress Tracker

```
Total Tasks: 15
Phase 1 (Critical): 5 tasks
Phase 2 (High): 3 tasks
Phase 3 (Polish): 7 tasks

Estimated Total Time: 9-13 hours
- Phase 1: 3-4 hours ⚡
- Phase 2: 2-3 hours 🔥
- Phase 3: 4-6 hours 💎
```

**Start with Phase 1 - these are blocking issues for a good user experience!**
