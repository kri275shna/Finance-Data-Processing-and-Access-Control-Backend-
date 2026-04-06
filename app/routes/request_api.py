from fastapi import APIRouter, Depends, HTTPException, Header
from app.auth import require_admin, require_any_role
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Request, IdempotencyKey, WorkflowState, Workflow, AuditLog, RuleExecutionLog, Rule
from app.schemas import RequestCreate, RequestResponse, AuditLogResponse, ExplainResponse, RuleExecutionLogResponse
from app.engine.workflow_engine import process_request
from fastapi import BackgroundTasks
import logging

router = APIRouter(prefix="/api/requests", tags=["Requests"])
logger = logging.getLogger(__name__)

@router.post("", response_model=RequestResponse)
def create_request(
    payload: RequestCreate, 
    background_tasks: BackgroundTasks,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    user=Depends(require_admin)
):
    # Check Idempotency
    existing_key = db.query(IdempotencyKey).filter(IdempotencyKey.key == idempotency_key).first()
    if existing_key and existing_key.request_id:
        existing_req = db.query(Request).filter(Request.id == existing_key.request_id).first()
        return format_request_response(db, existing_req)

    # Verify workflow exists
    workflow = db.query(Workflow).filter(Workflow.id == payload.workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Find INIT state for the workflow
    init_state = db.query(WorkflowState).filter(
        WorkflowState.workflow_id == workflow.id, 
        WorkflowState.name == "INIT"
    ).first()

    if not init_state:
        raise HTTPException(status_code=500, detail="Workflow does not have an INIT state configured")

    # Create Request
    new_req = Request(
        workflow_id=workflow.id,
        current_state_id=init_state.id,
        payload=payload.payload
    )
    db.add(new_req)
    
    # Store Idempotency
    idempotency_record = IdempotencyKey(key=idempotency_key, request_id=new_req.id) # using uuid generation locally allows us to link immediately
    db.add(idempotency_record)
    
    # Initial Audit
    audit = AuditLog(
        request_id=new_req.id,
        to_state_id=init_state.id,
        reason="Initial Submit"
    )
    db.add(audit)
    db.commit()
    db.refresh(new_req)

    # Hand off to background worker for processing state machine
    background_tasks.add_task(process_wrapper, new_req.id)

    return format_request_response(db, new_req)

def process_wrapper(request_id: str):
    """Background task wrapper that gets a new DB session for engine."""
    # This ensures we don't leak sessions across threads
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        req = db.query(Request).filter(Request.id == request_id).first()
        if req:
            process_request(db, req)
    except Exception as e:
        logger.error(f"Error processing request {request_id}: {e}")
    finally:
        db.close()


@router.get("/{request_id}", response_model=RequestResponse)
def get_request(request_id: str, db: Session = Depends(get_db), user=Depends(require_any_role)):
    req = db.query(Request).filter(Request.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    return format_request_response(db, req)


@router.get("/{request_id}/history", response_model=list[AuditLogResponse])
def get_request_history(request_id: str, db: Session = Depends(get_db), user=Depends(require_any_role)):
    logs = db.query(AuditLog).filter(AuditLog.request_id == request_id).order_by(AuditLog.created_at.asc()).all()
    
    results = []
    for log in logs:
        from_state = db.query(WorkflowState).filter(WorkflowState.id == log.from_state_id).first() if log.from_state_id else None
        to_state = db.query(WorkflowState).filter(WorkflowState.id == log.to_state_id).first()
        results.append(AuditLogResponse(
            id=log.id,
            request_id=log.request_id,
            from_state=from_state.name if from_state else None,
            to_state=to_state.name if to_state else "Unknown",
            reason=log.reason,
            created_at=log.created_at
        ))
    return results

@router.get("/{request_id}/explain", response_model=ExplainResponse)
def explain_request(request_id: str, db: Session = Depends(get_db), user=Depends(require_any_role)):
    req = db.query(Request).filter(Request.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
        
    rule_logs = db.query(RuleExecutionLog).filter(RuleExecutionLog.request_id == request_id).order_by(RuleExecutionLog.executed_at.asc()).all()
    history = get_request_history(request_id, db)
    
    evaluated_rules = []
    for rl in rule_logs:
        rule = db.query(Rule).filter(Rule.id == rl.rule_id).first()
        evaluated_rules.append(RuleExecutionLogResponse(
            rule_name=rule.name if rule else "Deleted Rule",
            passed=rl.passed,
            details=rl.details,
            executed_at=rl.executed_at
        ))
    
    current_state = db.query(WorkflowState).filter(WorkflowState.id == req.current_state_id).first()
    
    reason = "Processing"
    if history:
        reason = history[-1].reason

    return ExplainResponse(
        request_id=req.id,
        input_snapshot=req.payload,
        final_state=current_state.name if current_state else "Unknown",
        decision_reason=reason,
        rules_evaluated=evaluated_rules,
        state_history=history
    )

def format_request_response(db: Session, req: Request):
    current_state = db.query(WorkflowState).filter(WorkflowState.id == req.current_state_id).first()
    return RequestResponse(
        id=req.id,
        workflow_id=req.workflow_id,
        current_state=current_state.name if current_state else "Unknown",
        retry_count=req.retry_count,
        created_at=req.created_at,
        updated_at=req.updated_at
    )
