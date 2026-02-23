"""
conftest.py for backend/scraper/tests/

Stubs out db.database before any scraper module can import it, so unit tests
run without a real database connection or environment variables.
"""

import sys
import os
from unittest.mock import MagicMock

# Add backend/ to sys.path (same as the scraper scripts do themselves).
_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

# Stub out db and db.database so module-level imports in scraper scripts
# don't require a real Supabase connection.
_mock_engine = MagicMock(name="engine")
_mock_db_module = MagicMock(name="db.database")
_mock_db_module.engine = _mock_engine

if "db" not in sys.modules:
    sys.modules["db"] = MagicMock(name="db")
if "db.database" not in sys.modules:
    sys.modules["db.database"] = _mock_db_module
