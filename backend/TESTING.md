# Quick Test Setup Guide

## Prerequisites

1. **MongoDB**: Ensure MongoDB is running on `localhost:27017`
2. **Python 3.9+**: Backend requires Python 3.9 or higher
3. **Backend Server**: Make sure you can start the backend on `localhost:8000`

## Installation

```bash
cd backend
pip install -r requirements-test.txt
```

## Quick Start

```bash
# Run all tests
pytest

# Run only fast tests (exclude performance tests)
pytest -m "not slow"

# Run with coverage
pytest --cov=. --cov-report=term-missing

# Run specific test category
pytest tests/api/          # REST API tests
pytest tests/websocket/    # WebSocket tests  
pytest tests/integration/  # Integration tests
pytest tests/performance/  # Performance tests (slow)
```

## Test Categories

### 🔗 API Tests
- Authentication (register, login, tokens)
- User management (profiles, search)
- Chat operations (create, manage, search) 
- Messaging (send, edit, reactions)
- Friend system (requests, blocking)

### ⚡ WebSocket Tests
- Connection management
- Real-time messaging
- Typing indicators
- User presence
- Room management

### 🔄 Integration Tests
- End-to-end user flows
- Multi-user scenarios
- Cross-platform consistency
- Error recovery

### 📊 Performance Tests
- Concurrent connections
- Message throughput
- API load testing
- Resource management

## Common Commands

```bash
# Debug specific test
pytest tests/api/test_auth.py::TestAuthentication::test_login_success -v -s

# Skip slow tests
pytest -m "not slow"

# Run with coverage report
pytest --cov=. --cov-report=html
open htmlcov/index.html

# List all tests
pytest --collect-only
```

## Troubleshooting

**Database Issues**: Ensure MongoDB is running and accessible
```bash
# Check MongoDB status
mongosh --eval "db.adminCommand('ping')"
```

**WebSocket Connection Issues**: Verify backend server is running
```bash
# Test server accessibility
curl http://localhost:8000/health
```

**Test Failures**: Run with verbose output for debugging
```bash
pytest -vvv -s --tb=long
```

For detailed documentation, see `tests/README.md`.