# Task ID: 4

**Title:** FastAPI Backend Setup

**Status:** done

**Dependencies:** 1 ✓, 3 ✓

**Priority:** high

**Description:** Initialize the FastAPI project structure with middleware, error handling, logging, and basic health check endpoints. Uses raw SQL with sqlalchemy.text() and Pydantic schemas for serialization (no ORM models). Public platform with no authentication required.

**Details:**

Set up a FastAPI application with the following components:

1. Project structure:
   ```
   backend/
     â”œâ”€â”€ api/
     â”‚   â”œâ”€â”€ v1/
     â”‚   â”‚   â”œâ”€â”€ endpoints/
     â”‚   â”‚   â”‚   â”œâ”€â”€ predictions.py
     â”‚   â”‚   â”‚   â”œâ”€â”€ analytics.py
     â”‚   â”‚   â”‚   â”œâ”€â”€ fighters.py
     â”‚   â”‚   â”‚   â”œâ”€â”€ fights.py
     â”‚   â”‚   â”‚   â””â”€â”€ events.py
     â”‚   â”‚   â””â”€â”€ router.py
     â”‚   â””â”€â”€ dependencies.py
     â”œâ”€â”€ core/
     â”‚   â”œâ”€â”€ config.py
     â”‚   â””â”€â”€ logging.py
     â”œâ”€â”€ db/
     â”‚   â””â”€â”€ database.py  (SessionLocal, engine already configured - use as-is)
     â”œâ”€â”€ schemas/
     â”‚   â”œâ”€â”€ fighter.py
     â”‚   â”œâ”€â”€ fight.py
     â”‚   â”œâ”€â”€ event.py
     â”‚   â”œâ”€â”€ prediction.py
     â”‚   â””â”€â”€ analytics.py
     â””â”€â”€ main.py
   ```

2. Key API endpoints to implement:
   - `GET /fighters` - list all fighters
   - `GET /fighters/{id}` - single fighter detail
   - `GET /fights` - list all fights
   - `GET /fights/{id}` - single fight detail
   - `GET /events` - list all events
   - `GET /events/{id}` - single event detail
   - `POST /predictions/fight-outcome` - predict fight outcome
   - `GET /analytics/style-evolution` - style evolution analytics
   - `GET /analytics/fighter-endurance/{id}` - fighter endurance analytics

3. Database access pattern:
   - Import SessionLocal and engine from `backend/db/database.py`
   - Use `sqlalchemy.text()` for all queries (no ORM models)
   - Use Pydantic schemas for request/response serialization
   - Example pattern:
     ```python
     from backend.db.database import SessionLocal
     from sqlalchemy import text
     
     def get_fighters(db: Session):
         result = db.execute(text("SELECT * FROM fighters"))
         return result.mappings().all()
     ```

4. Middleware configuration:
   - CORS with appropriate origins (allow frontend dev server)
   - Request ID generation
   - Timing middleware
   - Error handling middleware
   - No authentication middleware needed (public platform)

5. Pydantic schemas (no ORM, pure serialization):
   - FighterBase, FighterResponse
   - FightBase, FightResponse
   - EventBase, EventResponse
   - PredictionRequest, PredictionResponse
   - AnalyticsResponse

6. Health check endpoints:
   - `/health` for basic API health
   - `/health/db` for database connectivity (run a simple `SELECT 1` via sqlalchemy.text())

7. Logging configuration:
   - Structured JSON logging
   - Log rotation
   - Different log levels for environments

Implement using Uvicorn for development and Gunicorn for production with appropriate worker configurations. No Redis, no security/auth module.

**Test Strategy:**

1. Unit test middleware functions
2. Test health check endpoints (`/health`, `/health/db`)
3. Verify CORS configuration
4. Test error handling with forced exceptions
5. Benchmark request processing time
6. Validate OpenAPI schema generation
7. Test logging output format and content
8. Test each endpoint with sample data: GET /fighters, GET /fighters/{id}, GET /fights, GET /fights/{id}, GET /events, GET /events/{id}
9. Test POST /predictions/fight-outcome with valid and invalid payloads
10. Test analytics endpoints return correctly structured responses
11. Verify raw SQL queries via sqlalchemy.text() return correct Pydantic-serializable data

## Subtasks

### 4.1. Project Structure and Core Configuration

**Status:** done  
**Dependencies:** None  

Initialize the FastAPI project directory structure, core configuration module, and logging setup as the foundation for all other components.

**Details:**

Create the full directory tree under backend/ as specified: api/v1/endpoints/, core/, db/, schemas/, and main.py. Implement backend/core/config.py using Pydantic BaseSettings to load environment variables (DATABASE_URL, ENVIRONMENT, LOG_LEVEL, ALLOWED_ORIGINS, etc.). Implement backend/core/logging.py with structured JSON logging using python-json-logger, log rotation via logging.handlers.RotatingFileHandler, and environment-aware log levels (DEBUG for dev, INFO/WARNING for prod). Create empty __init__.py files in all packages. Acceptance criteria: All directories and files exist, config loads from .env without errors, logging outputs valid JSON to console and file, log rotation is configured.

### 4.2. Database Session Management and Dependencies

**Status:** done  
**Dependencies:** None  

Set up the database session dependency for FastAPI endpoints, importing the existing SessionLocal and engine from backend/db/database.py and providing a reusable get_db dependency.

**Details:**

In backend/api/dependencies.py, implement a get_db() generator function that yields a SessionLocal instance and ensures the session is closed in a finally block. Verify the import from backend/db/database.py works correctly (SessionLocal, engine already configured). Add a utility function to test DB connectivity by executing sqlalchemy.text('SELECT 1'). Do NOT redefine engine or SessionLocal. Acceptance criteria: get_db() yields a valid session, session is always closed after request, connectivity test function returns True on success and raises a clear exception on failure.

### 4.3. Pydantic Schemas Definition

**Status:** done  
**Dependencies:** None  

Define all Pydantic schemas for request/response serialization across fighters, fights, events, predictions, and analytics â€” with no ORM models.

**Details:**

Create the following schema files under backend/schemas/: fighter.py (FighterBase, FighterResponse with id, name, height_cm, weight_lbs, reach_inches, stance, birth_date, wins, losses, draws, no_contests), fight.py (FightBase, FightResponse with relevant fight fields), event.py (EventBase, EventResponse with id, name, date, city, country), prediction.py (PredictionRequest with fighter_a_id, fighter_b_id and optional parameters; PredictionResponse with win_probability, predicted_winner, confidence, method_probabilities), analytics.py (StyleEvolutionResponse, FighterEnduranceResponse). All schemas use Pydantic v2 with model_config = ConfigDict(from_attributes=False) since there are no ORM models. Acceptance criteria: All schemas import without errors, PredictionRequest validates required fields, all Response schemas serialize dict/mapping inputs correctly.

### 4.4. Middleware and Error Handling Configuration

**Status:** done  
**Dependencies:** None  

Configure CORS, request ID generation, timing middleware, and global error handling in main.py to make the API production-ready.

**Details:**

In backend/main.py, create the FastAPI app instance and add the following middleware in order: (1) CORSMiddleware with origins from config (e.g., http://localhost:3000, http://localhost:5173), allow_methods=['*'], allow_headers=['*']; (2) Custom RequestIDMiddleware that generates a UUID per request and attaches it to request.state and response headers as X-Request-ID; (3) Custom TimingMiddleware that measures request duration and logs it with the request ID and path; (4) Global exception handler using @app.exception_handler(Exception) that returns a structured JSON error response with request_id, message, and status_code, and logs the full traceback. No authentication middleware. Acceptance criteria: CORS headers present on responses, X-Request-ID header in every response, timing logged per request, unhandled exceptions return JSON (not HTML), 404s return structured JSON.

### 4.5. API Endpoints Implementation and Router Setup

**Status:** done  
**Dependencies:** None  

Implement all v1 API endpoint modules for fighters, fights, events, predictions, and analytics using raw SQL via sqlalchemy.text(), and wire them into the versioned router.

**Details:**

Implement each endpoint file under backend/api/v1/endpoints/: fighters.py (GET /fighters with optional pagination query params, GET /fighters/{id}), fights.py (GET /fights with optional filters, GET /fights/{id}), events.py (GET /events, GET /events/{id}), predictions.py (POST /predictions/fight-outcome â€” accepts PredictionRequest, queries fighter stats via raw SQL, returns PredictionResponse with placeholder logic until ML model is ready in Task 6), analytics.py (GET /analytics/style-evolution with fighter_id query param, GET /analytics/fighter-endurance/{id}). All DB queries use db.execute(text('...')).mappings().all() or .first(). Return 404 HTTPException when single resources are not found. In backend/api/v1/router.py, create an APIRouter and include all endpoint routers with appropriate prefixes and tags. In main.py, include the v1 router under prefix /api/v1. Acceptance criteria: All endpoints return correct HTTP status codes, 404 on missing resources, responses validate against Pydantic schemas, raw SQL used exclusively (no ORM), OpenAPI docs auto-generated at /docs.

### 4.6. Health Check Endpoints and Server Configuration

**Status:** done  
**Dependencies:** None  

Implement /health and /health/db endpoints, finalize main.py app wiring, and configure Uvicorn/Gunicorn server settings for development and production.

**Details:**

Add health check routes directly in main.py or a dedicated health router: GET /health returns {status: 'ok', environment: str, version: str, timestamp: ISO datetime}; GET /health/db executes db.execute(text('SELECT 1')) via a direct SessionLocal() call (not the request-scoped dependency) and returns {status: 'ok', db: 'connected'} or {status: 'error', db: str(exception)} with HTTP 503 on failure. Create a backend/run_dev.py or document uvicorn command: uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000. Create a Procfile or gunicorn.conf.py for production: gunicorn backend.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --access-logfile - --error-logfile -. Ensure app startup event logs the environment and config summary. Acceptance criteria: /health returns 200 with valid JSON, /health/db returns 200 when DB is reachable and 503 when not, Uvicorn starts successfully in dev mode, Gunicorn config file is valid, startup log message appears on launch.
