# ChatApp Test Suite

Comprehensive test suite for the ChatApp backend, covering authentication, database operations, API endpoints, real-time messaging, and integration workflows.

## 📁 Test Structure

```
tests/
├── conftest.py              # Test configuration and fixtures
├── test_auth.py             # Authentication and JWT tests
├── test_database.py         # Database operation tests
├── test_api_routes.py       # REST API endpoint tests
├── test_socketio.py         # Socket.IO and real-time messaging tests
├── test_integration.py      # End-to-end integration tests
├── run_tests.py            # Test runner script
├── test_requirements.txt   # Test dependencies
└── README.md               # This file
```

## 🧪 Test Categories

### Unit Tests
- **Authentication** (`test_auth.py`)
  - Password hashing and verification
  - JWT token creation and validation
  - User registration and login
  - Token expiration handling
  - Input validation

- **Database Operations** (`test_database.py`)
  - Database connection and disconnection
  - User CRUD operations
  - Message creation and retrieval
  - Chat room management
  - Error handling

### API Tests (`test_api_routes.py`)
- **Authentication Routes** (`/api/auth/`)
  - User registration endpoint
  - User login endpoint
  - Token validation
  - Error responses

- **User Routes** (`/api/users/`)
  - Profile management
  - Contacts retrieval
  - Authorization middleware
  - Profile updates

- **Chat Routes** (`/api/chat/`)
  - Message sending
  - Message retrieval
  - Message read status
  - Room management

### Socket.IO Tests (`test_socketio.py`)
- **Real-time Messaging**
  - Client connection and authentication
  - Room joining and leaving
  - Message broadcasting
  - Error handling
  - Session management

### Integration Tests (`test_integration.py`)
- **Complete Workflows**
  - Registration → Login → API usage
  - Message sending → Retrieval → Read marking
  - Profile creation → Updates → Verification
  - Error recovery scenarios
  - Security validations

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Install test dependencies
pip install -r test_requirements.txt

# Or use the automated installer
python run_tests.py --install-deps
```

### 2. Run All Tests

```bash
# Run complete test suite
python run_tests.py

# Run with verbose output
python run_tests.py --verbose

# Run with coverage report
python run_tests.py --coverage
```

### 3. Run Specific Test Types

```bash
# Run only unit tests
python run_tests.py --type unit

# Run only integration tests
python run_tests.py --type integration

# Run only authentication tests
python run_tests.py --type auth

# Run only API tests
python run_tests.py --type api

# Run only Socket.IO tests
python run_tests.py --type socketio

# Run only database tests
python run_tests.py --type database
```

## 📊 Test Coverage

### Current Coverage Targets
- **Authentication**: 95%+
- **Database Operations**: 90%+
- **API Routes**: 85%+
- **Socket.IO**: 80%+
- **Overall**: 85%+

### Generate Coverage Report

```bash
# Generate HTML coverage report
python run_tests.py --coverage

# View coverage report
open htmlcov/index.html  # On macOS/Linux
start htmlcov/index.html # On Windows
```

## 🔧 Development Workflow

### Running Tests During Development

```bash
# Run tests continuously during development
pytest --watch tests/

# Run specific test file
pytest tests/test_auth.py -v

# Run specific test function
pytest tests/test_auth.py::TestAuthManager::test_login_user_success -v

# Run tests with specific markers
pytest -m "auth and not integration" -v
```

### Test Markers

Tests are marked with categories for easy filtering:

- `@pytest.mark.auth` - Authentication-related tests
- `@pytest.mark.database` - Database operation tests
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.socketio` - Socket.IO tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow-running tests

### Example: Running Only Fast Tests

```bash
pytest -m "not slow" -v
```

## 🧩 Test Fixtures

Common fixtures are defined in `conftest.py`:

- `mock_database` - Mock database for isolated testing
- `auth_manager` - AuthManager instance with mocked dependencies
- `test_user_data` - Sample user data for testing
- `valid_jwt_token` - Valid JWT token for authentication tests
- `mock_socketio_client` - Mock Socket.IO client for testing

### Using Fixtures

```python
def test_example(mock_database, test_user_data):
    # Use fixtures in your tests
    mock_database.users.find_one.return_value = test_user_data
    # ... test logic
```

## 🔍 Writing New Tests

### Test File Naming Convention
- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`

### Example Test Structure

```python
class TestNewFeature:
    """Test suite for new feature."""
    
    @pytest.fixture
    def setup_data(self):
        """Setup data for tests."""
        return {"example": "data"}
    
    @pytest.mark.auth
    async def test_feature_success(self, setup_data):
        """Test successful feature operation."""
        # Arrange
        # Act
        # Assert
        pass
    
    @pytest.mark.auth
    async def test_feature_failure(self, setup_data):
        """Test feature error handling."""
        # Arrange
        # Act
        # Assert
        pass
```

## 🐛 Debugging Tests

### Run Tests with Debugging

```bash
# Run with Python debugger
pytest --pdb tests/test_auth.py

# Run with detailed output
pytest tests/test_auth.py -v -s --tb=long

# Run single test with debugging
pytest tests/test_auth.py::TestAuthManager::test_login_user_success --pdb
```

### Common Debugging Tips

1. **Use print statements** in tests for debugging
2. **Mock external dependencies** to isolate functionality
3. **Check fixture setup** if tests fail unexpectedly
4. **Verify async/await** usage in async tests
5. **Check import paths** for backend modules

## 📈 Performance Testing

### Load Testing Endpoints

```python
def test_api_performance(client):
    """Test API performance under load."""
    import time
    
    start_time = time.time()
    responses = []
    
    for i in range(100):
        response = client.get("/api/users/contacts")
        responses.append(response)
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Assert performance requirements
    assert duration < 10.0  # All 100 requests under 10 seconds
    assert all(r.status_code == 200 for r in responses)
```

## 🔐 Security Testing

### Testing Authentication Security

```python
def test_token_security(client):
    """Test JWT token security."""
    # Test with malformed tokens
    malformed_tokens = [
        "invalid.token.format",
        "Bearer fake_token",
        "malicious_token_injection"
    ]
    
    for token in malformed_tokens:
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/users/profile", headers=headers)
        assert response.status_code == 401
```

## 🚨 Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Add backend to Python path
   export PYTHONPATH="${PYTHONPATH}:$(pwd)/backend"
   ```

2. **Async Test Issues**
   ```python
   # Ensure proper async test decoration
   @pytest.mark.asyncio
   async def test_async_function():
       await some_async_operation()
   ```

3. **Mock Issues**
   ```python
   # Patch the correct import path
   @patch('backend.routes_auth.auth_manager')  # Correct
   # Not @patch('auth_manager')  # Incorrect
   ```

4. **Database Connection Errors**
   - Tests should use mocked database connections
   - Avoid real database connections in unit tests

### Getting Help

1. Check test output for detailed error messages
2. Run tests with `-v` flag for verbose output
3. Use `--tb=long` for detailed tracebacks
4. Check fixture definitions in `conftest.py`

## 📝 Test Reports

### Generate Test Documentation

```bash
# Generate comprehensive test report
python run_tests.py --report

# This creates TEST_REPORT.md with detailed information
```

### Continuous Integration

Example GitHub Actions workflow:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r tests/test_requirements.txt
    
    - name: Run tests
      run: |
        python tests/run_tests.py --coverage
    
    - name: Upload coverage
      uses: codecov/codecov-action@v1
```

## ✅ Best Practices

1. **Write tests before or alongside code** (TDD approach)
2. **Mock external dependencies** (database, APIs, etc.)
3. **Use descriptive test names** that explain what is being tested
4. **Test both success and failure scenarios**
5. **Keep tests independent** - no shared state between tests
6. **Use appropriate assertions** with clear error messages
7. **Group related tests** in test classes
8. **Use fixtures** for common test data and setup
9. **Test edge cases** and error conditions
10. **Keep tests fast** - unit tests should run in milliseconds

---

## 📞 Support

For questions about the test suite:

1. Check this README for common solutions
2. Review test output for specific error details
3. Check the test files for examples
4. Ensure all dependencies are installed correctly

Happy testing! 🧪✨