"""
schemas.py — Pydantic request/response schemas

Defines the shape of data going in and out of every API endpoint.
FastAPI uses these to validate inputs, strip unwanted DB columns from
responses, and auto-generate the OpenAPI (Swagger) documentation.

Schema classes defined here (Task 4.3):
    Fighters:    FighterResponse, FighterListResponse
    Fights:      FightResponse, FightListResponse
    Events:      EventResponse, EventListResponse
    Analytics:   StyleEvolutionResponse, EnduranceRoundResponse, EnduranceResponse
    Predictions: PredictionRequest, PredictionResponse
    Shared:      PaginationMeta

Implemented in Task 4.3.
"""
