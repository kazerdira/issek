import pytest
import asyncio
import socketio
import time
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
from httpx import AsyncClient

from tests.conftest import TestDataFactory


@pytest.mark.performance
class TestWebSocketPerformance:
    """Test WebSocket performance under load."""

    @pytest.mark.slow
    async def test_multiple_concurrent_connections(self):
        """Test multiple concurrent WebSocket connections."""
        num_connections = 50
        clients = []
        connection_times = []
        
        async def create_connection():
            start_time = time.time()
            client = socketio.AsyncClient()
            
            try:
                await client.connect("http://localhost:8000", socketio_path="/socket.io/")
                connection_time = time.time() - start_time
                connection_times.append(connection_time)
                return client
            except Exception as e:
                print(f"Connection failed: {e}")
                return None
        
        try:
            # Create connections concurrently
            tasks = [create_connection() for _ in range(num_connections)]
            clients = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter successful connections
            successful_clients = [c for c in clients if c is not None and hasattr(c, 'connected') and c.connected]
            
            # Should have most connections successful
            success_rate = len(successful_clients) / num_connections
            assert success_rate > 0.8, f"Success rate too low: {success_rate}"
            
            # Average connection time should be reasonable
            avg_connection_time = sum(connection_times) / len(connection_times)
            assert avg_connection_time < 1.0, f"Average connection time too slow: {avg_connection_time}s"
            
            print(f"Successfully connected {len(successful_clients)}/{num_connections} clients")
            print(f"Average connection time: {avg_connection_time:.3f}s")
            
        finally:
            # Cleanup
            for client in clients:
                if client and hasattr(client, 'connected') and client.connected:
                    await client.disconnect()

    @pytest.mark.slow  
    async def test_message_throughput(self, test_chat: Dict[str, Any], test_user: Dict[str, Any]):
        """Test message sending throughput."""
        num_messages = 100
        clients = []
        messages_received = []
        
        # Create sender and receivers
        sender = socketio.AsyncClient()
        receivers = [socketio.AsyncClient() for _ in range(5)]
        
        # Setup message reception tracking
        for receiver in receivers:
            @receiver.event
            async def new_message(data):
                messages_received.append((time.time(), data))
        
        try:
            # Connect all clients
            await sender.connect("http://localhost:8000", socketio_path="/socket.io/")
            await sender.emit("authenticate", {"token": test_user["access_token"]})
            await sender.emit("join_chat", {"chat_id": test_chat["id"]})
            
            for receiver in receivers:
                await receiver.connect("http://localhost:8000", socketio_path="/socket.io/")
                await receiver.emit("authenticate", {"token": test_user["access_token"]})
                await receiver.emit("join_chat", {"chat_id": test_chat["id"]})
            
            await asyncio.sleep(0.2)
            
            # Send messages rapidly
            start_time = time.time()
            
            for i in range(num_messages):
                message_data = {
                    "chat_id": test_chat["id"],
                    "content": f"Performance test message {i}",
                    "message_type": "text"
                }
                await sender.emit("send_message", message_data)
                
                # Small delay to prevent overwhelming
                if i % 10 == 0:
                    await asyncio.sleep(0.01)
            
            # Wait for all messages to be processed
            await asyncio.sleep(2)
            
            send_time = time.time() - start_time
            messages_per_second = num_messages / send_time
            
            print(f"Sent {num_messages} messages in {send_time:.2f}s")
            print(f"Throughput: {messages_per_second:.1f} messages/second")
            print(f"Received {len(messages_received)} message notifications")
            
            # Should achieve reasonable throughput
            assert messages_per_second > 10, f"Throughput too low: {messages_per_second}"
            
            # Should receive most messages (allowing for some loss in high load)
            expected_total = num_messages * len(receivers)
            received_rate = len(messages_received) / expected_total
            assert received_rate > 0.7, f"Message delivery rate too low: {received_rate}"
            
        finally:
            await sender.disconnect()
            for receiver in receivers:
                await receiver.disconnect()

    @pytest.mark.slow
    async def test_room_scaling(self, test_user: Dict[str, Any], test_user2: Dict[str, Any]):
        """Test performance with many users in same chat room."""
        num_users = 20
        clients = []
        
        # Create a chat for testing
        from httpx import AsyncClient
        async with AsyncClient(base_url="http://localhost:8000") as http_client:
            headers = {"Authorization": f"Bearer {test_user['access_token']}"}
            
            chat_data = {
                "name": "Load Test Chat",
                "description": "Performance testing room",
                "chat_type": "group",
                "is_public": True
            }
            
            response = await http_client.post("/api/chats", json=chat_data, headers=headers)
            chat = response.json()
        
        join_times = []
        
        async def join_chat_room(user_token):
            start_time = time.time()
            client = socketio.AsyncClient()
            
            try:
                await client.connect("http://localhost:8000", socketio_path="/socket.io/")
                await client.emit("authenticate", {"token": user_token})
                await client.emit("join_chat", {"chat_id": chat["id"]})
                
                join_time = time.time() - start_time
                join_times.append(join_time)
                return client
                
            except Exception as e:
                print(f"Failed to join chat: {e}")
                return None
        
        try:
            # Create tasks to join room concurrently
            # Use same token for simplicity (simulating same user multiple connections)
            tasks = [join_chat_room(test_user["access_token"]) for _ in range(num_users)]
            clients = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful_joins = [c for c in clients if c is not None and hasattr(c, 'connected')]
            
            # Performance metrics
            avg_join_time = sum(join_times) / len(join_times) if join_times else 0
            success_rate = len(successful_joins) / num_users
            
            print(f"Room join success rate: {success_rate:.2%}")
            print(f"Average join time: {avg_join_time:.3f}s")
            
            # Performance assertions
            assert success_rate > 0.8, f"Room join success rate too low: {success_rate}"
            assert avg_join_time < 2.0, f"Room join time too slow: {avg_join_time}s"
            
        finally:
            # Cleanup
            for client in clients:
                if client and hasattr(client, 'connected') and client.connected:
                    await client.disconnect()


@pytest.mark.performance  
class TestAPIPerformance:
    """Test REST API performance under load."""

    @pytest.mark.slow
    async def test_concurrent_api_requests(self, client: AsyncClient, test_user: Dict[str, Any]):
        """Test API performance with concurrent requests."""
        num_requests = 50
        headers = {"Authorization": f"Bearer {test_user['access_token']}"}
        
        response_times = []
        
        async def make_request():
            start_time = time.time()
            response = await client.get("/api/users/me", headers=headers)
            response_time = time.time() - start_time
            response_times.append(response_time)
            return response.status_code
        
        # Make concurrent requests
        start_time = time.time()
        tasks = [make_request() for _ in range(num_requests)]
        status_codes = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Calculate metrics
        successful_requests = sum(1 for code in status_codes if code == 200)
        success_rate = successful_requests / num_requests
        requests_per_second = num_requests / total_time
        avg_response_time = sum(response_times) / len(response_times)
        
        print(f"API Performance Metrics:")
        print(f"  Success rate: {success_rate:.2%}")
        print(f"  Requests/second: {requests_per_second:.1f}")
        print(f"  Average response time: {avg_response_time:.3f}s")
        print(f"  Total time: {total_time:.2f}s")
        
        # Performance assertions
        assert success_rate > 0.95, f"API success rate too low: {success_rate}"
        assert requests_per_second > 20, f"API throughput too low: {requests_per_second}"
        assert avg_response_time < 0.5, f"API response time too slow: {avg_response_time}s"

    @pytest.mark.slow
    async def test_bulk_message_creation(self, client: AsyncClient, test_chat: Dict[str, Any], test_user: Dict[str, Any]):
        """Test performance of bulk message creation."""
        num_messages = 100
        headers = {"Authorization": f"Bearer {test_user['access_token']}"}
        
        response_times = []
        
        async def send_message(i):
            start_time = time.time()
            message_data = {
                "content": f"Bulk test message {i}",
                "message_type": "text"
            }
            
            response = await client.post(f"/api/chats/{test_chat['id']}/messages",
                                       json=message_data, 
                                       headers=headers)
            response_time = time.time() - start_time
            response_times.append(response_time)
            return response.status_code
        
        # Send messages with limited concurrency to avoid overwhelming
        start_time = time.time()
        
        # Process in batches
        batch_size = 10
        all_status_codes = []
        
        for i in range(0, num_messages, batch_size):
            batch_tasks = [send_message(j) for j in range(i, min(i + batch_size, num_messages))]
            batch_codes = await asyncio.gather(*batch_tasks)
            all_status_codes.extend(batch_codes)
            
            # Small delay between batches
            await asyncio.sleep(0.1)
        
        total_time = time.time() - start_time
        
        # Calculate metrics
        successful_messages = sum(1 for code in all_status_codes if code == 201)
        success_rate = successful_messages / num_messages
        messages_per_second = num_messages / total_time
        avg_response_time = sum(response_times) / len(response_times)
        
        print(f"Bulk Message Performance:")
        print(f"  Success rate: {success_rate:.2%}")
        print(f"  Messages/second: {messages_per_second:.1f}")
        print(f"  Average response time: {avg_response_time:.3f}s")
        
        # Performance assertions
        assert success_rate > 0.9, f"Message creation success rate too low: {success_rate}"
        assert messages_per_second > 5, f"Message creation rate too low: {messages_per_second}"

    @pytest.mark.slow
    async def test_chat_search_performance(self, client: AsyncClient, test_user: Dict[str, Any]):
        """Test search performance with large datasets."""
        headers = {"Authorization": f"Bearer {test_user['access_token']}"}
        
        # Create multiple chats for search testing
        num_chats = 20
        
        for i in range(num_chats):
            chat_data = {
                "name": f"Search Test Chat {i}",
                "description": f"Chat for search performance testing {i}",
                "chat_type": "group",
                "is_public": True
            }
            await client.post("/api/chats", json=chat_data, headers=headers)
        
        # Test search performance
        search_times = []
        search_queries = ["test", "chat", "performance", "search", "group"]
        
        for query in search_queries:
            start_time = time.time()
            response = await client.get(f"/api/chats/search?q={query}", headers=headers)
            search_time = time.time() - start_time
            search_times.append(search_time)
            
            assert response.status_code == 200
        
        avg_search_time = sum(search_times) / len(search_times)
        
        print(f"Search Performance:")
        print(f"  Average search time: {avg_search_time:.3f}s")
        print(f"  Searched {num_chats} chats with {len(search_queries)} queries")
        
        # Search should be fast even with multiple chats
        assert avg_search_time < 1.0, f"Search too slow: {avg_search_time}s"


@pytest.mark.performance
class TestMemoryAndResources:
    """Test memory usage and resource management."""

    async def test_connection_cleanup(self):
        """Test that connections are properly cleaned up."""
        num_connections = 30
        
        # Create and immediately disconnect connections
        for i in range(num_connections):
            client = socketio.AsyncClient()
            await client.connect("http://localhost:8000", socketio_path="/socket.io/")
            await client.disconnect()
            
            # Small delay to allow cleanup
            if i % 10 == 0:
                await asyncio.sleep(0.1)
        
        # Give server time to clean up
        await asyncio.sleep(1)
        
        # Test that new connections still work
        test_client = socketio.AsyncClient()
        try:
            await test_client.connect("http://localhost:8000", socketio_path="/socket.io/")
            assert test_client.connected
        finally:
            await test_client.disconnect()

    @pytest.mark.slow
    async def test_long_running_connections(self, test_user: Dict[str, Any]):
        """Test stability of long-running connections."""
        client = socketio.AsyncClient()
        
        try:
            await client.connect("http://localhost:8000", socketio_path="/socket.io/")
            await client.emit("authenticate", {"token": test_user["access_token"]})
            
            # Keep connection alive and periodically send data
            for i in range(20):
                # Send heartbeat or small data
                await client.emit("ping", {"timestamp": time.time()})
                await asyncio.sleep(0.5)  # 10 seconds total
            
            # Connection should still be alive
            assert client.connected
            
        finally:
            await client.disconnect()

    async def test_rapid_connect_disconnect_cycles(self):
        """Test rapid connection/disconnection cycles for memory leaks."""
        num_cycles = 20
        
        for i in range(num_cycles):
            client = socketio.AsyncClient()
            
            # Rapid connect/disconnect
            await client.connect("http://localhost:8000", socketio_path="/socket.io/")
            assert client.connected
            await client.disconnect()
            assert not client.connected
            
            # Very small delay
            await asyncio.sleep(0.05)
        
        # Final test to ensure server is still responsive
        final_client = socketio.AsyncClient()
        try:
            await final_client.connect("http://localhost:8000", socketio_path="/socket.io/")
            assert final_client.connected
        finally:
            await final_client.disconnect()


@pytest.mark.performance
class TestLoadTesting:
    """Comprehensive load testing scenarios."""

    @pytest.mark.slow
    async def test_realistic_chat_simulation(self):
        """Simulate realistic chat usage patterns."""
        # This test simulates a realistic chat scenario with multiple users
        num_users = 10
        simulation_duration = 30  # seconds
        
        users = []
        clients = []
        
        # Create test users
        from httpx import AsyncClient
        async with AsyncClient(base_url="http://localhost:8000") as http_client:
            for i in range(num_users):
                user_data = TestDataFactory.create_user_data()
                response = await http_client.post("/api/auth/register", json=user_data)
                users.append(response.json())
            
            # Create a shared chat
            headers = {"Authorization": f"Bearer {users[0]['access_token']}"}
            chat_data = {
                "name": "Load Test Chat Room",
                "description": "Simulated chat room",
                "chat_type": "group", 
                "is_public": True
            }
            response = await http_client.post("/api/chats", json=chat_data, headers=headers)
            chat = response.json()
        
        messages_sent = 0
        messages_received = 0
        
        async def user_simulation(user, user_index):
            nonlocal messages_sent, messages_received
            
            client = socketio.AsyncClient()
            
            @client.event
            async def new_message(data):
                nonlocal messages_received
                messages_received += 1
            
            try:
                # Connect and join chat
                await client.connect("http://localhost:8000", socketio_path="/socket.io/")
                await client.emit("authenticate", {"token": user["access_token"]})
                await client.emit("join_chat", {"chat_id": chat["id"]})
                
                clients.append(client)
                
                start_time = time.time()
                
                # Simulate user behavior
                while time.time() - start_time < simulation_duration:
                    # Random actions
                    action = (user_index + int(time.time())) % 4
                    
                    if action == 0:  # Send message
                        await client.emit("send_message", {
                            "chat_id": chat["id"],
                            "content": f"Message from user {user_index} at {time.time():.1f}",
                            "message_type": "text"
                        })
                        messages_sent += 1
                        
                    elif action == 1:  # Typing indicator
                        await client.emit("typing_start", {"chat_id": chat["id"]})
                        await asyncio.sleep(0.1)
                        await client.emit("typing_stop", {"chat_id": chat["id"]})
                        
                    # Wait between actions (simulate human timing)
                    await asyncio.sleep(0.5 + (user_index * 0.1))
                
            except Exception as e:
                print(f"User {user_index} simulation error: {e}")
            finally:
                if client.connected:
                    await client.disconnect()
        
        try:
            # Run all user simulations concurrently
            tasks = [user_simulation(user, i) for i, user in enumerate(users)]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Calculate metrics
            total_expected_messages = messages_sent * num_users  # Each message should be received by all users
            delivery_rate = messages_received / total_expected_messages if total_expected_messages > 0 else 0
            messages_per_second = messages_sent / simulation_duration
            
            print(f"Load Test Results:")
            print(f"  Users: {num_users}")
            print(f"  Duration: {simulation_duration}s")
            print(f"  Messages sent: {messages_sent}")
            print(f"  Messages received: {messages_received}")
            print(f"  Expected total: {total_expected_messages}")
            print(f"  Delivery rate: {delivery_rate:.2%}")
            print(f"  Messages/second: {messages_per_second:.1f}")
            
            # Performance assertions
            assert messages_sent > 0, "No messages were sent during simulation"
            assert delivery_rate > 0.7, f"Message delivery rate too low: {delivery_rate:.2%}"
            
        finally:
            # Cleanup any remaining connections
            for client in clients:
                if client.connected:
                    await client.disconnect()