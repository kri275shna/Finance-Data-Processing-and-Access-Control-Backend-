from sqlalchemy.orm import Session
import uuid
import random
from datetime import datetime
from app.models import Request, Transition, AuditLog, RuleExecutionLog, WorkflowState
from app.engine.rule_engine import evaluate_rules
import requests

class ExternalServiceException(Exception):
    pass

def mock_credit_service(ssn: str) -> int:
    """Simulates an external API call to fetch a credit score."""
    # Simulate random failure
    if random.choice([True, False, False]): # 33% chance of failure
        raise ExternalServiceException("Failed to connect to Credit Agency API.")
    return random.randint(500, 850)

def process_request(db: Session, request_obj: Request):
    """
    Drives a request through the state machine until it hits a state with no passing transitions,
    or encounters an error requiring a RETRY.
    """
    
    # We will loop until no transitions happen natively
    while True:
        # Get current state
        current_state = request_obj.current_state
        if not current_state:
            # Maybe it hasn't been lazy-loaded or we just have ID
            current_state = db.query(WorkflowState).filter(WorkflowState.id == request_obj.current_state_id).first()
        
        if not current_state:
            break

        # Special interception for data enrichment before evaluation if we are in VALIDATION or similar
        # To make it dynamic without hardcoding specific workflow names, we can check if it needs credit score
        payload = request_obj.payload
        needs_credit_score = payload.get("ssn") is not None and payload.get("credit_score") is None
        
        if needs_credit_score:
            try:
                score = mock_credit_service(payload["ssn"])
                payload["credit_score"] = score
                request_obj.payload = payload # Update JSON
                
                # We save an audit log for data enrichment internally or just proceed
            except ExternalServiceException:
                # Need to move to RETRY or FAILED
                handle_failure(db, request_obj, reason="External API: Credit check failed.")
                return # Stop processing, it will be retried by queue

        # Find possible transitions from current state, ordered by priority
        transitions = db.query(Transition).filter(
            Transition.from_state_id == current_state.id,
            Transition.workflow_id == request_obj.workflow_id
        ).order_by(Transition.priority.asc()).all()

        moved = False
        for transition in transitions:
            # Check rule
            rule_passed = True # Assume true if no rule
            if transition.rule:
                rule_passed = evaluate_rules(transition.rule.conditions, payload)
                
                # Log rule execution
                rule_log = RuleExecutionLog(
                    request_id=request_obj.id,
                    rule_id=transition.rule.id,
                    passed=rule_passed,
                    details={"evaluated_payload": payload}
                )
                db.add(rule_log)

            if rule_passed:
                # Perform transition
                audit = AuditLog(
                    request_id=request_obj.id,
                    from_state_id=current_state.id,
                    to_state_id=transition.to_state.id if transition.to_state else transition.to_state_id,
                    reason=f"Transition rule passed" if transition.rule else "Unconditional transition"
                )
                db.add(audit)
                
                request_obj.current_state_id = transition.to_state_id
                # Reset retry count if we successfully move state
                request_obj.retry_count = 0 
                
                db.commit()
                moved = True
                break # We took a transition, now loop again starting from the *new* state
        
        if not moved:
            # No transitions possible, terminal state reached
            break

def handle_failure(db: Session, request_obj: Request, reason: str):
    """
    Handles transition to RETRY or FAILED based on retry_count.
    """
    max_retries = 3
    
    # We need to find the ID of the states
    retry_state = db.query(WorkflowState).filter(
        WorkflowState.workflow_id == request_obj.workflow_id,
        WorkflowState.name == "RETRY"
    ).first()
    
    failed_state = db.query(WorkflowState).filter(
        WorkflowState.workflow_id == request_obj.workflow_id,
        WorkflowState.name == "FAILED"
    ).first()
    
    if not retry_state or not failed_state:
        # Cannot fallback properly without standard states, just throw error
        return
    
    current_state_id = request_obj.current_state_id

    if request_obj.retry_count < max_retries:
        request_obj.retry_count += 1
        request_obj.current_state_id = retry_state.id
        db.add(AuditLog(
            request_id=request_obj.id,
            from_state_id=current_state_id,
            to_state_id=retry_state.id,
            reason=f"Failure: {reason}. Retry {request_obj.retry_count}/{max_retries}"
        ))
    else:
        request_obj.current_state_id = failed_state.id
        db.add(AuditLog(
            request_id=request_obj.id,
            from_state_id=current_state_id,
            to_state_id=failed_state.id,
            reason=f"Max retries exceeded. Failure: {reason}"
        ))
    
    db.commit()
