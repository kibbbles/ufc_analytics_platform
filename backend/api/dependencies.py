"""
dependencies.py — FastAPI dependency injection

Provides get_db() for use with Depends() in route handlers, wrapping the
session factory from db.database so FastAPI manages the session lifecycle
(open on request start, close on request end, even if an error occurs).

Implemented in Task 4.2.
"""
