# UDYOGSETU - free deploy kits (no credit card required)

Two fully-free ways to host the backend. Both keep the frontend on Vercel.

- **No VM, no card, fastest**: Host the backend on a **Hugging Face Space**
  (free CPU Docker) + **Neon** PostgreSQL + **Upstash** Redis. See
  [`HUGGINGFACE_SPACES.md`](HUGGINGFACE_SPACES.md) and push with
  `./push-to-hf.sh <user>/<space>`.
- **Your own VM**: Merge everything into one free VM (e.g. Oracle Always Free)
  with persistent volumes and nightly backups. Rest of this README.

---

# UDYOGSETU - free single-VM deploy kit

Deploy the whole backend (FastAPI + PostgreSQL + Redis) on a free Ubuntu VM
(e.g. **Oracle Cloud Always Free**) with persistent volumes, and keep the
frontend on **Vercel (free)**. Total monthly cost: **$0**.

## What's here

| File | Purpose |
|---|---|
| `docker-compose.yml` | Production stack: postgres + redis + backend only (no frontend/nginx — those live on Vercel). Persistent volumes for DB, Redis, uploads. |
| `.env.example` | Template for the variables; copy to `.env` (never commit). |
| `setup-vm.sh` | Idempotent VM bootstrap: Docker, UFW (SSH + `:8000` only), clone repo, start stack, wait for `/health`. |
| `backup.sh` + `crontab.example` | Nightly `pg_dump` to `/var/backups/udyogsetu`, 7-day retention. |

## Steps

### 1. Create the VM (Oracle Cloud Always Free)
1. Sign up at https://www.oracle.com/cloud/free (card for identity only, never charged).
2. Create an instance: Ubuntu 22.04, **VM.Standard.A1.Flex**, 2 OCPU / 8 GB.
3. In the VCN security list open **22/tcp** and **8000/tcp**.
4. Note the public IP or the instance's `<instance>.oraclecloud.com` hostname.

### 2. Run the setup script
```bash
scp -r deploy ubuntu@<PUBLIC_IP>:/tmp/
ssh ubuntu@<PUBLIC_IP> 'sudo mkdir -p /opt/udyogsetu && sudo mv /tmp/deploy /opt/udyogsetu/ && sudo /opt/udyogsetu/deploy/setup-vm.sh'
```
The script clones the repo, creates `deploy/.env`, and stops for you to edit it.

### 3. Fill in `deploy/.env`
```bash
ssh ubuntu@<PUBLIC_IP>
sudo nano /opt/udyogsetu/deploy/.env
```
- `POSTGRES_PASSWORD`, `JWT_SECRET_KEY` (generate via `python3 -c "import secrets; print(secrets.token_hex(32))"`)
- `CORS_ORIGINS=["https://<your-app>.vercel.app"]`
- `ALLOWED_HOSTS=["localhost","127.0.0.1","<PUBLIC_IP>","<instance>.oraclecloud.com"]`

Then re-run: `sudo /opt/udyogsetu/deploy/setup-vm.sh` — it builds the backend
image, runs `alembic upgrade head`, starts uvicorn on `:8000`, and waits for
`/health` to report healthy.

### 4. Vercel (free)
1. Import the repo, **Root Directory**: `frontend`.
2. Environment variable `NEXT_PUBLIC_API_URL = http://<PUBLIC_IP>:8000/api` (Production + Preview).
3. Deploy, then log in at your `*.vercel.app` URL.

### 5. Verify
```bash
curl http://<PUBLIC_IP>:8000/health
# {"status":"healthy",...,"database":"ok"}
```
Browser: login (demo accounts in the README), create a project, upload a document.

## Optional: backups (still free)
```bash
ssh ubuntu@<PUBLIC_IP> 'sudo chmod +x /opt/udyogsetu/deploy/backup.sh && sudo crontab /opt/udyogsetu/deploy/crontab.example'
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `400 Bad Request` on everything | `ALLOWED_HOSTS` must include the VM public IP/hostname. |
| Browser CORS error | `CORS_ORIGINS` must exactly match the Vercel origin (scheme + host), then redeploy. |
| `JWT_SECRET_KEY must be set` | Compose fails fast — fill the `.env`, re-run the script. |
| Backend unhealthy | `docker compose -f deploy/docker-compose.yml logs backend`, and check `ufw status`. |

## Notes / limitations
- PostgreSQL + Redis + uploads live in named Docker volumes on the VM → data
  survives restarts/redeploys (unlike Railway's ephemeral disk).
- Government integrations are MOCK, AI falls back to mock unless you set
  `GEMINI_API_KEY`/`GROQ_API_KEY` (server-side), and background jobs are
  in-memory (single backend container).
- For HTTPS on the API later, add a domain + Caddy/certbot and move `:8000`
  behind it; update `ALLOWED_HOSTS`/`CORS_ORIGINS` accordingly.