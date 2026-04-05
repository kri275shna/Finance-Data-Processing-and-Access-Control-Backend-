import asyncio
import logging
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models import Request, WorkflowState
from app.engine.workflow_engine import process_request

logger = logging.getLogger(__name__)

async def retry_loop():
    """
    Background loop that polls for requests in the RETRY state and re-processes them 
    if exponential backoff time has elapsed.
    """
    logger.info("Starting Retry Queue Worker...")
    while True:
        try:
            db = SessionLocal()
            # We want to find requests in the RETRY state. 
            # We don't have the exact ID of RETRY state globally, so we join.
            retry_requests = db.query(Request).join(WorkflowState, Request.current_state_id == WorkflowState.id).filter(
                WorkflowState.name == "RETRY"
            ).all()

            for req in retry_requests:
                # Exponential backoff formula: 2^retry_count * 5 seconds
                backoff_seconds = (2 ** req.retry_count) * 5
                next_retry_time = req.updated_at + timedelta(seconds=backoff_seconds)
                
                if datetime.utcnow() >= next_retry_time:
                    logger.info(f"Retrying request {req.id} (Attempt {req.retry_count + 1})")
                    # Hand off to the engine again
                    process_request(db, req)

            db.close()
        except Exception as e:
            logger.error(f"Error in retry loop: {e}")
        
        await asyncio.sleep(5) # Poll every 5 seconds
