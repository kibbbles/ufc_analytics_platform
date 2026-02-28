"""run_dev.py — Start the UFC Analytics API in development mode.

Equivalent CLI command (run from backend/):
    uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

The --reload flag watches for file changes and restarts automatically.
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug",
    )
