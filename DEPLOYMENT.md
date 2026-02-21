# Deployment Guide

This app can be deployed in several ways. Choose based on your hosting preference.

---

## Free & Low-Cost Hosting (Cheaper Than Render $19)

| Platform | Cost | Notes |
|----------|------|-------|
| **Render Free** | $0 | 750 hrs/month. Spins down after 15 min idle (cold start ~1 min). Use **Free** plan, not Professional. |
| **Koyeb** | $0 | 1 free web service, 512MB RAM. Docker support. No credit card. [koyeb.com](https://www.koyeb.com) |
| **Railway** | ~$0–1/mo | $5 free credit (30 days), then $1/month free credits. [railway.app](https://railway.app) |
| **Fly.io** | $5/mo min | After trial. Good if you need always-on. [fly.io](https://fly.io) — see Option 6 below |
| **PythonAnywhere** | $0 | Python-only. Build React locally, deploy Flask + static files. [pythonanywhere.com](https://www.pythonanywhere.com) |

**Tip:** On Render, create a **Web Service** (not under a paid team). The free tier is available — avoid upgrading to the $19 Professional plan unless you need team features.

---

## Option 1: Single Server (VPS, Railway, Render)

Build the React frontend, then run Flask. Flask serves both the API and the built static files.

### Steps

```bash
# 1. Install dependencies
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

cd frontend
npm install
npm run build
cd ..

# 2. Run with gunicorn (production)
gunicorn -w 2 -b 0.0.0.0:5001 "api.app:app"

# Or run with Flask dev server (development only)
python api/app.py
```

Open `http://localhost:5001`. The app serves the React build at `/` and the API at `/api`.

### Environment variables

| Variable | Description |
|---------|-------------|
| `PORT` | Server port (default: 5001) |
| `NEWSAPI_KEY` | Optional NewsAPI key for more news sources |
| `FLASK_DEBUG` | Set to `true` for debug mode |

---

## Option 2: Railway

1. Create a [Railway](https://railway.app) project and connect your repo.
2. Add a **Procfile** (or use the one below).
3. Set `PORT` (Railway sets this automatically).
4. Deploy.

**Procfile:**
```
web: cd frontend && npm run build && cd .. && gunicorn -w 2 -b 0.0.0.0:$PORT api.app:app
```

Or use a **build + start** approach:

**railway.json** (optional):
```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "cd frontend && npm run build && cd .. && gunicorn -w 2 -b 0.0.0.0:$PORT api.app:app",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

**nixpacks.toml** (if using Nixpacks):
```toml
[phases.setup]
nixPkgs = ["python312", "nodejs_20"]

[phases.install]
cmds = [
  "pip install -r requirements.txt",
  "cd frontend && npm install"
]

[phases.build]
cmds = ["cd frontend && npm run build"]

[start]
cmd = "gunicorn -w 2 -b 0.0.0.0:$PORT api.app:app"
```

---

## Option 3: Render (Free Tier)

Use the **free** Web Service — do not upgrade to the $19 Professional plan.

The repo includes `render.yaml` for one-click deploy.

### Deploy steps

1. Push your code to **GitHub**.
2. Go to [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint**.
3. Connect your GitHub repo (the one containing this project).
4. Render will detect `render.yaml` and create the web service.
5. **Select the Free instance type** (not paid).
6. Click **Apply** to deploy.
7. (Optional) Add `NEWSAPI_KEY` in **Environment** for more news sources.

Your app will be live at `https://<your-service>.onrender.com`. Free tier spins down after 15 min of inactivity.

### Manual setup (if not using Blueprint)

1. **New** → **Web Service** (not under a paid team).
2. Connect your repo.
3. **Build Command:** `pip install -r requirements.txt && cd frontend && npm install && npm run build`
4. **Start Command:** `gunicorn -w 2 -b 0.0.0.0:$PORT api.app:app`
5. Choose **Free** instance. Deploy.

---

## Option 4: Koyeb (Free, No Credit Card)

[Koyeb](https://www.koyeb.com) offers 1 free web service (512MB RAM) with Docker support.

1. Sign up at [koyeb.com](https://www.koyeb.com).
2. **Create App** → **Docker** → Connect your GitHub repo.
3. Set **Dockerfile path:** `Dockerfile`
4. Deploy. Your app will be at `https://<your-app>.koyeb.app`

No credit card required. Free tier includes scale-to-zero when idle.

---

## Option 5: Docker

**Dockerfile:**
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install Node for frontend build
RUN apt-get update && apt-get install -y nodejs npm && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App
COPY . .

# Build frontend
RUN cd frontend && npm install && npm run build && cd ..

EXPOSE 5001
ENV PORT=5001
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5001", "api.app:app"]
```

**Build and run:**
```bash
docker build -t breaking-news-sentiment .
docker run -p 5001:5001 breaking-news-sentiment
```

---

## Option 6: Fly.io

The repo includes `fly.toml` for Fly.io deployment. **Requires Fly CLI and a paid plan** ($5/mo minimum after trial).

### Install Fly CLI

```bash
# macOS/Linux
curl -L https://fly.io/install.sh | sh

# Or with Homebrew
brew install flyctl
```

### Deploy

```bash
# First time: create app and deploy (requires fly auth login)
fly launch --no-deploy   # Review fly.toml, then:
fly deploy

# Subsequent deploys
fly deploy
```

### First-time setup

1. Sign up at [fly.io](https://fly.io)
2. Run `fly auth login`
3. Run `fly launch` — it will create the app and prompt for region
4. Run `fly deploy` to build and deploy

Your app will be at `https://breaking-news-sentiment.fly.dev` (or your chosen app name).

### Optional: set secrets

```bash
fly secrets set NEWSAPI_KEY=your_key_here
```

---

## Option 7: Separate Frontend + Backend

Deploy the Flask API to one host (e.g. Railway) and the React app to another (e.g. Vercel).

1. **Backend:** Deploy `api/app.py` as above. Do **not** build the frontend. Get the API URL (e.g. `https://your-api.railway.app`).

2. **Frontend:** Set the API base URL at build time:
   ```bash
   cd frontend
   VITE_API_URL=https://your-api.railway.app npm run build
   ```
   Then update `App.jsx` to use `import.meta.env.VITE_API_URL || '/api'` for the API constant, and configure your host to use that env var.

3. **CORS:** The Flask app has CORS enabled. If your frontend is on a different domain, ensure `flask-cors` allows your frontend origin (it currently allows all with `CORS(app)`).

---

## Data persistence

The app writes to `data/` (news archive, sentiment history). For production:

- **Railway/Render:** Use a persistent disk or external storage (e.g. S3) if you need data to survive restarts.
- **Docker:** Mount a volume for `./data` if you want to persist:
  ```bash
  docker run -p 5001:5001 -v $(pwd)/data:/app/data breaking-news-sentiment
  ```

---

## Quick deploy script

```bash
#!/bin/bash
# deploy.sh - Build and run for production
set -e
cd "$(dirname "$0")"
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
echo "Build complete. Starting server..."
gunicorn -w 2 -b 0.0.0.0:${PORT:-5001} api.app:app
```
