# 🚀 ChatApp - Server Startup Guide

## Prerequisites

### Required Software:
- ✅ **Python 3.11+** (for backend)
- ✅ **Node.js 18+** (for frontend)
- ✅ **MongoDB** (running locally or connection string)
- ✅ **Redis** (optional, for Socket.IO scaling)

---

## 📦 Installation

### 1. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (CMD):
.\venv\Scripts\activate.bat
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install
# or
yarn install
```

---

## ⚙️ Configuration

### Backend Environment Variables

Create a `.env` file in the `backend/` directory:

```env
# MongoDB Configuration
MONGODB_URL=mongodb://localhost:27017
DB_NAME=chatapp

# JWT Configuration
SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# Server Configuration
HOST=0.0.0.0
PORT=8000

# CORS Configuration (allow frontend)
CORS_ORIGINS=["http://localhost:8081", "http://localhost:19006", "exp://192.168.1.100:8081"]

# Redis (optional, for Socket.IO scaling)
# REDIS_URL=redis://localhost:6379

# Google OAuth (optional)
# GOOGLE_CLIENT_ID=your-google-client-id
# GOOGLE_CLIENT_SECRET=your-google-client-secret
```

### Frontend Environment Variables

Create a `.env` file in the `frontend/` directory:

```env
# Backend API URL
EXPO_PUBLIC_BACKEND_URL=http://localhost:8000

# For physical device testing, use your computer's local IP:
# EXPO_PUBLIC_BACKEND_URL=http://192.168.1.100:8000
```

---

## 🚀 Starting the Servers

### Start Backend Server

#### Option 1: Using Uvicorn (Recommended for Development)

```bash
cd backend

# Make sure virtual environment is activated
# Then run:

uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

**Or with custom settings:**

```bash
# With auto-reload and logging
uvicorn server:app --reload --host 0.0.0.0 --port 8000 --log-level info

# For production (no reload):
uvicorn server:app --host 0.0.0.0 --port 8000 --workers 4
```

#### Option 2: Using Python directly

```bash
cd backend
python -m uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

**Backend will be available at:**
- API: `http://localhost:8000/api`
- Docs: `http://localhost:8000/docs` (Swagger UI)
- ReDoc: `http://localhost:8000/redoc`
- Socket.IO: `ws://localhost:8000/socket.io`

---

### Start Frontend Server

#### Option 1: Expo Development Server

```bash
cd frontend

# Start Expo development server
npm start
# or
expo start
```

This will open the Expo DevTools in your browser. You can then:
- Press `w` - Run on web browser
- Press `a` - Run on Android emulator
- Press `i` - Run on iOS simulator
- Scan QR code with Expo Go app on your phone

#### Option 2: Specific Platforms

```bash
# Web only
npm run web

# Android
npm run android

# iOS
npm run ios
```

**Frontend will be available at:**
- Web: `http://localhost:8081` or `http://localhost:19006`
- Mobile: Via Expo Go app (scan QR code)

---

## 🔥 Quick Start (Both Servers)

### Terminal 1 - Backend:
```bash
cd backend
.\venv\Scripts\Activate.ps1  # Windows PowerShell
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

### Terminal 2 - Frontend:
```bash
cd frontend
npm start
```

---

## 🧪 Testing the Setup

### 1. Check Backend Health

```bash
# Test API endpoint
curl http://localhost:8000/

# Or visit in browser:
# http://localhost:8000/docs
```

### 2. Check MongoDB Connection

```bash
# The backend logs should show:
# INFO:     Starting up ChatApp API...
# INFO:     Database indexes created successfully
```

### 3. Run Tests

```bash
cd backend
python -m pytest tests/test_message_features.py -v

# Should show: 12 passed ✅
```

---

## 🔧 Troubleshooting

### Backend Issues

**Problem: ModuleNotFoundError**
```bash
# Solution: Ensure virtual environment is activated and dependencies installed
pip install -r requirements.txt
```

**Problem: MongoDB connection failed**
```bash
# Solution: Check if MongoDB is running
# Windows:
net start MongoDB

# macOS/Linux:
sudo systemctl start mongod

# Or use MongoDB Atlas (cloud) connection string
```

**Problem: Port 8000 already in use**
```bash
# Solution: Use different port
uvicorn server:app --reload --port 8001
# Update frontend .env: EXPO_PUBLIC_BACKEND_URL=http://localhost:8001
```

### Frontend Issues

**Problem: expo-cli not found**
```bash
# Solution: Install Expo CLI globally
npm install -g expo-cli
```

**Problem: Network error connecting to backend**
```bash
# Solution 1: Check EXPO_PUBLIC_BACKEND_URL in .env
# Solution 2: For physical device, use local IP instead of localhost:
#   EXPO_PUBLIC_BACKEND_URL=http://192.168.1.100:8000

# Find your IP:
# Windows PowerShell:
ipconfig
# Look for IPv4 Address under your network adapter

# macOS/Linux:
ifconfig
# or
ip addr show
```

**Problem: Metro bundler won't start**
```bash
# Solution: Clear cache and restart
npm start -- --clear
```

---

## 📱 Development Workflow

### Typical Development Session:

1. **Start MongoDB** (if local)
2. **Start Backend** (Terminal 1)
   ```bash
   cd backend
   .\venv\Scripts\Activate.ps1
   uvicorn server:app --reload --port 8000
   ```
3. **Start Frontend** (Terminal 2)
   ```bash
   cd frontend
   npm start
   ```
4. **Test on device/emulator** (scan QR or press i/a/w)

### Hot Reload:
- ✅ Backend: Auto-reloads on file changes (--reload flag)
- ✅ Frontend: Auto-reloads in Expo

---

## 🌐 Production Deployment

### Backend (FastAPI):

```bash
# Install production server
pip install gunicorn

# Run with Gunicorn
gunicorn server:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Or with Uvicorn (production mode)
uvicorn server:app --host 0.0.0.0 --port 8000 --workers 4
```

### Frontend (React Native/Expo):

```bash
# Build for production
expo build:android
expo build:ios
expo build:web

# Or use EAS Build
eas build --platform all
```

---

## 📊 Monitoring

### Backend Logs:
```bash
# Uvicorn logs show:
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Starting up ChatApp API...
INFO:     Database indexes created successfully
INFO:     Application startup complete.
```

### API Endpoints:
- Health Check: `GET /`
- API Docs: `GET /docs`
- Auth: `POST /api/auth/register`, `POST /api/auth/login`
- Chats: `GET /api/chats`, `POST /api/chats/{id}/messages`
- Socket.IO: `ws://localhost:8000/socket.io`

---

## 🎯 Success Indicators

✅ Backend running: Visit `http://localhost:8000/docs`
✅ Frontend running: Expo DevTools opens
✅ MongoDB connected: See "Database indexes created" in logs
✅ Tests passing: `12 passed` in pytest output
✅ Socket.IO working: Real-time messages appear instantly

---

## 📞 Support

### Useful Commands:

```bash
# Backend - Check dependencies
pip list

# Backend - Run specific test
python -m pytest tests/test_message_features.py::test_send_message_with_reply -v

# Frontend - Check version
expo --version

# Frontend - Clear cache
expo start --clear

# MongoDB - Check status
mongosh
> use chatapp
> db.users.countDocuments()
```

---

## 🚀 Ready to Launch!

Both servers should now be running:
- 🟢 Backend: `http://localhost:8000`
- 🟢 Frontend: Expo DevTools

Open the Expo app on your device or press `w` for web version!

---

*Last Updated: November 9, 2025*
*ChatApp - Modern Real-time Messaging*
