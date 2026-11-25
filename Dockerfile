FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements_dashboard.txt ./
RUN pip install -r requirements_dashboard.txt

COPY athlete_dashboard.py ./
COPY api_server.py ./
COPY start.sh ./
COPY bihar_districts.geojson ./
COPY "BSSA_logo.png" ./
COPY Athlete_10000_augmented.xlsx ./

RUN chmod +x start.sh

# 8501 = Streamlit dashboard, 8502 = FastAPI session API
EXPOSE 8501 8502

HEALTHCHECK --interval=30s --timeout=10s --start-period=25s --retries=3 \
    CMD curl -fsS http://localhost:8501/_stcore/health || exit 1

CMD ["./start.sh"]
