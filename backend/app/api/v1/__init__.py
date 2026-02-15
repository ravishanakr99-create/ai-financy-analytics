"""API v1 module."""

from fastapi import APIRouter

from app.api.v1 import reports, test

router = APIRouter()

router.include_router(test.router)
router.include_router(reports.router)
