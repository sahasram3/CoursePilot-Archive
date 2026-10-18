# Deploying CoursePilot

CoursePilot ships as **one container**: FastAPI serves both the API (`/api/*`) and the built React app. There's no
database, and the catalog is read-only JSON baked into the image. Any host that runs a Docker image works.

The image was built and verified locally: `docker build` succeeded (543 MB). The container passed the full
browser end-to-end suite and handled six concurrent double-major plan requests without errors.

## Option A: Render (blueprint included)

1. Push this repository to GitHub.
2. In Render: **New → Blueprint**, then select the repository. `render.yaml` defines a Docker web service with a
   health check on `/api/health`.
3. Deploy, and open the `*.onrender.com` URL.

The `starter` plan is recommended. The free plan works, but it sleeps when idle, so the first request after a nap
takes about a minute.

Measured under simulated free-tier limits (`docker run --cpus=0.1 --memory=512m` with the `render.yaml` settings):
about 40–60 s cold start, 5–25 s per single-major plan, and about 25 s for a double major. On that CPU budget a
double-major plan is returned unpolished: valid, but less evenly spread. The `starter` plan or a bigger host gives
faster, fully balanced plans. All 15 browser checks pass under those limits.

## Option B: Fly.io

```bash
fly launch --dockerfile Dockerfile --internal-port 8000 --no-deploy
fly scale memory 1024
fly deploy
```

## Option C: any Docker host (Railway, Cloud Run, a VM)

```bash
docker build -t coursepilot .
docker run -d -p 80:8000 --restart unless-stopped coursepilot
```

The image honors `$PORT`, which Cloud Run and Railway set automatically. It runs as a non-root user and includes a
`HEALTHCHECK`.

## Configuration

All settings are optional; see `.env.example`.

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `8000` | Listening port |
| `PREREQPATH_MAX_CONCURRENT` | `2` | Simultaneous plan solves (each uses several CPU-seconds). Excess requests wait up to 15 s, then get HTTP 503 with a retry message. Raise it on bigger machines. |
| `PREREQPATH_SOLVER_WORKERS` | `8` | CP-SAT search threads per plan. Set `1` on CPU-capped hosts (Render free = 0.1 CPU): measured within 1–4% of 8-thread plan quality at 5–14× less CPU. `render.yaml` sets 1. |
| `PREREQPATH_MAX_ALTERNATIVES` | `3` | Cap on alternative plans per request; each is another solve. `render.yaml` sets 1 for the free tier. |
| `PREREQPATH_DATA_DIR` | `<repo>/data` | Location of `catalog/` and `verified/` |
| `PREREQPATH_CORS_ORIGINS` | unset | Only if the frontend is hosted on a different origin (comma-separated) |
| `VITE_API_BASE` | unset | **Frontend build-time** API URL, used only for split hosting |

### Sizing

Use 1 vCPU and 1 GB RAM for a demo; the container measured about 300 MB resident after serving concurrent solves.
CP-SAT uses up to 8 search threads per solve, so more vCPUs shorten double-major solves.

## Split hosting (optional)

To host the static frontend on Vercel or Netlify and the API elsewhere:

```bash
cd frontend
VITE_API_BASE=https://your-api.example.com npm run build     # deploy frontend/dist
```

Then set `PREREQPATH_CORS_ORIGINS=https://your-frontend.example.com` on the API.

## Post-deploy smoke test

```bash
curl -s https://YOUR-APP/api/health          # {"ok":true}
cd frontend && BASE_URL=https://YOUR-APP npm run e2e
```

## Updating catalog data

```bash
cd backend
python -m prereqpath.catalog.build courses      # ~4 min, rate-limited
python -m prereqpath.catalog.build programs
python -m prereqpath.catalog.build exams
python -m pytest                                # verified overlays fail loudly if catalog text changed
```

Commit the updated `data/catalog/` and redeploy. If UNC changed a verified program's text, the app shows it as
"Catalog changed: re-review" until the overlay in `data/verified/` is re-checked.
