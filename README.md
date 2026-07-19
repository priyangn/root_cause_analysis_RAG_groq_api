# CauseSense AI — Root Cause Analysis RAG Platform

AI-powered root cause intelligence platform for machine failure analysis.

**Live site:** [https://causesenseai.com](https://causesenseai.com)

## Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 19, Tailwind CSS, Recharts |
| Backend | Python FastAPI, Motor (MongoDB) |
| AI/ML | Groq (Llama 3.3 70B), LangGraph, scikit-learn, XGBoost, SHAP |
| Database | MongoDB |
| Vector DB | ChromaDB |

## Quick Start (Docker — recommended)

```bash
# 1. Copy environment file and add your Groq API key
cp .env.example .env
# Edit .env — set GROQ_API_KEY and SECRET_KEY

# 2. Build and run all services
docker compose up -d --build

# 3. Open the app
# http://localhost/login
```

## Local Development

### Backend

```bash
cd backend
cp .env.example .env   # configure MONGO_URL, GROQ_API_KEY
pip install -r requirements.txt
uvicorn server:app --reload --port 8001
```

### Frontend

```bash
cd frontend
cp .env.example .env   # REACT_APP_BACKEND_URL=http://localhost:8001
npm install --legacy-peer-deps
npm start
```

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description |
|----------|-------------|
| `MONGO_URL` | MongoDB connection string |
| `DB_NAME` | Database name |
| `SECRET_KEY` | JWT signing secret (change in production) |
| `CORS_ORIGINS` | Comma-separated allowed origins |
| `GROQ_API_KEY` | Groq API key (primary LLM) |
| `EMERGENT_LLM_KEY` | Optional Emergent LLM fallback |

### Frontend (`frontend/.env`)

| Variable | Description |
|----------|-------------|
| `REACT_APP_BACKEND_URL` | Backend URL. Leave empty in production (nginx proxies `/api`) |

## Deploy to causesenseai.com (free — no VPS payment)

**Recommended:** [Render](https://render.com) + [MongoDB Atlas](https://www.mongodb.com/atlas) free tiers.  
See [DEPLOYMENT.md](./DEPLOYMENT.md) for the full guide (Atlas → GitHub → Render → Cloudflare DNS).

DigitalOcean is optional and paid; use it only if free Render RAM is too small for ML analysis.

## API Endpoints

- `POST /api/auth/register` — Register
- `POST /api/auth/login` — Login
- `POST /api/upload` — Upload CSV/PDF/Excel
- `POST /api/analysis/start` — Start RCA pipeline
- `POST /api/chat` — AI chat assistant
- `GET /api/health` — Health check
