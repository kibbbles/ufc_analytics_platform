"""
fighters.py — Fighter endpoints

Routes:
    GET  /fighters          List all fighters (paginated, filterable)
    GET  /fighters/{id}     Single fighter profile + tale of the tape

Implemented in Task 4.5.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/fighters", tags=["fighters"])
