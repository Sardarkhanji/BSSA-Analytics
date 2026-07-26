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
COPY bihar_districts.geojson ./
COPY "BSSA_logo.png" ./

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "athlete_dashboard.py", "--server.port=8501", "--server.address=0.0.0.0", "--browser.gatherUsageStats=false"]
