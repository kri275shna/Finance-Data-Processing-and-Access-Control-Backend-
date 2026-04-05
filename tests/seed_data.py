import sys
import os

# Ensure app is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine, Base
from app.models import Workflow, WorkflowState, Rule, Transition

def seed_db():
    print("Setting up database schema...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    print("Cleaning up old data...")
    db.query(Transition).delete()
    db.query(Rule).delete()
    db.query(WorkflowState).delete()
    db.query(Workflow).delete()
    db.commit()

    print("Seeding Loan Approval Workflow...")
    workflow = Workflow(name="Loan Approval", description="Standard Loan Approval Process")
    db.add(workflow)
    db.commit()
    db.refresh(workflow)

    states = ["INIT", "VALIDATION", "RULE_EVALUATION", "APPROVED", "REJECTED", "MANUAL_REVIEW", "RETRY", "FAILED"]
    state_objects = {}
    for st_name in states:
        state = WorkflowState(workflow_id=workflow.id, name=st_name)
        db.add(state)
        db.commit()
        db.refresh(state)
        state_objects[st_name] = state

    print("Seeding Rules...")
    # Rule 1: Reject if income < 20000
    rule_reject = Rule(
        workflow_id=workflow.id,
        name="Income too low",
        conditions={"field": "income", "operator": "<", "value": 20000}
    )
    
    # Rule 2: Approve if credit score > 700
    # Note: credit_score might be fetched by the engine
    rule_approve = Rule(
        workflow_id=workflow.id,
        name="Good Credit",
        conditions={"field": "credit_score", "operator": ">", "value": 700}
    )

    db.add(rule_reject)
    db.add(rule_approve)
    db.commit()
    db.refresh(rule_reject)
    db.refresh(rule_approve)

    print("Seeding Transitions...")
    # INIT -> VALIDATION (unconditional)
    t1 = Transition(workflow_id=workflow.id, from_state_id=state_objects["INIT"].id, to_state_id=state_objects["VALIDATION"].id, priority=1)
    
    # VALIDATION -> RULE_EVALUATION (unconditional, after ssn fetch)
    t2 = Transition(workflow_id=workflow.id, from_state_id=state_objects["VALIDATION"].id, to_state_id=state_objects["RULE_EVALUATION"].id, priority=1)
    
    # RULE_EVALUATION -> REJECTED (if income too low)
    t3 = Transition(workflow_id=workflow.id, from_state_id=state_objects["RULE_EVALUATION"].id, to_state_id=state_objects["REJECTED"].id, rule_id=rule_reject.id, priority=10)
    
    # RULE_EVALUATION -> APPROVED (if good credit)
    t4 = Transition(workflow_id=workflow.id, from_state_id=state_objects["RULE_EVALUATION"].id, to_state_id=state_objects["APPROVED"].id, rule_id=rule_approve.id, priority=20)
    
    # RULE_EVALUATION -> MANUAL_REVIEW (fallback if no rules matched)
    t5 = Transition(workflow_id=workflow.id, from_state_id=state_objects["RULE_EVALUATION"].id, to_state_id=state_objects["MANUAL_REVIEW"].id, rule_id=None, priority=100)

    db.add_all([t1, t2, t3, t4, t5])
    db.commit()

    print("Seed complete.")
    print(f"Workflow ID to use: {workflow.id}")
    
    db.close()

if __name__ == "__main__":
    seed_db()
