"""Test endpoint for frontend-backend connectivity."""

from datetime import datetime

from fastapi import APIRouter

router = APIRouter()


@router.get("/test")
async def test_connection():
    """
    Test endpoint to verify frontend-backend connection.
    Called by the React app to confirm the API is reachable.
    """
    return {
        "status": "ok",
        "message": "Frontend successfully connected to FastAPI backend",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "0.1.0",
    }
