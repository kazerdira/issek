"""
Comprehensive tests for Media API
Tests file uploads, voice messages, media in chats, validation
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
import io

from helpers import (
    BASE_URL,
    create_test_user,
    establish_friendship,
    create_direct_chat,
    create_group_chat,
    send_message
)


class TestVoiceMessageUpload:
    """Test voice message upload functionality"""
    
    @pytest.mark.asyncio
    async def test_upload_voice_message(self):
        """Test uploading a valid voice message"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            user1 = await create_test_user(client, "voice_sender")
            user2 = await create_test_user(client, "voice_receiver")
            
            await establish_friendship(client, user1, user2)
            chat = await create_direct_chat(client, user1, user2)
            
            # Create a fake audio file
            audio_content = b"fake audio data " * 100  # Small audio file
            audio_file = io.BytesIO(audio_content)
            
            # Upload voice message
            response = await client.post(
                "/api/media/upload-voice",
                files={"file": ("voice.mp3", audio_file, "audio/mpeg")},
                data={"chat_id": chat["id"]},
                headers=user1["headers"]
            )
            
            print(f"\n🎤 Upload voice message: {response.status_code}")
            assert response.status_code == 200
            
            result = response.json()
            assert "media_url" in result
            assert "file_size" in result
            assert "content_type" in result
            assert result["content_type"] == "audio/mpeg"
            
            print(f"✅ Voice message uploaded successfully")
            print(f"   File size: {result['file_size']} bytes")
            print(f"   Content type: {result['content_type']}")
    
    @pytest.mark.asyncio
    async def test_upload_voice_different_formats(self):
        """Test uploading voice messages in different audio formats"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            user1 = await create_test_user(client, "format_tester")
            user2 = await create_test_user(client, "format_receiver")
            
            await establish_friendship(client, user1, user2)
            chat = await create_direct_chat(client, user1, user2)
            
            audio_formats = [
                ("voice.mp3", "audio/mpeg"),
                ("voice.wav", "audio/wav"),
                ("voice.ogg", "audio/ogg"),
                ("voice.m4a", "audio/mp4")
            ]
            
            print(f"\n🎤 Testing different audio formats...")
            
            for filename, content_type in audio_formats:
                audio_content = b"fake audio " * 50
                audio_file = io.BytesIO(audio_content)
                
                response = await client.post(
                    "/api/media/upload-voice",
                    files={"file": (filename, audio_file, content_type)},
                    data={"chat_id": chat["id"]},
                    headers=user1["headers"]
                )
                
                print(f"   {filename} ({content_type}): {response.status_code}")
                assert response.status_code == 200
            
            print(f"✅ All audio formats accepted")
    
    @pytest.mark.asyncio
    async def test_send_message_with_voice(self):
        """Test sending a message with voice attachment"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            user1 = await create_test_user(client, "voice_msg_sender")
            user2 = await create_test_user(client, "voice_msg_receiver")
            
            await establish_friendship(client, user1, user2)
            chat = await create_direct_chat(client, user1, user2)
            
            # Upload voice message
            audio_content = b"voice data " * 100
            audio_file = io.BytesIO(audio_content)
            
            upload_response = await client.post(
                "/api/media/upload-voice",
                files={"file": ("voice.mp3", audio_file, "audio/mpeg")},
                data={"chat_id": chat["id"]},
                headers=user1["headers"]
            )
            
            assert upload_response.status_code == 200
            media_data = upload_response.json()
            
            print(f"\n🎤 Voice uploaded, sending message...")
            
            # Send message with voice attachment
            message_response = await client.post(
                f"/api/chats/{chat['id']}/messages",
                json={
                    "chat_id": chat["id"],
                    "sender_id": user1["user"]["id"],
                    "content": "Voice message",
                    "message_type": "voice",
                    "media_url": media_data["media_url"]
                },
                headers=user1["headers"]
            )
            
            print(f"💬 Send voice message: {message_response.status_code}")
            assert message_response.status_code == 200
            
            message = message_response.json()
            assert message["message_type"] == "voice"
            assert message["media_url"] is not None
            
            print(f"✅ Voice message sent successfully")


class TestMediaValidation:
    """Test media upload validation"""
    
    @pytest.mark.asyncio
    async def test_reject_non_audio_file(self):
        """Test that non-audio files are rejected"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            user1 = await create_test_user(client, "reject_user1")
            user2 = await create_test_user(client, "reject_user2")
            
            await establish_friendship(client, user1, user2)
            chat = await create_direct_chat(client, user1, user2)
            
            # Try to upload an image as voice
            image_content = b"fake image data"
            image_file = io.BytesIO(image_content)
            
            response = await client.post(
                "/api/media/upload-voice",
                files={"file": ("image.jpg", image_file, "image/jpeg")},
                data={"chat_id": chat["id"]},
                headers=user1["headers"]
            )
            
            print(f"\n🚫 Upload non-audio file: {response.status_code}")
            assert response.status_code == 400
            
            error = response.json()
            assert "must be an audio file" in error["detail"].lower()
            
            print(f"✅ Non-audio file rejected correctly")
    
    @pytest.mark.asyncio
    async def test_reject_oversized_file(self):
        """Test that files over 10MB are rejected"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            user1 = await create_test_user(client, "bigfile_user1")
            user2 = await create_test_user(client, "bigfile_user2")
            
            await establish_friendship(client, user1, user2)
            chat = await create_direct_chat(client, user1, user2)
            
            # Create a file larger than 10MB
            large_audio = b"x" * (11 * 1024 * 1024)  # 11MB
            audio_file = io.BytesIO(large_audio)
            
            print(f"\n📦 Uploading 11MB file (limit is 10MB)...")
            
            response = await client.post(
                "/api/media/upload-voice",
                files={"file": ("large.mp3", audio_file, "audio/mpeg")},
                data={"chat_id": chat["id"]},
                headers=user1["headers"]
            )
            
            print(f"🚫 Upload oversized file: {response.status_code}")
            # 413 is correct for "Request Entity Too Large" or 400
            assert response.status_code in [400, 413]
            
            if response.status_code == 400:
                error = response.json()
                assert "too large" in error["detail"].lower()
            
            print(f"✅ Oversized file rejected correctly")
    
    @pytest.mark.asyncio
    async def test_upload_to_nonexistent_chat(self):
        """Test uploading to a chat that doesn't exist"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            user = await create_test_user(client, "orphan_uploader")
            
            audio_content = b"audio data " * 50
            audio_file = io.BytesIO(audio_content)
            
            response = await client.post(
                "/api/media/upload-voice",
                files={"file": ("voice.mp3", audio_file, "audio/mpeg")},
                data={"chat_id": "nonexistent-chat-id"},
                headers=user["headers"]
            )
            
            print(f"\n🚫 Upload to nonexistent chat: {response.status_code}")
            assert response.status_code == 404
            
            print(f"✅ Nonexistent chat handled correctly")
    
    @pytest.mark.asyncio
    async def test_upload_to_unauthorized_chat(self):
        """Test uploading to a chat where user is not a participant"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            user1 = await create_test_user(client, "outsider")
            user2 = await create_test_user(client, "chat_owner1")
            user3 = await create_test_user(client, "chat_owner2")
            
            await establish_friendship(client, user2, user3)
            chat = await create_direct_chat(client, user2, user3)
            
            # user1 tries to upload to user2-user3 chat
            audio_content = b"audio " * 50
            audio_file = io.BytesIO(audio_content)
            
            response = await client.post(
                "/api/media/upload-voice",
                files={"file": ("voice.mp3", audio_file, "audio/mpeg")},
                data={"chat_id": chat["id"]},
                headers=user1["headers"]
            )
            
            print(f"\n🚫 Upload to unauthorized chat: {response.status_code}")
            assert response.status_code == 403
            
            error = response.json()
            assert "not a participant" in error["detail"].lower()
            
            print(f"✅ Unauthorized upload blocked correctly")


class TestMediaInMessages:
    """Test sending different media types in messages"""
    
    @pytest.mark.asyncio
    async def test_send_image_message(self):
        """Test sending an image message"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            user1 = await create_test_user(client, "img_sender")
            user2 = await create_test_user(client, "img_receiver")
            
            await establish_friendship(client, user1, user2)
            chat = await create_direct_chat(client, user1, user2)
            
            # Send image message (with fake media_url)
            response = await client.post(
                f"/api/chats/{chat['id']}/messages",
                json={
                    "chat_id": chat["id"],
                    "sender_id": user1["user"]["id"],
                    "content": "Check this out!",
                    "message_type": "image",
                    "media_url": "data:image/jpeg;base64,fakebase64data"
                },
                headers=user1["headers"]
            )
            
            print(f"\n📷 Send image message: {response.status_code}")
            assert response.status_code == 200
            
            message = response.json()
            assert message["message_type"] == "image"
            assert message["media_url"] is not None
            
            print(f"✅ Image message sent successfully")
    
    @pytest.mark.asyncio
    async def test_send_video_message(self):
        """Test sending a video message"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            user1 = await create_test_user(client, "vid_sender")
            user2 = await create_test_user(client, "vid_receiver")
            
            await establish_friendship(client, user1, user2)
            chat = await create_direct_chat(client, user1, user2)
            
            # Send video message
            response = await client.post(
                f"/api/chats/{chat['id']}/messages",
                json={
                    "chat_id": chat["id"],
                    "sender_id": user1["user"]["id"],
                    "content": "Video message",
                    "message_type": "video",
                    "media_url": "data:video/mp4;base64,fakevideo"
                },
                headers=user1["headers"]
            )
            
            print(f"\n🎥 Send video message: {response.status_code}")
            assert response.status_code == 200
            
            message = response.json()
            assert message["message_type"] == "video"
            
            print(f"✅ Video message sent successfully")
    
    @pytest.mark.asyncio
    async def test_send_file_message(self):
        """Test sending a file attachment"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            user1 = await create_test_user(client, "file_sender")
            user2 = await create_test_user(client, "file_receiver")
            
            await establish_friendship(client, user1, user2)
            chat = await create_direct_chat(client, user1, user2)
            
            # Send file message
            response = await client.post(
                f"/api/chats/{chat['id']}/messages",
                json={
                    "chat_id": chat["id"],
                    "sender_id": user1["user"]["id"],
                    "content": "document.pdf",
                    "message_type": "file",
                    "media_url": "data:application/pdf;base64,fakepdf",
                    "file_name": "document.pdf",
                    "file_size": 1024
                },
                headers=user1["headers"]
            )
            
            print(f"\n📎 Send file message: {response.status_code}")
            assert response.status_code == 200
            
            message = response.json()
            assert message["message_type"] == "file"
            assert message["file_name"] == "document.pdf"
            
            print(f"✅ File message sent successfully")
    
    @pytest.mark.asyncio
    async def test_retrieve_messages_with_media(self):
        """Test retrieving messages that contain media"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            user1 = await create_test_user(client, "media_retriever1")
            user2 = await create_test_user(client, "media_retriever2")
            
            await establish_friendship(client, user1, user2)
            chat = await create_direct_chat(client, user1, user2)
            
            # Send multiple media messages
            await send_message(client, user1, chat["id"], "Text message", "text")
            
            await client.post(
                f"/api/chats/{chat['id']}/messages",
                json={
                    "chat_id": chat["id"],
                    "sender_id": user1["user"]["id"],
                    "content": "Image",
                    "message_type": "image",
                    "media_url": "data:image/jpeg;base64,img"
                },
                headers=user1["headers"]
            )
            
            await client.post(
                f"/api/chats/{chat['id']}/messages",
                json={
                    "chat_id": chat["id"],
                    "sender_id": user1["user"]["id"],
                    "content": "Voice",
                    "message_type": "voice",
                    "media_url": "data:audio/mpeg;base64,voice"
                },
                headers=user1["headers"]
            )
            
            print(f"\n💬 Sent 3 messages (text, image, voice)")
            
            # Retrieve messages
            response = await client.get(
                f"/api/chats/{chat['id']}/messages",
                headers=user1["headers"]
            )
            
            print(f"📥 Get messages: {response.status_code}")
            assert response.status_code == 200
            
            messages = response.json()
            assert len(messages) >= 3
            
            # Check message types
            message_types = [m["message_type"] for m in messages]
            assert "text" in message_types
            assert "image" in message_types
            assert "voice" in message_types
            
            print(f"✅ Retrieved {len(messages)} messages with different media types")


class TestGroupMediaSharing:
    """Test media sharing in group chats"""
    
    @pytest.mark.asyncio
    async def test_voice_in_group_chat(self):
        """Test sending voice messages in a group chat"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            admin = await create_test_user(client, "group_voice_admin")
            member1 = await create_test_user(client, "group_voice_member1")
            member2 = await create_test_user(client, "group_voice_member2")
            
            # Create group
            group = await create_group_chat(client, admin, [member1, member2], "Voice Group")
            
            # Upload voice message
            audio_content = b"group voice " * 100
            audio_file = io.BytesIO(audio_content)
            
            upload_response = await client.post(
                "/api/media/upload-voice",
                files={"file": ("voice.mp3", audio_file, "audio/mpeg")},
                data={"chat_id": group["id"]},
                headers=member1["headers"]
            )
            
            print(f"\n🎤 Member uploads voice to group: {upload_response.status_code}")
            assert upload_response.status_code == 200
            
            media_data = upload_response.json()
            
            # Send voice message to group
            message_response = await client.post(
                f"/api/chats/{group['id']}/messages",
                json={
                    "chat_id": group["id"],
                    "sender_id": member1["user"]["id"],
                    "content": "Group voice message",
                    "message_type": "voice",
                    "media_url": media_data["media_url"]
                },
                headers=member1["headers"]
            )
            
            print(f"💬 Send voice to group: {message_response.status_code}")
            assert message_response.status_code == 200
            
            print(f"✅ Voice message sent to group successfully")
    
    @pytest.mark.asyncio
    async def test_multiple_members_upload_media(self):
        """Test multiple group members uploading media"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            admin = await create_test_user(client, "multi_media_admin")
            member1 = await create_test_user(client, "multi_media_member1")
            member2 = await create_test_user(client, "multi_media_member2")
            
            group = await create_group_chat(client, admin, [member1, member2], "Media Share")
            
            print(f"\n👥 Multiple members uploading to group...")
            
            # Each member uploads
            for i, member in enumerate([admin, member1, member2], 1):
                audio_content = f"audio{i} ".encode() * 50
                audio_file = io.BytesIO(audio_content)
                
                response = await client.post(
                    "/api/media/upload-voice",
                    files={"file": (f"voice{i}.mp3", audio_file, "audio/mpeg")},
                    data={"chat_id": group["id"]},
                    headers=member["headers"]
                )
                
                print(f"   Member {i}: {response.status_code}")
                assert response.status_code == 200
            
            print(f"✅ All group members can upload media")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
