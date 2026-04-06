from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Workflow, WorkflowState, Rule, Transition
from app.schemas import WorkflowCreate, WorkflowResponse, RuleCreate, RuleResponse, TransitionCreate, TransitionResponse

from app.auth import require_admin

router = APIRouter(prefix="/api/admin", tags=["Admin Configuration"], dependencies=[Depends(require_admin)])

@router.post("/workflows", response_model=WorkflowResponse)
def create_workflow(payload: WorkflowCreate, db: Session = Depends(get_db)):
    # Create workflow
    workflow = Workflow(name=payload.name, description=payload.description)
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    
    # Create associated states
    for state_name in payload.states:
        ws = WorkflowState(workflow_id=workflow.id, name=state_name)
        db.add(ws)
    
    # Make sure INIT state exists if it wasn't provided
    if "INIT" not in payload.states:
        db.add(WorkflowState(workflow_id=workflow.id, name="INIT"))

    db.commit()
    db.refresh(workflow)

    return workflow

@router.post("/rules", response_model=RuleResponse)
def create_rule(payload: RuleCreate, db: Session = Depends(get_db)):
    workflow = db.query(Workflow).filter(Workflow.id == payload.workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
        
    rule = Rule(
        workflow_id=payload.workflow_id,
        name=payload.name,
        conditions=payload.conditions
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule

@router.post("/transitions", response_model=TransitionResponse)
def create_transition(payload: TransitionCreate, db: Session = Depends(get_db)):
    # Verify resources exist
    if payload.rule_id:
        rule = db.query(Rule).filter(Rule.id == payload.rule_id).first()
        if not rule:
             raise HTTPException(status_code=404, detail="Rule not found")
             
    from_state = db.query(WorkflowState).filter(WorkflowState.id == payload.from_state_id).first()
    to_state = db.query(WorkflowState).filter(WorkflowState.id == payload.to_state_id).first()
    
    if not from_state or not to_state:
        raise HTTPException(status_code=404, detail="State not found")

    transition = Transition(
        workflow_id=payload.workflow_id,
        from_state_id=payload.from_state_id,
        to_state_id=payload.to_state_id,
        rule_id=payload.rule_id,
        priority=payload.priority
    )
    db.add(transition)
    db.commit()
    db.refresh(transition)
    return transition
