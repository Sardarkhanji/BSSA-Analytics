"""
BSSA Analytics Session API
--------------------------
Lightweight FastAPI server that runs alongside the Streamlit dashboard.

The Data Collection Flutter app POSTs athlete CSV data here and receives a
session_id.  The Streamlit dashboard reads the session via its own internal
HTTP call when launched with ?session=<session_id>.
"""
import uuid
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="BSSA Analytics Session API", version="1.0.0")

# Allow the Flutter web app (running on a different port) to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# In-memory session store: session_id -> CSV string
_sessions: Dict[str, str] = {}


class UploadBody(BaseModel):
    csv: str


@app.get("/health")
def health():
    return {"status": "ok", "sessions": len(_sessions)}


@app.post("/sessions", status_code=201)
def create_session(body: UploadBody):
    """Accept a CSV string and return a session_id."""
    session_id = str(uuid.uuid4())
    _sessions[session_id] = body.csv
    return {"session_id": session_id}


@app.get("/sessions/{session_id}")
def get_session(session_id: str):
    """Return the CSV stored under the given session_id."""
    csv = _sessions.get(session_id)
    if csv is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"csv": csv}


@app.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: str):
    """Remove a session from the store."""
    _sessions.pop(session_id, None)
