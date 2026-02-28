# Task ID: 6

**Title:** ML Model Training and Serving

**Status:** pending

**Dependencies:** 4 ✓, 5 ⧖

**Priority:** high

**Description:** Implement the machine learning pipeline to train fight prediction models (win/loss and method prediction) and create a model serving infrastructure using joblib serialization, loaded at API startup.

**Details:**

Build a complete ML pipeline using scikit-learn 1.3+ and XGBoost 2.0:

1. Data preparation:
   - Train/validation/test splitting (temporal split)
   - Feature scaling and normalization
   - Class imbalance handling (SMOTE or class weights)

2. Model training:
   - Binary classification model for win/loss prediction
     - XGBoost with hyperparameter tuning
     - Cross-validation with time-based splits
   - Multi-class model for fight outcome method
     - Random Forest for KO/TKO vs Submission vs Decision
     - Calibrated probabilities

3. Model evaluation:
   - Accuracy, precision, recall metrics
   - ROC-AUC and PR-AUC curves
   - Confusion matrices
   - Feature importance analysis (critical for UI sliders feature)
   - Backtesting on historical fights

4. Model serialization:
   - Use joblib to serialize trained models to backend/models/ directory
   - Save feature scaler alongside models
   - Store feature importance data as JSON for frontend consumption
   - Version models with simple filename conventions (e.g., win_loss_v1.joblib, method_v1.joblib)

5. Model serving:
   - Models loaded at FastAPI application startup (Task 4 lifespan event)
   - FastAPI endpoints for predictions in backend/api/v1/endpoints/predictions.py
   - Input validation with Pydantic
   - Batch prediction capability

6. Interpretability (priority for UI):
   - Export feature importance rankings from XGBoost and Random Forest
   - Generate feature importance charts/data consumable by the frontend sliders feature
   - SHAP values for individual prediction explanations (optional but valuable)

Implement a simple model loader utility that reads joblib files from backend/models/ at startup and exposes them via FastAPI app state.

**Test Strategy:**

1. Test model accuracy on holdout data
2. Verify calibration of probability outputs
3. Benchmark prediction latency
4. Test model loading from backend/models/ directory at startup
5. Verify joblib serialization/deserialization round-trip
6. Test concurrent prediction requests
7. Verify model reproducibility with fixed random seeds
8. Test feature importance output format matches frontend expectations
9. Validate batch prediction endpoint

## Subtasks

### 6.1. Data preparation and train/test splitting

**Status:** pending  
**Dependencies:** None  

Load engineered features from Task 5, perform temporal train/validation/test split, apply feature scaling, and handle class imbalance using SMOTE or class weights.

### 6.2. Train XGBoost win/loss binary classifier

**Status:** pending  
**Dependencies:** None  

Train an XGBoost binary classification model for win/loss prediction with hyperparameter tuning and time-based cross-validation. Evaluate with accuracy, ROC-AUC, and PR-AUC metrics.

### 6.3. Train Random Forest method multi-class classifier

**Status:** pending  
**Dependencies:** None  

Train a Random Forest multi-class model to predict fight outcome method (KO/TKO vs Submission vs Decision) with calibrated probabilities. Evaluate with confusion matrix and per-class metrics.

### 6.4. Feature importance extraction and export

**Status:** pending  
**Dependencies:** None  

Extract feature importance rankings from both XGBoost and Random Forest models. Export as JSON files to backend/models/ for frontend consumption. This data powers the UI sliders feature showing which attributes matter most.

### 6.5. Serialize models with joblib to backend/models/

**Status:** pending  
**Dependencies:** None  

Serialize trained models and feature scalers using joblib to the backend/models/ directory. Use clear filename conventions (e.g., win_loss_v1.joblib, method_v1.joblib, scaler_v1.joblib). Include a model manifest JSON with metadata.

### 6.6. Model loader utility and FastAPI startup integration

**Status:** pending  
**Dependencies:** None  

Create a model loader utility (backend/ml/model_loader.py) that reads joblib files from backend/models/ at application startup via FastAPI lifespan event. Expose loaded models through app state for use in prediction endpoints.

### 6.7. Prediction endpoints implementation

**Status:** pending  
**Dependencies:** None  

Implement FastAPI prediction endpoints in backend/api/v1/endpoints/predictions.py. Include single fight prediction and batch prediction capability. Use Pydantic for input validation. Return probabilities and feature importance context.

### 6.8. Model evaluation and backtesting report

**Status:** pending  
**Dependencies:** None  

Run full evaluation on holdout test set: accuracy, precision, recall, ROC-AUC, PR-AUC, confusion matrices, and backtesting on historical fights. Save evaluation report to backend/models/evaluation_report.json.
