FROM python:3.12-slim

WORKDIR /app

# Install Python dependencies first (separate layer — cached unless requirements change)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY backend/ .

# Create the logs directory the app expects
RUN mkdir -p logs

EXPOSE 8000

# 1 uvicorn worker keeps memory within Fly.io free tier (256 MB).
# FastAPI is async so 1 worker still handles concurrent requests fine.
CMD ["gunicorn", "api.main:app", "-c", "gunicorn.conf.py", "--workers", "1"]
