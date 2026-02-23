# Glial Sales Research Demo

## 🚀 Quick Start (Demo Mode)

### 1. Start the Backend (API & Autopilot)
```bash
cd backend
# Ensure virtual environment is active
source .venv/bin/activate
# Run the server
uvicorn main:app --reload
```
*Health Check:* [http://localhost:8000/docs](http://localhost:8000/docs)

### 2. Start the Frontend (Command Center)
```bash
cd frontend
# Install dependencies if needed
npm install
# Run the development server
npm run dev
```
*Access UI:* [http://localhost:3000](http://localhost:3000)

## 🔑 Key Demo Features
- **Dashboard:** View "Autopilot" stats and active leads.
- **Leads:** Click on any lead to see the "Deep Analysis" sidebar.
- **Settings:** Show the "HubSpot Integration" toggle to demonstrate the sync.

## ⚠️ Troubleshooting
- If backend fails, check `.env` for `OPENAI_API_KEY` and `DATABASE_URL`.
- If frontend fails, ensure Node.js v18+ is installed.
