# UDYOGSETU on Hugging Face Spaces - free, no credit card
#
# Hosts the FastAPI backend on the HF Spaces FREE CPU plan and keeps the
# frontend on Vercel (free). Database = Neon (free), Redis = Upstash (free).
# No credit card is required anywhere.

## Architecture
```
Vercel (free) --HTTPS--> https://<user>-<space>.hf.space/api  (Spaces free CPU)
                                |-> Postgres: Neon free (DATABASE_URL)
                                |-> Redis:    Upstash free (REDIS_URL)
```

## 1. Create the Space from this repo
1. Go to https://huggingface.co/new-space
2. Name it (e.g. `udyogsetu`), SDK auto-detected as **Docker** (a root
   `Dockerfile` already exists in this repo), license whatever you like.
3. Or connect this GitHub repo directly: HF Spaces -> Create -> "use a
   template/repo"... simplest is: create an empty Docker Space, then from the
   command line push this repo's `main` branch to `https://huggingface.co/spaces/<user>/udyogsetu`:
   ```bash
   git clone https://github.com/amulya-ajay/Udyogsetu-SIH-Project-.git /tmp/udyogsetu
   cd /tmp/udyogsetu
   git remote add hf https://<USER>@huggingface.co/spaces/<USER>/udyogsetu
   git push hf main
   ```
   The root `Dockerfile` builds the backend (port 7860 is the Spaces proxy
   port; migrations run before uvicorn starts).

## 2. Set Space variables
Space -> Settings -> Variables and Secrets:

| Variable | Value |
|---|---|
| `ENVIRONMENT` | `production` |
| `DEBUG` | `false` |
| `JWT_SECRET_KEY` | `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | Neon connection string (see step 3) |
| `REDIS_URL` | Upstash connection string (see step 4) |
| `CORS_ORIGINS` | `["https://<your-app>.vercel.app"]` |
| `ALLOWED_HOSTS` | `["localhost","127.0.0.1","*.hf.space"]` |
| `UPLOAD_DIRECTORY` | `/var/uploads` (or `/tmp`) |
| `GEMINI_API_KEY` / `GROQ_API_KEY` | optional (mock fallback otherwise) |

`ALLOWED_HOSTS=*.hf.space` prevents `TrustedHostMiddleware` HTTP 400s on the
Spaces proxy. If you attach a custom domain, add it too.

## 3. Neon (free PostgreSQL, no card)
1. neon.tech -> sign in with GitHub -> New Project.
2. Create a database, copy the connection string.
3. Paste into the Space `DATABASE_URL` variable above. A plain
   `postgresql://...` value works (the backend auto-adds the asyncpg driver).

## 4. Upstash (free Redis, no card)
1. upstash.com -> sign in with GitHub -> Create Database.
2. Copy the `redis://` connection string -> the Space `REDIS_URL` variable.
3. Rate limiting now works (it fails open if Redis is ever unreachable).

## 5. Vercel (free frontend, no card)
1. Import this repo. **Root Directory**: `frontend`.
2. Environment variable `NEXT_PUBLIC_API_URL`:
   `https://<user>-<space>.hf.space/api` (Production + Preview).
3. Deploy, open your `*.vercel.app` URL, log in (demo accounts in README).

## 6. Verify
```bash
curl https://<user>-<space>.hf.space/health
# {"status":"healthy",...,"database":"ok"}
```
Then in the browser: create project -> explore -> upload -> submit -> officer/admin.

## Caveats (free tier)
- The Space **disk is ephemeral**: uploaded documents reset on the next
  build/reboot. Fine for a demo; object storage is the future fix.
- The Space sleeps after ~48h idle; first request after sleep is slower while
  it wakes.
- Government integrations are MOCK, AI falls back to mock unless you set a
  provider key (server-side only).
- Free Spaces run 1 CPU instance; background jobs are in-process (see
  `backend/app/workers/background.py`).

## Troubleshooting
| Symptom | Fix |
|---|---|
| HTTP 400 on everything | `ALLOWED_HOSTS` must include `*.hf.space` (+ your domain). |
| Browser CORS error | `CORS_ORIGINS` must exactly match the Vercel origin; then redeploy. |
| Space build fails at Docker | Check build logs; ensure the Space has a root `Dockerfile` (present in this repo). |
| Migrations on fresh DB | `alembic upgrade head` runs inside the container before uvicorn starts. |