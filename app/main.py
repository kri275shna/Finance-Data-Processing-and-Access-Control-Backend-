from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
import logging
from app.database import engine, Base
from app.routes import request_api, admin_api
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

from fastapi.responses import RedirectResponse

@app.get("/")
def read_root():
    return RedirectResponse(url="/docs")

@app.get("/health")
def health_check():
    return {"status": "ok"}
