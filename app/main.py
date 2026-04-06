from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
import logging
from app.database import engine, Base
from app.routes import request_api, admin_api, dashboard_api
from app.queue.retry_worker import retry_loop

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB (usually done by alembic or setup script in production, but we do it here for simplicity)
    Base.metadata.create_all(bind=engine)
    
    # Start the background task for retries
    retry_task = asyncio.create_task(retry_loop())
    
    yield
    
    # Clean up (cancel task on shutdown)
    retry_task.cancel()

app = FastAPI(
    title="Configurable Workflow Decision Platform",
    description="A robust backend for configuring state machines and rule engines.",
    version="1.0.0",
    lifespan=lifespan
)

# Include Routers
app.include_router(request_api.router)
app.include_router(admin_api.router)
app.include_router(dashboard_api.router)

from fastapi.responses import RedirectResponse
from fastapi import Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime
from app.models import Request
from app.auth import require_any_role
from app.database import get_db

@app.get("/records")
def get_records(
    type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_any_role)
):
    query = db.query(Request)
    
    if type:
        # Check both schemas {"type": "income"} and {"income": ...}
        t = type.lower()
        query = query.filter(
            (func.json_extract(Request.payload, '$.type') == t) |
            (func.json_extract(Request.payload, f'$.{t}') != None)
        )
    if category:
        query = query.filter(func.json_extract(Request.payload, '$.category') == category)
    if start_date:
        query = query.filter(Request.created_at >= start_date)
    if end_date:
        query = query.filter(Request.created_at <= end_date)
        
    records = query.order_by(Request.created_at.desc()).all()
    
    # Return formatted records with payload
    from app.routes.request_api import format_request_response
    results = []
    for r in records:
        resp = format_request_response(db, r).model_dump()
        resp["payload"] = r.payload
        results.append(resp)
        
    return results

@app.get("/")
def read_root():
    return RedirectResponse(url="/docs")

@app.get("/health")
def health_check():
    return {"status": "ok"}
