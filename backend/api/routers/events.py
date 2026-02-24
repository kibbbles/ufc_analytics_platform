"""
events.py — Event endpoints

Routes:
    GET  /events            List all events (paginated, filterable by year/location)
    GET  /events/{id}       Single event + all fights on the card

Implemented in Task 4.5.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/events", tags=["events"])
