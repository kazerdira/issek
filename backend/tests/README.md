# Backend Testing Documentation

## Overview

This document provides comprehensive information about the testing infrastructure for the chat application backend. The test suite covers REST APIs, WebSocket functionality, integration scenarios, and performance testing.

## Test Structure

```
backend/tests/
├── conftest.py                    # Test configuration and fixtures
├── requirements-test.txt          # Testing dependencies
├── pytest.ini                    # Pytest configuration
├── api/                          # REST API tests
│   ├── test_auth.py              # Authentication endpoints
│   ├── test_users.py             # User management endpoints
│   ├── test_chats.py             # Chat functionality endpoints
│   ├── test_messages.py          # Message endpoints
│   └── test_friends.py           # Friend system endpoints
├── websocket/                    # WebSocket tests
│   └── test_websocket.py         # Real-time functionality tests
├── integration/                  # End-to-end tests
│   └── test_integration.py       # Combined API + WebSocket scenarios
└── performance/                  # Performance tests
    └── test_performance.py       # Load and stress testing
```

## Setup

### 1. Install Dependencies

```bash
# Install testing dependencies
cd backend
pip install -r requirements-test.txt
```

### 2. Database Setup

The tests require a separate MongoDB test database. Ensure MongoDB is running and accessible at `mongodb://localhost:27017/`.

**Important**: Tests use a separate database (`test_chat_app`) that is automatically cleaned between test runs.

### 3. Environment Configuration

Make sure your backend server can be started on `localhost:8000` for testing. The test suite will make requests to this address.

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Specific Test Categories

```bash
# API tests only
pytest tests/api/

# WebSocket tests only  
pytest tests/websocket/

# Integration tests only
pytest tests/integration/

# Performance tests only
pytest tests/performance/
```

### Run Tests by Markers

```bash
# Unit tests only
pytest -m unit

# WebSocket tests only
pytest -m websocket  

# Integration tests only
pytest -m integration

# Performance tests only
pytest -m performance

# Exclude slow tests
pytest -m "not slow"

# Run only fast tests
pytest -m "not slow and not performance"
```

### Run Specific Test Files

```bash
# Authentication tests
pytest tests/api/test_auth.py

# WebSocket connection tests
pytest tests/websocket/test_websocket.py::TestWebSocketConnection

# Specific test function
pytest tests/api/test_auth.py::TestAuthentication::test_register_user_success
```

### Coverage Reports

```bash
# Run with coverage
pytest --cov=. --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Test Categories

### 1. API Tests (tests/api/)

**Purpose**: Test REST API endpoints for functionality, validation, and error handling.

**Coverage**:
- **Authentication** (`test_auth.py`): Registration, login, token refresh, logout
- **Users** (`test_users.py`): Profile management, search, presence status
- **Chats** (`test_chats.py`): Chat CRUD, member management, search
- **Messages** (`test_messages.py`): Sending, reactions, editing, deletion
- **Friends** (`test_friends.py`): Friend requests, blocking, relationships

**Key Features**:
- Comprehensive input validation testing
- Error scenario coverage
- Authentication and authorization testing
- Data persistence verification

### 2. WebSocket Tests (tests/websocket/)

**Purpose**: Test real-time functionality via WebSocket connections.

**Coverage**:
- **Connection Management**: Connect, disconnect, multiple connections
- **Authentication**: WebSocket token validation and security
- **Real-time Messaging**: Message broadcasting, delivery confirmation
- **Room Management**: Joining/leaving chats, room isolation
- **Presence System**: Online/offline status, typing indicators
- **Error Handling**: Malformed messages, rate limiting, reconnection

**Key Features**:
- Concurrent connection testing
- Real-time message delivery verification
- Presence and typing indicator testing
- Connection recovery scenarios

### 3. Integration Tests (tests/integration/)

**Purpose**: Test end-to-end workflows combining REST API and WebSocket functionality.

**Coverage**:
- **Complete User Flows**: Registration → Chat creation → Real-time messaging
- **Multi-user Scenarios**: Multiple users chatting simultaneously
- **Cross-platform Consistency**: REST and WebSocket data synchronization
- **Error Recovery**: Token expiration, connection recovery, state preservation

**Key Features**:
- Realistic user journey testing
- Cross-component interaction verification
- Data consistency across REST and WebSocket
- Concurrent operation testing

### 4. Performance Tests (tests/performance/)

**Purpose**: Validate system performance under load and stress conditions.

**Coverage**:
- **Connection Scaling**: Multiple concurrent WebSocket connections
- **Message Throughput**: High-volume message processing
- **API Performance**: Concurrent REST request handling
- **Resource Management**: Memory usage, connection cleanup
- **Load Simulation**: Realistic chat usage patterns

**Key Features**:
- Concurrent user simulation
- Throughput measurement
- Resource utilization monitoring
- Performance regression detection

## Test Configuration

### Pytest Configuration (pytest.ini)

```ini
[tool:pytest]
testpaths = tests
addopts = 
    --tb=short
    --cov=.
    --cov-report=term-missing
    --cov-exclude=tests/*
asyncio_mode = auto

markers =
    unit: Unit tests for individual components
    integration: Integration tests across multiple components  
    websocket: WebSocket functionality tests
    api: REST API endpoint tests
    slow: Tests that take longer to run
    performance: Performance and load tests
```

### Test Fixtures (conftest.py)

**Database Fixtures**:
- `test_db`: Isolated test database with automatic cleanup
- `clean_db`: Database cleanup between tests

**Authentication Fixtures**:
- `test_user`: Registered user with authentication token
- `test_user2`: Second user for multi-user testing

**HTTP Client Fixtures**:
- `client`: HTTP client for REST API testing
- `authenticated_client`: Pre-authenticated HTTP client

**WebSocket Fixtures**:
- `websocket_client`: WebSocket client for real-time testing

**Data Fixtures**:
- `test_chat`: Pre-created chat for testing
- `TestDataFactory`: Factory for generating test data

## Test Data Management

### TestDataFactory

The `TestDataFactory` class provides methods for generating consistent test data:

```python
# Generate user data
user_data = TestDataFactory.create_user_data()

# Generate chat data  
chat_data = TestDataFactory.create_chat_data()

# Generate message data
message_data = TestDataFactory.create_message_data()

# Generate random data
username = TestDataFactory.random_username()
email = TestDataFactory.random_email()
```

### Database Isolation

- Each test runs with a clean database state
- Test data is automatically cleaned up after each test
- Database transactions are used where possible for faster cleanup

## Common Testing Patterns

### 1. API Endpoint Testing

```python
async def test_api_endpoint(client: AsyncClient, test_user: Dict[str, Any]):
    headers = {"Authorization": f"Bearer {test_user['access_token']}"}
    
    response = await client.post("/api/endpoint", 
                               json={"data": "value"}, 
                               headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["field"] == "expected_value"
```

### 2. WebSocket Testing

```python
async def test_websocket_feature(websocket_client: socketio.AsyncClient, test_user: Dict[str, Any]):
    received_data = []
    
    @websocket_client.event
    async def event_handler(data):
        received_data.append(data)
    
    await websocket_client.connect("http://localhost:8000", socketio_path="/socket.io/")
    await websocket_client.emit("authenticate", {"token": test_user["access_token"]})
    await websocket_client.emit("action", {"data": "value"})
    
    await asyncio.sleep(0.1)  # Wait for processing
    
    assert len(received_data) > 0
    assert received_data[0]["field"] == "expected"
```

### 3. Multi-user Testing

```python
async def test_multi_user_scenario(test_user: Dict[str, Any], test_user2: Dict[str, Any]):
    client1 = socketio.AsyncClient()
    client2 = socketio.AsyncClient()
    
    try:
        # Setup both clients
        await client1.connect("http://localhost:8000")
        await client2.connect("http://localhost:8000")
        
        await client1.emit("authenticate", {"token": test_user["access_token"]})
        await client2.emit("authenticate", {"token": test_user2["access_token"]})
        
        # Test interaction between users
        # ...
        
    finally:
        await client1.disconnect()
        await client2.disconnect()
```

## Performance Testing Guidelines

### 1. Connection Limits

- Test concurrent connection limits (typically 50-100 connections)
- Verify graceful handling of connection limit exceeded
- Check connection cleanup and resource management

### 2. Message Throughput

- Test message processing under high load
- Measure messages per second capability
- Verify message delivery guarantees under stress

### 3. Resource Usage

- Monitor memory usage during long-running tests
- Check for memory leaks in connection handling
- Verify proper resource cleanup

### 4. Load Testing Best Practices

```python
@pytest.mark.performance
@pytest.mark.slow
async def test_load_scenario():
    # Use realistic timing (avoid overwhelming the system)
    # Measure and assert on specific metrics
    # Clean up resources properly
    # Use appropriate batch sizes for concurrent operations
```

## Debugging Tests

### 1. Verbose Output

```bash
# Verbose test output
pytest -v

# Show print statements
pytest -s

# Full tracebacks
pytest --tb=long
```

### 2. Running Single Tests

```bash
# Run specific test
pytest tests/api/test_auth.py::TestAuthentication::test_login_success -v -s
```

### 3. Debugging WebSocket Tests

- Add print statements in event handlers
- Use smaller timeouts for faster feedback
- Check WebSocket connection status before operations

### 4. Database State Inspection

```python
# In test, inspect database state
async def test_something(test_db):
    # Your test logic
    
    # Debug: Check database state
    collection = test_db["users"]
    users = await collection.find({}).to_list(length=None)
    print(f"Users in DB: {users}")
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Backend Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      mongodb:
        image: mongo:latest
        ports:
          - 27017:27017
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        cd backend
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Run tests
      run: |
        cd backend
        pytest --cov=. --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v1
```

## Best Practices

### 1. Test Organization

- **Group related tests** in the same test class
- **Use descriptive test names** that explain what is being tested
- **Keep tests independent** - each test should be able to run in isolation
- **Use appropriate markers** to categorize tests

### 2. Test Data

- **Use factories** for generating test data instead of hardcoded values
- **Create minimal data** needed for each test
- **Clean up data** after each test to avoid interference

### 3. Async Testing

- **Always await async operations** in tests
- **Use appropriate timeouts** for WebSocket operations
- **Handle exceptions properly** in async contexts

### 4. Performance Testing

- **Mark slow tests** with `@pytest.mark.slow`
- **Use realistic load patterns** rather than artificial stress
- **Assert on specific metrics** rather than just "doesn't crash"
- **Clean up resources** properly after load tests

### 5. Error Testing

- **Test both positive and negative scenarios**
- **Verify error messages and status codes**
- **Test edge cases and boundary conditions**
- **Check security aspects** (authorization, input validation)

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Ensure MongoDB is running on localhost:27017
   - Check that test database can be created and accessed
   - Verify no conflicts with existing data

2. **WebSocket Connection Failures**
   - Ensure backend server is running on localhost:8000
   - Check that WebSocket endpoint is accessible
   - Verify no firewall blocking connections

3. **Test Timeouts**
   - Increase asyncio.sleep() times if operations need more time
   - Check for deadlocks in concurrent operations
   - Verify proper cleanup of resources

4. **Flaky Tests**
   - Add proper waiting mechanisms instead of fixed sleeps
   - Ensure tests are truly independent
   - Check for race conditions in concurrent operations

### Debug Environment

```bash
# Run tests with maximum verbosity
pytest -vvv -s --tb=long

# Run single test with debugging
pytest tests/websocket/test_websocket.py::TestWebSocketConnection::test_socket_connection -vvv -s

# Check test discovery
pytest --collect-only
```

## Contributing

When adding new tests:

1. **Follow the existing structure** and naming conventions
2. **Add appropriate markers** for test categorization
3. **Include both positive and negative test cases**
4. **Add performance tests** for new features that handle load
5. **Update documentation** when adding new test categories
6. **Ensure tests are deterministic** and don't depend on external factors

## Test Coverage Goals

- **API Endpoints**: >95% coverage of all REST endpoints
- **WebSocket Events**: >90% coverage of real-time functionality  
- **Integration Flows**: >80% coverage of user workflows
- **Error Scenarios**: >85% coverage of error handling paths
- **Performance**: Key performance metrics under normal and peak load

Current test suite provides comprehensive coverage of:
- ✅ Authentication and authorization
- ✅ User management and profiles
- ✅ Chat creation and management
- ✅ Real-time messaging
- ✅ Friend system and relationships
- ✅ WebSocket functionality
- ✅ Integration workflows
- ✅ Performance characteristics