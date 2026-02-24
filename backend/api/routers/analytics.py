"""
analytics.py — Analytics endpoints

Routes:
    GET  /analytics/style-evolution             Finish rates and style trends over time
    GET  /analytics/fighter-endurance/{id}      Round-by-round performance profile for a fighter

These power Products 2 and 3 (Style Evolution Timeline, Fighter Endurance Dashboard).
Implemented in Task 4.5.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/analytics", tags=["analytics"])
