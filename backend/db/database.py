"""Database connection and session management."""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Try to load dotenv, fallback if not available
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("dotenv loaded successfully")
except ImportError:
    print("dotenv not available, using environment variables directly")

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

# If not in environment, try to read .env file manually
if not DATABASE_URL:
    try:
        env_file = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    if line.startswith('DATABASE_URL='):
                        DATABASE_URL = line.split('=', 1)[1].strip()
                        print("Found DATABASE_URL in .env file")
                        break
    except Exception as e:
        print(f"Could not read .env file: {e}")

# For GitHub Actions: Use connection pooler (port 6543) which supports IPv4
# Direct connection (port 5432) uses IPv6 which GitHub Actions doesn't support
if DATABASE_URL and ":5432/" in DATABASE_URL and os.getenv("GITHUB_ACTIONS"):
    print("GitHub Actions detected - switching to connection pooler (IPv4)")
    DATABASE_URL = DATABASE_URL.replace(":5432/", ":6543/")

if not DATABASE_URL:
    print("DATABASE_URL not found!")
else:
    print("DATABASE_URL loaded")

# Create engine
# Note: SQLAlchemy requires "postgresql://" not "postgres://"
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Configure connection args to prefer IPv4 over IPv6
# This fixes GitHub Actions connectivity issues where IPv6 is not available
connect_args = {
    "connect_timeout": 10,
    "options": "-c client_encoding=utf8"
}

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using them
    pool_size=10,        # Number of connections to maintain
    max_overflow=20,     # Maximum overflow connections
    connect_args=connect_args
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_engine():
    """Get database engine for direct SQL operations."""
    return engine