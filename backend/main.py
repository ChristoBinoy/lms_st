from contextlib import asynccontextmanager
from fastapi import FastAPI,Depends,HTTPException
from sqlalchemy.orm import Session

from backend.database import engine, Base, SessionLocal,get_db
from backend.queries import get_all_leads_flat
import backend.models  # Keeps your existing tables discovery import safe

# 1. Wrap your table creation code into the official FastAPI startup lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initializing database generation sequence...")
    # This automatically spawns your tables in lms.db if they were deleted

    Base.metadata.create_all(bind=engine)
    print("Success! Your 'lms.db' file infrastructure is validated.")
    yield # The server opens up for business right here!


# 2. Instantiate the core REST API engine with your lifespan wrapper

app = FastAPI(
    title="LMS Core REST API Gateway",
    version="1.0.0",
    lifespan=lifespan
)

# 3. Create your lightweight health check route endpoint
@app.get("/health")
def health_check():

    """
    Lightweight, unauthenticated endpoint used to verify if our 
    FastAPI backend server is live, healthy, and reachable across the network.
    """
    return {
        "status": "healthy",
        "service": "lms-backend-engine",
        "environment": "development"
    }

# 2. Add your new database-backed network route right under your health check
@app.get("/api/leads")
def fetch_all_leads_api(db: Session = Depends(get_db)):
    """
    Network endpoint that queries the SQLite database safely behind 
    our API firewall and returns all active leads as a serialized JSON array.
    """
    try:
        leads = get_all_leads_flat(db)
        return leads
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database Network Error: {str(e)}")
