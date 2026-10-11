# 🏆 CompileX - Next-Gen Competitive Coding Platform

**CompileX** is a revolutionary multiplayer coding platform where developers battle in real-time with **AI-generated unique questions**. Every challenge is different, every match is fresh, and every question is guaranteed to be unique!

[![Live Demo](https://img.shields.io/badge/Live-Demo-success?style=for-the-badge)](https://compile-x-code-engine.vercel.app)
[![Backend API](https://img.shields.io/badge/API-Live-blue?style=for-the-badge)](https://compilex-clkm.onrender.com)
[![AI Service](https://img.shields.io/badge/AI-Service-purple?style=for-the-badge)](https://compilex-ai-service.onrender.com)

---

## 🌟 What Makes CompileX Unique?

### 🎯 **Guaranteed Unique Questions**
- **Never repeats** - Same question will NEVER appear twice
- **Infinite variety** - Can generate millions of unique coding challenges
- **Self-learning AI** - Tracks generated questions and adapts
- **Title variations** - Each question template has 5+ different titles
- **Dual-layer deduplication** - Hash-based + title tracking

### ⚡ **Real-Time Multiplayer**
- Live coding battles with WebSocket synchronization
- Real-time leaderboards and progress tracking
- Multiple rounds with questions per round
- Instant feedback and test case results

### 🤖 **Advanced AI System**
- **Dynamic Question Generator** - Creates unique problems on-the-fly
- **Smart Debugger** - AI-powered hints and debugging assistance
- **Adaptive Difficulty** - Easy, Medium, Hard with proper constraints
- **Multiple Topics** - Arrays, Strings, Trees, Graphs, DP, and more

### 🔒 **Secure Code Execution**
- Isolated Docker containers for each submission
- Support for Python, C++, Java, JavaScript
- Memory and CPU limits for safety
- 10-second timeout protection

---

## 🚀 Live Demo

| Service | URL | Status |
|---------|-----|--------|
| **Frontend** | [compile-x-code-engine.vercel.app](https://compile-x-code-engine.vercel.app) | ✅ Live |
| **Backend API** | [compilex-clkm.onrender.com](https://compilex-clkm.onrender.com) | ✅ Live |
| **AI Service** | [compilex-ai-service.onrender.com](https://compilex-ai-service.onrender.com) | ✅ Live |

---

## ✨ Key Features

### 🎮 **Gameplay**
- ✅ Real-time multiplayer coding battles
- ✅ Create/join lobbies with custom settings
- ✅ Multiple rounds with configurable questions per round
- ✅ Live leaderboards and scoring
- ✅ Custom input testing for debugging
- ✅ Syntax highlighting and code editor

### 🧠 **AI-Powered**
- ✅ **Unique question generation** - Never repeats
- ✅ **Dynamic test cases** - Computed on-the-fly
- ✅ **Smart debugger** - Context-aware hints
- ✅ **Adaptive difficulty** - Scales with player skill
- ✅ **Topic variety** - 15+ coding topics

### 🔐 **Authentication & Security**
- ✅ JWT-based authentication
- ✅ OAuth (Google, GitHub)
- ✅ Password reset via email
- ✅ Secure session management
- ✅ Rate limiting (1000 requests/min)

### 📊 **Code Execution**
- ✅ Multi-language support (Python, C++, Java, JS)
- ✅ Docker-based sandboxing
- ✅ Real-time test case validation
- ✅ Memory and CPU limits
- ✅ Detailed error messages

### 🎬 **AI Explainer Videos**
- ✅ **Learn More section** - name any coding topic on the landing page
- ✅ **Narrated video** - hook, real-world intuition, mechanism, code trace, summary
- ✅ **Animated code execution** - variables, arrays and call stacks walked line by line
- ✅ **Built with Claude + Manim** - see [`videogen/`](videogen/README.md)

### 🎨 **User Experience**
- ✅ Modern, responsive UI
- ✅ Light and dark themes
- ✅ Real-time updates via WebSocket
- ✅ Visual diagrams for tree/graph problems
- ✅ Syntax highlighting
- ✅ Custom input testing

---

## 🛠️ Tech Stack

### **Frontend**
```
React 18 + Vite
├── Socket.IO Client (Real-time)
├── Axios (API requests)
├── Monaco Editor (Code editing)
└── Tailwind CSS (Styling)
```

### **Backend**
```
FastAPI (Python 3.10+)
├── SQLAlchemy (async ORM)
├── Socket.IO (WebSocket)
├── Docker SDK (Code execution)
├── JWT Authentication
└── SMTP Email Service
```

### **AI Service**
```
Dynamic Question Generator
├── UUID-based uniqueness
├── Hash deduplication
├── Title variation system
├── Recent title tracking
└── 50+ question templates
```

### **Infrastructure**
- **Frontend:** Vercel (Edge Network)
- **Backend:** Render (Free Tier)
- **AI Service:** Render (Free Tier)
- **Database:** SQLite (Portable)
- **Code Execution:** Docker

---

## 🎯 How It Works

### **Question Generation Flow**

```
User clicks "Generate Question"
         ↓
AI Service generates with UUID seed
         ↓
Apply random title variation (1 of 5+)
         ↓
Compute SHA256 hash of content
         ↓
Check 1: Hash exists? → Reject & retry
Check 2: Title recently used? → Reject & retry
         ↓
Both checks pass → Accept!
         ↓
Track hash + title
         ↓
Return unique question to user
```

### **Code Execution Flow**

```
User submits code
         ↓
Backend creates Docker container
         ↓
Copy code + test cases to container
         ↓
Compile (if needed)
         ↓
Run against each test case
         ↓
Compare output (line-by-line)
         ↓
Return results + score
         ↓
Update leaderboard
```

---

## 📦 Quick Start

### **Prerequisites**
- Python 3.10+
- Node.js 18+
- Git
- Docker Desktop (optional locally — only needed for sandboxed code execution)

### **1. Clone Repository**
```bash
git clone https://github.com/Sayan59das/CompileX.git
cd CompileX
```

### **2. Install Dependencies**
```bash
py -3.10 -m venv .venv
.venv\Scripts\python -m pip install -r backend\requirements.txt -r question-service\requirements.txt

cd frontend && npm install && cd ..
```

### **3. Setup Environment**
```bash
copy backend\.env.example backend\.env
```
Then set `SECRET_KEY` in `backend\.env` (generate one with
`python -c "import secrets; print(secrets.token_hex(32))"`).

The frontend needs no env file for local development — Vite proxies
`/api` and `/socket.io` to the backend on port 8000.

### **4. Run Everything**
```bash
scripts\start.bat
```

To wipe the database and start fresh: `scripts\reset-db.bat`

This starts:
- ✅ Backend API → `http://localhost:8000`
- ✅ Question Service → `http://localhost:8001`
- ✅ Frontend → `http://localhost:5173`

### **5. Access Application**
Open browser: `http://localhost:5173`

### **6. Explainer videos (optional)**

The landing page's **Learn More** section generates a narrated explainer video
for any coding topic. Without the setup below the section still loads and
explains what is missing; the rest of the app is unaffected.

The renderer needs manim, manim-voiceover and ffmpeg, which the API server does
not, so it gets its own interpreter:

```bash
py -3.11 -m venv videogen\.venv
videogen\.venv\Scripts\python -m pip install -r videogen\requirements.txt
winget install Gyan.FFmpeg
```

Then in `backend\.env`:

```env
ANTHROPIC_API_KEY=sk-ant-...
VIDEOGEN_PYTHON=E:/CompileX/videogen/.venv/Scripts/python.exe
```

Restart the backend — settings are cached, so a running server will not pick the
key up. A cold render takes several minutes and spends API credits, so finished
videos are cached on disk, one render runs at a time, and each visitor is capped
at `VIDEOGEN_RATE_LIMIT_PER_HOUR` (default 3).

To render without the web app — faster to debug, and anything it produces shows
up in the Learn More section automatically:

```bash
cd videogen
.venv\Scripts\python generator.py "hash tables"
```

See [`videogen/README.md`](videogen/README.md) for the pipeline and its options.

---

## 🌐 Deployment

### **Frontend (Vercel)**

1. **Import from GitHub**
2. **Configure:**
   - Root Directory: `frontend`
   - Build Command: `npm run build`
   - Output Directory: `dist`
3. **Environment Variables:**
   ```
   VITE_API_URL=https://your-backend.onrender.com/api/v1
   VITE_SOCKET_URL=https://your-backend.onrender.com
   ```

### **Backend (Render)**

1. **Create Web Service**
2. **Configure:**
   - Root Directory: `backend`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. **Environment Variables:** (see `backend/.env.example`)

### **AI Service (Render)**

1. **Create Web Service**
2. **Configure:**
   - Root Directory: `question-service`
   - Docker: Use `Dockerfile`
3. **Auto-deploys** from GitHub

---

## 📁 Project Structure

```
CompileX/
├── backend/                          # FastAPI API server (port 8000)
│   ├── app/
│   │   ├── api/v1/routes.py          # All REST endpoints
│   │   ├── core/config.py            # Settings (env-driven)
│   │   ├── db/database.py            # Async SQLAlchemy engine
│   │   ├── models/models.py          # ORM models
│   │   ├── schemas/schemas.py        # Pydantic schemas
│   │   ├── services/
│   │   │   ├── ai_generator.py       # Talks to question-service
│   │   │   ├── code_executor.py      # Sandboxed code execution
│   │   │   ├── elo_service.py        # Rating calculations
│   │   │   ├── lobby_manager.py      # Live lobby state
│   │   │   ├── websocket_handler.py  # Socket.IO events
│   │   │   ├── video_generator.py    # Drives videogen/ for explainer videos
│   │   │   └── email_service.py      # SMTP / password reset
│   │   └── main.py                   # App entrypoint + Socket.IO mount
│   ├── tests/
│   ├── reset_db.py                   # Drop + recreate schema
│   ├── Dockerfile
│   ├── .env.example
│   └── requirements.txt
│
├── frontend/                         # React 18 + Vite SPA (port 5173)
│   ├── src/
│   │   ├── pages/                    # Landing, Game, Lobby, Profile, ...
│   │   ├── components/               # Navbar, Leaderboard, Timer, ...
│   │   ├── context/AuthContext.jsx
│   │   ├── services/
│   │   │   ├── api.js                # Axios client
│   │   │   └── socket.js             # Socket.IO client
│   │   └── App.jsx
│   ├── Dockerfile
│   └── package.json
│
├── question-service/                 # Question generator (port 8001)
│   ├── main_dynamic.py               # Service entrypoint (production)
│   ├── model/                        # Generators, tokenizer, question DB
│   ├── data/                         # Curated question datasets
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
│
├── videogen/                         # Manim explainer-video generator
│   ├── generator.py                  # CLI: topic in, narrated video out
│   ├── lesson_plan.py                # Stage 1: Claude designs the lesson
│   ├── scene_writer.py               # Stage 2: Claude writes the Manim scene
│   ├── layout.py / theme.py          # Overlap-proof layout primitives
│   ├── plans/                        # One saved lesson design per topic
│   └── requirements.txt
│
├── scripts/
│   ├── start.bat                     # Launch all three services
│   └── reset-db.bat                  # Wipe database, then launch
│
├── docs/
│   └── ROADMAP.md                    # Planned work, prioritized
│
├── docker-compose.yml                # Full stack incl. Postgres + Redis
└── README.md
```

---

## 🎮 How to Play

### **1. Register/Login**
- Create account or use OAuth (Google/GitHub)
- Verify email for password reset

### **2. Create/Join Lobby**
- **Create:** Set difficulty, topics, rounds, time limit
- **Join:** Browse active lobbies and join

### **3. Wait for Players**
- Lobby starts when host clicks "Start"
- All players get the same question

### **4. Solve Challenge**
- Write code in your preferred language
- Run tests to validate
- Submit when ready

### **5. Compete & Win**
- First to solve gets points
- Multiple rounds for comeback chances
- Final leaderboard shows winner

---

## 🤖 AI Question System

### **Uniqueness Guarantees**

| Feature | Description |
|---------|-------------|
| **Hash Deduplication** | SHA256 hash of content prevents exact duplicates |
| **Title Tracking** | Tracks last 100 titles to prevent repetition |
| **Title Variations** | 5+ variations per template (e.g., "Two Sum" → "Find Pair with Given Sum") |
| **UUID Seeding** | Each generation uses unique seed |
| **Retry Mechanism** | Up to 50 attempts to find unique question |

### **Question Topics**

- 📊 **Arrays** - Subarray, rotation, product, missing number
- 🔤 **Strings** - Palindrome, anagram, substring, prefix
- 🌳 **Trees** - BST, traversal, depth, diameter, LCA
- 🕸️ **Graphs** - BFS, DFS, shortest path, cycle detection
- 💡 **Dynamic Programming** - Knapsack, LCS, LIS, coin change
- 📚 **Stacks/Queues** - Valid parentheses, next greater element
- 🎯 **Greedy** - Activity selection, fractional knapsack
- 🔍 **Sorting/Searching** - Merge sort, binary search

### **Statistics API**

Check AI service health:
```bash
GET https://compilex-ai-service.onrender.com/stats
```

Response:
```json
{
  "total_unique_questions": 1523,
  "recent_titles_tracked": 100,
  "max_recent_titles": 100,
  "deduplication": "active",
  "title_tracking": "active"
}
```

---

## 🔧 Configuration

### **Environment Variables**

**Backend (`backend/.env`):**
```env
# Database
DATABASE_URL=sqlite+aiosqlite:///./CompileX.db

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# AI Service
AI_SERVICE_URL=https://compilex-ai-service.onrender.com
AI_RATE_LIMIT_PER_MINUTE=1000

# Email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-secret
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-secret

# CORS
ALLOWED_ORIGINS=https://your-frontend.vercel.app
FRONTEND_URL=https://your-frontend.vercel.app
```

**Frontend (`frontend/.env.local`) — production only:**
```env
VITE_API_URL=https://your-backend.onrender.com/api/v1
VITE_SOCKET_URL=https://your-backend.onrender.com
```

---

## 📊 Performance

| Metric | Value |
|--------|-------|
| **Question Generation** | < 50ms |
| **Code Execution** | 1-3 seconds |
| **WebSocket Latency** | < 100ms |
| **API Response Time** | < 200ms |
| **Concurrent Users** | 100+ |
| **Questions Generated** | Unlimited |

---

## 🐛 Troubleshooting

### **Docker Issues**
```bash
# Check Docker is running
docker ps

# Pull required images
docker pull python:3.11-alpine
docker pull gcc:14
docker pull node:18-alpine
docker pull eclipse-temurin:17-alpine
```

### **Port Conflicts**
```bash
# Backend (8000)
netstat -ano | findstr :8000

# Frontend (5173)
netstat -ano | findstr :5173

# AI Service (8001)
netstat -ano | findstr :8001
```

### **Database Issues**
```bash
# Reset database
cd backend
rm CompileX.db
python -c "from app.db.database import init_db; import asyncio; asyncio.run(init_db())"
```

---

## 🤝 Contributing

We welcome contributions! Here's how:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details

---

## 🙏 Acknowledgments

- **FastAPI** - Modern Python web framework
- **React** - UI library
- **Socket.IO** - Real-time communication
- **Docker** - Containerization
- **Vercel** - Frontend hosting
- **Render** - Backend hosting

---

## 📞 Contact

- **GitHub:** [@Sayan59das](https://github.com/Sayan59das)
- **Live Demo:** [compile-x-code-engine.vercel.app](https://compile-x-code-engine.vercel.app)

---

<div align="center">

**Built with ❤️ for competitive programmers**

⭐ **Star this repo if you find it useful!** ⭐

</div>
