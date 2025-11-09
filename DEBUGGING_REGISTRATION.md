# 🔍 Registration Issue - Debugging Guide

## Problem: "Something went wrong" during registration

This error message comes from the frontend when the backend returns an error.

---

## Step-by-Step Debugging

### 1️⃣ **Check Backend is Running**

```bash
# In Terminal 1 - Start backend
cd backend
.\venv\Scripts\Activate.ps1
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Starting up ChatApp API...
INFO:     Database connection established
INFO:     Database indexes created successfully
INFO:     Application startup complete.
```

**If you see errors:**
- ❌ "No module named..." → Run `pip install -r backend/requirements.txt`
- ❌ MongoDB connection error → See step 2

---

### 2️⃣ **Check MongoDB is Running**

The most common issue is **MongoDB not running**.

#### Option A: Install & Start MongoDB Locally

**Windows:**
```bash
# Check if MongoDB is installed
mongod --version

# If not installed, download from: https://www.mongodb.com/try/download/community

# Start MongoDB service
net start MongoDB

# Or run manually
mongod --dbpath C:\data\db
```

**Check if MongoDB is accessible:**
```bash
# Try connecting (if mongosh is installed)
mongosh

# Or check the port
netstat -an | findstr 27017
```

#### Option B: Use MongoDB Atlas (Cloud - Easier!)

1. Go to https://www.mongodb.com/cloud/atlas
2. Create free account
3. Create a cluster (free M0)
4. Get connection string
5. Update `backend/.env`:
   ```env
   MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/chatapp?retryWrites=true&w=majority
   ```

---

### 3️⃣ **Check Backend Environment Variables**

Create or check `backend/.env` file:

```env
# MongoDB
MONGODB_URL=mongodb://localhost:27017
DB_NAME=chatapp

# JWT Secret
SECRET_KEY=your-super-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# CORS (important for frontend!)
CORS_ORIGINS=["http://localhost:8081", "http://localhost:19006"]
```

---

### 4️⃣ **Check Frontend Configuration**

Create or check `frontend/.env`:

```env
EXPO_PUBLIC_BACKEND_URL=http://localhost:8000
```

**If testing on physical device:**
```env
# Replace with your computer's IP address
EXPO_PUBLIC_BACKEND_URL=http://192.168.1.100:8000
```

**Find your IP:**
```bash
# Windows PowerShell
ipconfig
# Look for IPv4 Address
```

---

### 5️⃣ **Test Backend Directly**

Open browser: http://localhost:8000/docs

Try registering via Swagger UI:
1. Click on `POST /api/auth/register`
2. Click "Try it out"
3. Fill in the example data:
   ```json
   {
     "username": "testuser",
     "display_name": "Test User",
     "email": "test@example.com",
     "password": "password123"
   }
   ```
4. Click "Execute"

**Expected:** Status 200 with token
**If error:** Check the response for details

---

### 6️⃣ **Check Backend Logs**

While trying to register from frontend, watch the backend terminal for errors:

**Common errors:**

```python
# Error 1: MongoDB not running
pymongo.errors.ServerSelectionTimeoutError: localhost:27017: [Errno 10061] No connection could be made

# Solution: Start MongoDB (see step 2)
```

```python
# Error 2: Duplicate user
"detail": "Email already registered"
"detail": "Username already exists"

# Solution: Use different email/username or clear database
```

```python
# Error 3: Validation error
"detail": [{"loc": ["body", "field"], "msg": "field required"}]

# Solution: Check all required fields are sent
```

---

### 7️⃣ **Check Frontend Console Logs**

In Expo dev tools, check for:

```
Network Error
- Backend might not be running
- Wrong EXPO_PUBLIC_BACKEND_URL
- CORS issue

Status 400/422
- Validation error (missing fields)
- Duplicate username/email

Status 500
- Backend crashed (check backend logs)
```

---

## 🚀 Quick Fix Checklist

Run through these:

- [ ] Backend server is running (`uvicorn server:app --reload`)
- [ ] MongoDB is running (or using MongoDB Atlas)
- [ ] `backend/.env` exists with MONGODB_URL
- [ ] `frontend/.env` exists with EXPO_PUBLIC_BACKEND_URL
- [ ] Can access http://localhost:8000/docs in browser
- [ ] Frontend and backend can communicate (no CORS errors)
- [ ] Using unique username/email (not already registered)

---

## 🧪 Test Registration Manually

### Via curl:

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser123",
    "display_name": "Test User",
    "email": "test123@example.com",
    "password": "password123"
  }'
```

### Via Python script:

```bash
python test_registration_debug.py
```

---

## 📱 Common Issues & Solutions

### Issue: "Cannot connect to backend"
**Solution:**
- Check backend is running on port 8000
- Check firewall isn't blocking
- If on device, use computer's IP not localhost

### Issue: "CORS error"
**Solution:**
Add to `backend/server.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development only!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Issue: "MongoDB connection timeout"
**Solution:**
- Start MongoDB: `net start MongoDB`
- Or use MongoDB Atlas
- Check MONGODB_URL in .env

### Issue: "Username already exists"
**Solution:**
- Use different username
- Or clear database: `mongosh` → `use chatapp` → `db.users.deleteMany({})`

---

## 🔧 Reset Everything

If nothing works:

```bash
# 1. Stop all servers (Ctrl+C)

# 2. Clear MongoDB (if local)
mongosh
use chatapp
db.dropDatabase()
exit

# 3. Restart backend
cd backend
.\venv\Scripts\Activate.ps1
uvicorn server:app --reload --host 0.0.0.0 --port 8000

# 4. Restart frontend
cd frontend
npm start -- --clear

# 5. Try registering with fresh data
```

---

## 📞 Need More Help?

1. **Check backend logs** - Most errors show there
2. **Check frontend console** - Network errors show there
3. **Test with Swagger UI** - http://localhost:8000/docs
4. **Run debug script** - `python test_registration_debug.py`

---

**Most Common Solution:**
MongoDB isn't running! → Start it with `net start MongoDB` or use MongoDB Atlas.
