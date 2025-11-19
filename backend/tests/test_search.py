"""
Comprehensive tests for Search API
Tests user search, global search (chats), filters, pagination, and blocked users
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient

from helpers import (
    BASE_URL,
    create_test_user,
    establish_friendship,
    create_group_chat,
    create_channel
)


class TestUserSearch:
    """Test user search functionality"""
    
    @pytest.mark.asyncio
    async def test_search_users_by_username(self):
        """Test searching users by username"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            searcher = await create_test_user(client, "searcher")
            target1 = await create_test_user(client, "alice_smith")
            target2 = await create_test_user(client, "alice_jones")
            other = await create_test_user(client, "bob_wilson")
            
            # Search for "alice"
            response = await client.get(
                "/api/users/search",
                params={"q": "alice"},
                headers=searcher["headers"]
            )
            
            print(f"\n🔍 Search 'alice': {response.status_code}")
            assert response.status_code == 200
            
            results = response.json()
            print(f"   Found {len(results)} users")
            
            # Should find both alice users
            assert len(results) >= 2
            usernames = [u["username"] for u in results]
            assert target1["username"] in usernames
            assert target2["username"] in usernames
            assert other["username"] not in usernames
            print(f"✅ Found correct users: {usernames}")
    
    @pytest.mark.asyncio
    async def test_search_users_by_display_name(self):
        """Test searching users by display name"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            searcher = await create_test_user(client, "searcher2")
            
            # Create user with specific display name
            import random, time
            username = f"testuser_target_{random.randint(10000, 99999)}_{int(time.time() * 1000)}"
            response = await client.post(
                f"{BASE_URL}/api/auth/register",
                json={
                    "username": username,
                    "display_name": "John Developer",
                    "phone_number": f"+1555{random.randint(1000000, 9999999)}",
                    "password": "TestPass123!@#"
                }
            )
            assert response.status_code == 200
            
            # Search by display name
            response = await client.get(
                "/api/users/search",
                params={"q": "Developer"},
                headers=searcher["headers"]
            )
            
            print(f"\n🔍 Search by display name 'Developer': {response.status_code}")
            assert response.status_code == 200
            
            results = response.json()
            print(f"   Found {len(results)} users")
            
            # Should find the user with "Developer" in display name
            display_names = [u["display_name"] for u in results]
            assert "John Developer" in display_names
            print(f"✅ Found user by display name")
    
    @pytest.mark.asyncio
    async def test_search_excludes_current_user(self):
        """Test that search results don't include the searcher"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            searcher = await create_test_user(client, "searchme")
            other = await create_test_user(client, "other_user")
            
            # Search with a broad query
            response = await client.get(
                "/api/users/search",
                params={"q": "test"},
                headers=searcher["headers"]
            )
            
            print(f"\n🔍 Search excludes self: {response.status_code}")
            assert response.status_code == 200
            
            results = response.json()
            user_ids = [u["id"] for u in results]
            
            # Current user should NOT be in results
            assert searcher["user"]["id"] not in user_ids
            print(f"✅ Current user excluded from search results")
    
    @pytest.mark.asyncio
    async def test_search_excludes_blocked_users(self):
        """Test that search excludes users blocked by searcher"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            searcher = await create_test_user(client, "blocker")
            blocked = await create_test_user(client, "blocked_user")
            normal = await create_test_user(client, "normal_user")
            
            # Block the user
            response = await client.post(
                f"/api/friends/block/{blocked['user']['id']}",
                headers=searcher["headers"]
            )
            assert response.status_code == 200
            print(f"\n🚫 Blocked user: {blocked['username']}")
            
            # Search
            response = await client.get(
                "/api/users/search",
                params={"q": "test"},
                headers=searcher["headers"]
            )
            
            print(f"🔍 Search after blocking: {response.status_code}")
            assert response.status_code == 200
            
            results = response.json()
            user_ids = [u["id"] for u in results]
            
            # Blocked user should NOT be in results
            assert blocked["user"]["id"] not in user_ids
            print(f"✅ Blocked user excluded from search results")
    
    @pytest.mark.asyncio
    async def test_search_excludes_users_who_blocked_searcher(self):
        """Test that search excludes users who blocked the searcher"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            searcher = await create_test_user(client, "victim")
            blocker = await create_test_user(client, "blocker2")
            
            # Other user blocks searcher
            response = await client.post(
                f"/api/friends/block/{searcher['user']['id']}",
                headers=blocker["headers"]
            )
            assert response.status_code == 200
            print(f"\n🚫 User {blocker['username']} blocked searcher")
            
            # Searcher tries to search
            response = await client.get(
                "/api/users/search",
                params={"q": blocker['username']},
                headers=searcher["headers"]
            )
            
            print(f"🔍 Search for blocker: {response.status_code}")
            assert response.status_code == 200
            
            results = response.json()
            usernames = [u["username"] for u in results]
            
            # Blocker should NOT be in results
            assert blocker["username"] not in usernames
            print(f"✅ User who blocked searcher excluded from results")
    
    @pytest.mark.asyncio
    async def test_search_pagination_limit(self):
        """Test that search results are limited (max 20)"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            searcher = await create_test_user(client, "paginator")
            
            # Search with broad query
            response = await client.get(
                "/api/users/search",
                params={"q": "test"},
                headers=searcher["headers"]
            )
            
            print(f"\n🔍 Search pagination: {response.status_code}")
            assert response.status_code == 200
            
            results = response.json()
            print(f"   Found {len(results)} users")
            
            # Should be limited to 20 results
            assert len(results) <= 20
            print(f"✅ Results limited to {len(results)} (max 20)")


class TestGlobalSearch:
    """Test global search (users + chats)"""
    
    @pytest.mark.asyncio
    async def test_global_search_finds_users(self):
        """Test that global search finds users"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            searcher = await create_test_user(client, "global_searcher")
            target = await create_test_user(client, "findme_user")
            
            # Global search
            response = await client.get(
                "/api/chats/search",
                params={"q": "findme"},
                headers=searcher["headers"]
            )
            
            print(f"\n🌐 Global search for 'findme': {response.status_code}")
            assert response.status_code == 200
            
            results = response.json()
            print(f"   Found {len(results)} results")
            
            # Should find the user
            user_results = [r for r in results if r["type"] == "user"]
            assert len(user_results) > 0
            print(f"✅ Found {len(user_results)} user(s) in global search")
    
    @pytest.mark.asyncio
    async def test_global_search_finds_public_groups(self):
        """Test that global search finds public groups"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            creator = await create_test_user(client, "group_creator2")
            searcher = await create_test_user(client, "group_searcher")
            
            # Create public group with searchable name
            group_response = await client.post(
                "/api/chats/",
                json={
                    "chat_type": "group",
                    "name": "Awesome Developers Group",
                    "description": "A group for developers",
                    "is_public": True
                },
                headers=creator["headers"]
            )
            assert group_response.status_code == 200
            print(f"\n👥 Created public group")
            
            # Global search
            response = await client.get(
                "/api/chats/search",
                params={"q": "Awesome"},
                headers=searcher["headers"]
            )
            
            print(f"🌐 Global search for 'Awesome': {response.status_code}")
            assert response.status_code == 200
            
            results = response.json()
            print(f"   Found {len(results)} results")
            
            # Should find the group
            group_results = [r for r in results if r["type"] == "group"]
            assert len(group_results) > 0
            
            group_names = [g["name"] for g in group_results]
            assert "Awesome Developers Group" in group_names
            print(f"✅ Found public group in global search")
    
    @pytest.mark.asyncio
    async def test_global_search_finds_public_channels(self):
        """Test that global search finds public channels"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            creator = await create_test_user(client, "channel_creator2")
            searcher = await create_test_user(client, "channel_searcher")
            
            # Create public channel
            channel = await create_channel(client, creator, "Tech News Channel", is_public=True)
            print(f"\n📢 Created public channel")
            
            # Global search
            response = await client.get(
                "/api/chats/search",
                params={"q": "Tech News"},
                headers=searcher["headers"]
            )
            
            print(f"🌐 Global search for 'Tech News': {response.status_code}")
            assert response.status_code == 200
            
            results = response.json()
            print(f"   Found {len(results)} results")
            
            # Should find the channel
            channel_results = [r for r in results if r["type"] == "channel"]
            assert len(channel_results) > 0
            
            channel_names = [c["name"] for c in channel_results]
            assert "Tech News Channel" in channel_names
            print(f"✅ Found public channel in global search")
    
    @pytest.mark.asyncio
    async def test_global_search_excludes_private_groups(self):
        """Test that global search doesn't show private groups to non-members"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            creator = await create_test_user(client, "private_creator")
            searcher = await create_test_user(client, "outsider")
            
            # Create PRIVATE group
            group = await create_group_chat(client, creator, [], "Secret Society")
            print(f"\n🔒 Created private group")
            
            # Outsider searches
            response = await client.get(
                "/api/chats/search",
                params={"q": "Secret"},
                headers=searcher["headers"]
            )
            
            print(f"🌐 Global search for 'Secret': {response.status_code}")
            assert response.status_code == 200
            
            results = response.json()
            print(f"   Found {len(results)} results")
            
            # Should NOT find the private group
            group_results = [r for r in results if r.get("type") == "group" and r.get("name") == "Secret Society"]
            assert len(group_results) == 0
            print(f"✅ Private group excluded from search for non-members")
    
    @pytest.mark.asyncio
    async def test_search_min_length_validation(self):
        """Test that search requires minimum query length"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            searcher = await create_test_user(client, "validator")
            
            # Try search with 1 character (should fail for global search which requires 2)
            response = await client.get(
                "/api/chats/search",
                params={"q": "a"},
                headers=searcher["headers"]
            )
            
            print(f"\n🔍 Search with 1 char: {response.status_code}")
            # Should return validation error
            assert response.status_code == 422
            print(f"✅ Search validation working (min 2 chars for global search)")
            
            # User search requires min 1 char, should work
            response = await client.get(
                "/api/users/search",
                params={"q": "a"},
                headers=searcher["headers"]
            )
            
            print(f"🔍 User search with 1 char: {response.status_code}")
            assert response.status_code == 200
            print(f"✅ User search works with 1 char")


class TestSearchFilters:
    """Test search filtering and edge cases"""
    
    @pytest.mark.asyncio
    async def test_search_case_insensitive(self):
        """Test that search is case-insensitive"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            searcher = await create_test_user(client, "case_searcher")
            target = await create_test_user(client, "CamelCase")
            
            # Search with lowercase
            response = await client.get(
                "/api/users/search",
                params={"q": "camel"},
                headers=searcher["headers"]
            )
            
            print(f"\n🔍 Case-insensitive search: {response.status_code}")
            assert response.status_code == 200
            
            results = response.json()
            usernames = [u["username"] for u in results]
            
            # Should find CamelCase with lowercase query
            assert any("camel" in u.lower() for u in usernames)
            print(f"✅ Search is case-insensitive")
    
    @pytest.mark.asyncio
    async def test_search_partial_match(self):
        """Test that search works with partial strings"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            searcher = await create_test_user(client, "partial_searcher")
            target = await create_test_user(client, "johnsmith123")
            
            # Search with partial string
            response = await client.get(
                "/api/users/search",
                params={"q": "smith"},
                headers=searcher["headers"]
            )
            
            print(f"\n🔍 Partial match search: {response.status_code}")
            assert response.status_code == 200
            
            results = response.json()
            usernames = [u["username"] for u in results]
            
            # Should find johnsmith123 with partial match
            assert any("smith" in u.lower() for u in usernames)
            print(f"✅ Partial string matching works")
    
    @pytest.mark.asyncio
    async def test_search_empty_results(self):
        """Test search with no matching results"""
        async with AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            searcher = await create_test_user(client, "empty_searcher")
            
            # Search for something that doesn't exist
            response = await client.get(
                "/api/users/search",
                params={"q": "xyzabc999nonexistent"},
                headers=searcher["headers"]
            )
            
            print(f"\n🔍 Search with no results: {response.status_code}")
            assert response.status_code == 200
            
            results = response.json()
            print(f"   Found {len(results)} users")
            
            # Should return empty array
            assert len(results) == 0
            print(f"✅ Empty results handled correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
