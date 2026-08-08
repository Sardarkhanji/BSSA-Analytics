#!/bin/sh
# start.sh – Launch the FastAPI session API and the Streamlit dashboard.
# Both processes share the same container and /tmp directory for session data.

set -e

# Start the FastAPI session API on port 8502 in the background.
uvicorn api_server:app --host 0.0.0.0 --port 8502 &

# Start the Streamlit dashboard on port 8501 (foreground).
exec streamlit run athlete_dashboard.py \
  --server.port=8501 \
  --server.address=0.0.0.0 \
  --browser.gatherUsageStats=false \
  --server.enableCORS=false \
  --server.enableXsrfProtection=false
