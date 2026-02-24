"""
fights.py — Fight endpoints

Routes:
    GET  /fights            List all fights (filterable by event, fighter, weight class)
    GET  /fights/{id}       Single fight detail + round-by-round stats

Implemented in Task 4.5.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/fights", tags=["fights"])
