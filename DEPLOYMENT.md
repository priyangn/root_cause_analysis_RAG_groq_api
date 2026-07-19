# CauseSense AI — Deployment Guide (Emergent → GitHub / free cloud)

Migrate from Emergent to **causesenseai.com** without paying for a VPS.

## Recommended free stack (no DigitalOcean payment)

```
causesenseai.com (Cloudflare DNS)
        │
        ├── Frontend  → Render Static Site (free)
        └── /api      → Render Web Service (free Docker)
                │
                └── MongoDB Atlas M0 (free)
```

| Piece | Free service | Card required? |
|-------|--------------|----------------|
| Backend API | [Render](https://render.com) Web Service | Usually **no** |
| Frontend | Render Static Site | Usually **no** |
| Database | [MongoDB Atlas](https://www.mongodb.com/atlas) M0 | Usually **no** |
| DNS / HTTPS | Cloudflare (you already use it) | No |

**Trade-offs:** Free Render services sleep after ~15 min idle (first request can take 30–60s). Free RAM is limited (~512 MB) — light auth/chat works; heavy ML analysis may need a paid bump later.

---

## Step 1 — MongoDB Atlas (free)

1. Sign up at https://www.mongodb.com/cloud/atlas (Google/GitHub OK)
2. Create a **free M0** cluster (any region close to you)
3. **Database Access** → Add user (username + password) — save the password
4. **Network Access** → Add IP Address → **Allow Access from Anywhere** (`0.0.0.0/0`) for Render
5. **Connect** → Drivers → copy connection string, e.g.  
   `mongodb+srv://USER:PASSWORD@cluster0.xxxxx.mongodb.net/causesense?retryWrites=true&w=majority`

---

## Step 2 — Push code to GitHub (required for Render)

Render deploys from GitHub. Push migration code **without** secrets (`.env` is gitignored).

Then in [Render Dashboard](https://dashboard.render.com):

1. Sign up with **GitHub**
2. **New** → **Blueprint** → select `priyangn/root_cause_analysis_RAG_groq_api`
3. Apply `render.yaml` (creates `causesense-api` + `causesense-web`)

### Env vars for `causesense-api`

| Key | Value |
|-----|--------|
| `MONGO_URL` | Atlas connection string from Step 1 |
| `DB_NAME` | `causesense` |
| `GROQ_API_KEY` | Your Groq key |
| `SECRET_KEY` | Long random string (or use Render generate) |
| `CORS_ORIGINS` | `https://causesenseai.com,https://www.causesenseai.com,https://causesense-web.onrender.com` |

### Env vars for `causesense-web` (build-time)

| Key | Value |
|-----|--------|
| `REACT_APP_BACKEND_URL` | `https://causesense-api.onrender.com` (use your real API URL after first deploy) |

Redeploy the static site after the API URL is known so the frontend builds with the correct backend.

---

## Step 3 — Point causesenseai.com (Cloudflare)

In Cloudflare DNS for `causesenseai.com`:

| Type | Name | Target |
|------|------|--------|
| CNAME | `@` | `causesense-web.onrender.com` (or use Render’s custom domain instructions) |
| CNAME | `www` | `causesense-web.onrender.com` |

Or in Render → Static site → **Custom Domains** → add `causesenseai.com` and `www`, then copy the CNAME they show into Cloudflare.

SSL: Cloudflare **Full** mode.

Remove old Emergent CNAMEs/A records.

---

## Step 4 — Verify

```bash
curl https://causesense-api.onrender.com/api/health
curl -I https://causesenseai.com/login
```

First request after sleep may be slow — wait up to a minute.

---

## Optional paid VPS (only if free tier is too small)

If ML analysis runs out of memory on Render free:

- **DigitalOcean Droplet** (~$24/mo, 4 GB) — see older Docker Compose path below
- **Oracle Cloud Always Free** (more RAM) — usually needs a card for account verify, $0 if you stay in free tier

### Docker Compose on a VPS

```bash
git clone https://github.com/priyangn/root_cause_analysis_RAG_groq_api.git ~/causesense
cd ~/causesense
cp .env.example .env   # set GROQ_API_KEY, SECRET_KEY, MONGO_URL if using Atlas
docker compose up -d --build
```

Point Cloudflare A records to the VPS IP. See `scripts/deploy-to-droplet.sh`.

---

## Environment variables reference

### Root / Render backend

```env
SECRET_KEY=<long-random-string>
GROQ_API_KEY=<your-groq-key>
MONGO_URL=mongodb+srv://...
DB_NAME=causesense
CORS_ORIGINS=https://causesenseai.com,https://www.causesenseai.com
```

### Frontend build

```env
REACT_APP_BACKEND_URL=https://causesense-api.onrender.com
```

Leave empty only when nginx proxies `/api` on the same host (Docker Compose setup).

---

## Migrating from Emergent

| Emergent | New setup |
|----------|-----------|
| `EMERGENT_LLM_KEY` | `GROQ_API_KEY` |
| Emergent preview URL | `https://causesenseai.com` |
| Emergent MongoDB | MongoDB Atlas M0 |
| Emergent supervisor | Render |
| `@emergentbase/visual-edits` | Removed |

User data from Emergent is **not** auto-migrated.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Login / CORS error | `CORS_ORIGINS` must include your domain |
| Analysis stuck / OOM | Free 512 MB too small — upgrade Render plan or use a VPS |
| 502 / spin-up delay | Free service was asleep — retry after 30–60s |
| Frontend blank API calls | Rebuild static site with correct `REACT_APP_BACKEND_URL` |
| Atlas connection failed | Network Access must allow `0.0.0.0/0`; check user/password in URI |

---

## Version

- **Version:** 1.1.0
- **Last updated:** 2026-07-20
- **Primary path:** Render + MongoDB Atlas (free)
