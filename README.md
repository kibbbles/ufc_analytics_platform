# UFC Analytics Platform 🥊

ML-powered UFC fight analytics platform with interactive predictions and visualizations. Built to demonstrate production-level data science and software engineering skills.

## 🎯 Features

- **Fight Outcome Predictor**: Interactive ML predictions with adjustable fighter parameters
- **Style Evolution Timeline**: Visualize how fighting styles evolved throughout UFC history  
- **Fighter Endurance Dashboard**: Round-by-round performance analysis and cardio predictions

## 🛠️ Tech Stack

### Backend
- **Framework**: FastAPI 0.104.1
- **Database**: PostgreSQL (Supabase)
- **ML**: XGBoost, scikit-learn
- **ORM**: SQLAlchemy 2.0

### Frontend (Coming Soon)
- **Framework**: React 18 + TypeScript
- **Visualization**: Recharts, D3.js
- **Styling**: Tailwind CSS

### Data Pipeline
- **Source**: UFCStats.com via enhanced Greko scraper
- **Processing**: pandas, numpy
- **Validation**: Great Expectations

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+ (for frontend)
- PostgreSQL (or Supabase account)

### Backend Setup

1. Clone the repository:
```bash
git clone https://github.com/kibbbles/ufc_analytics_platform.git
cd ufc_analytics_platform
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r backend/requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your Supabase credentials
```

5. Run database migrations:
```bash
cd backend
alembic upgrade head
```

6. Start the API server:
```bash
uvicorn app.main:app --reload
```

API will be available at `http://localhost:8000`
API docs at `http://localhost:8000/docs`

## 📊 Project Status

### Current Phase: Database Setup
- ✅ Project structure created
- ✅ Supabase database provisioned
- ✅ Database schema implemented (matching Greco's CSV format)
- ⏳ SQLAlchemy models setup
- ⏳ Data scraper enhancement
- ⏳ ML model development
- ⏳ Frontend development

### Progress Tracking
See [Task Master tasks](/.taskmaster/tasks/tasks.json) for detailed progress.

## 📁 Project Structure

```
ufc_analytics_platform/
├── backend/
│   ├── app/           # FastAPI application
│   ├── db/            # Database models and config
│   ├── models/        # ML models
│   ├── schemas/       # Pydantic schemas
│   ├── services/      # Business logic
│   └── utils/         # Helper functions
├── frontend/          # React application (coming soon)
├── .taskmaster/       # Task management
└── docs/             # Documentation
```

## 🔗 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/predictions/simulate` | POST | Get fight outcome prediction |
| `/api/v1/analytics/style-evolution` | GET | Get style evolution data |
| `/api/v1/fighters/{id}/endurance` | GET | Get fighter endurance profile |
| `/health` | GET | API health check |

## 🤝 Contributing

This is a portfolio project for demonstration purposes. Feel free to explore the code!

## 📝 License

MIT License - See [LICENSE](LICENSE) file for details

## 👤 Author

**kabec**
- GitHub: [@kibbbles](https://github.com/kibbbles)

## 🙏 Acknowledgments

- UFC Stats for providing fight data
- Greko scraper for data collection capabilities

---

**Last Updated**: August 30, 2024
- Initial project setup
- Supabase database provisioned
- Database schema created (6 tables: fighters, events, fights, fight_stats, raw_fighter_details, raw_fight_stats)
- Schema designed to match Greco's UFC scraper CSV format
- Backend folder structure established