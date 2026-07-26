# Mashal Athlete Dashboard

Streamlit dashboard for athlete analytics, data cleaning, test performance, and profiling.

## What to keep in Git

For this dashboard to run reliably (especially with Docker), commit these files:

- `athlete_dashboard.py`
- `requirements_dashboard.txt`
- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`
- `.env.example`
- `bihar_districts.geojson`
- `README.md`

Optional (commit only if useful for your team):

- `request-list.http`
- `endpoint_testing.js`
- `test-script.py`
- sample anonymized test datasets

Do **not** commit:

- `.env` (contains secrets)
- `viz/` or any virtualenv
- `__pycache__/`
- generated exports (`*.xlsx`, logs, temp files)

---

## Why Docker Compose (instead of only Docker)

`docker-compose` is used because this app is a service with runtime config (port, env vars, healthcheck) that you want to start consistently with one command.

Benefits here:

- Single command startup/shutdown (`up`, `down`)
- Versioned service config in `docker-compose.yml`
- Easy env injection from `.env`
- Built-in healthcheck and readable service status
- Scales better if you later add DB/API/cache services

For a single local run, plain `docker run` works too, but Compose is cleaner and repeatable for day-to-day use.

---

## Quick Start (Docker)

### 1) Set environment variable

```bash
cd /home/risshukl/tools_and_utilities
cp .env.example .env
```

Edit `.env` and set:

```env
NVIDIA_API_KEY=your_real_key_here
```

### 2) Build and start

```bash
cd /home/risshukl/tools_and_utilities
docker-compose up -d --build
```

### 3) Open dashboard

- `http://localhost:8501`

### 4) Check status/logs

```bash
cd /home/risshukl/tools_and_utilities
docker-compose ps
docker-compose logs --tail=50 athlete-dashboard
```

### 5) Stop

```bash
cd /home/risshukl/tools_and_utilities
docker-compose down
```

---

## If `docker-compose down` says permission denied

If Docker cannot stop the container but it is running, use:

```bash
docker update --restart=no athlete-dashboard
docker exec athlete-dashboard sh -lc 'kill 1'
docker rm athlete-dashboard
docker-compose down --remove-orphans
```

### One-command helper script

You can run the bundled cleanup helper:

```bash
cd /home/risshukl/tools_and_utilities
./scripts/force_remove_athlete_dashboard.sh
```

This script attempts safe recovery first, then prints manual fallback steps if the container is still stuck.

If the above still fails, force-remove by container PID:

```bash
# 1) Find the container ID (example filter for athlete-dashboard)
docker ps -a --filter name=athlete-dashboard --format '{{.ID}}\t{{.Names}}\t{{.Status}}'

# 2) Get host PID for that container
docker inspect --format '{{.State.Pid}}' <container_id>

# 3) Kill that PID (requires sudo)
sudo kill -9 <pid>

# 4) Force remove the container
docker rm -f <container_id>

# 5) Clean compose leftovers
docker-compose down --remove-orphans
```

Then start again:

```bash
docker-compose up -d --build
```

---

## Non-Docker fallback (venv)

```bash
cd /home/risshukl/tools_and_utilities
source viz/bin/activate
pip install -r requirements_dashboard.txt
streamlit run athlete_dashboard.py
```

---

## Project files used by dashboard runtime

- App: `athlete_dashboard.py`
- Dependencies: `requirements_dashboard.txt`
- Geo map data: `bihar_districts.geojson`
- Container build: `Dockerfile`
- Service orchestration: `docker-compose.yml`
