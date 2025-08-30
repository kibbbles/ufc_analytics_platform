# UFC Analytics Platform - Complete API Documentation

## What is an API?
An API (Application Programming Interface) is like a waiter in a restaurant:
- Your **frontend** (React app) is the customer
- Your **backend** (FastAPI server) is the kitchen  
- The **API endpoints** are menu items the customer can order
- The waiter takes orders (requests) and brings back food (responses)

## Base URLs
- **Local Development:** `http://localhost:8000` (when running FastAPI locally)
- **Production:** `https://your-api.railway.app` (after deployment)

---

## API Structure Overview

### How API Calls Work:
1. **Frontend sends request** → `POST http://localhost:8000/api/v1/predictions/fight-outcome`
2. **Backend processes request** → Runs ML model with input data
3. **Backend sends response** → Returns prediction as JSON
4. **Frontend displays result** → Shows win probability on dashboard

### Request Types:
- **GET:** Fetch/retrieve data (like getting fighter info)
- **POST:** Send data for processing (like submitting prediction request)

---

## 1. PREDICTION ENDPOINTS

### POST /api/v1/predictions/fight-outcome
**Purpose:** Get ML prediction for who wins a fight between two fighters

**What it does:** Takes fighter stats and returns win probabilities + method predictions

**Request Format:**
```json