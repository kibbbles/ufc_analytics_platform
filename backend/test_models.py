"""Test script to verify SQLAlchemy models work correctly."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from db import Base, engine, SessionLocal, Fighter, Event, Fight


def test_database_connection():
    """Test basic database connectivity."""
    try:
        # Test connection
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("[SUCCESS] Database connection successful!")
            return True
    except Exception as e:
        print(f"[ERROR] Database connection failed: {e}")
        return False


def test_models():
    """Test that models can be used."""
    try:
        # Create a session
        db = SessionLocal()
        
        # Try to query (should return empty results but no errors)
        fighters = db.query(Fighter).limit(5).all()
        events = db.query(Event).limit(5).all()
        fights = db.query(Fight).limit(5).all()
        
        print(f"[SUCCESS] Models working! Found {len(fighters)} fighters, {len(events)} events, {len(fights)} fights")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] Model test failed: {e}")
        return False


if __name__ == "__main__":
    print("Testing UFC Analytics Platform Database Models...")
    print("=" * 50)
    
    # Test connection
    if test_database_connection():
        # Test models
        test_models()
    
    print("=" * 50)
    print("Database testing complete!")