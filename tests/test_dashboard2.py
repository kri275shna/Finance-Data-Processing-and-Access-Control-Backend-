import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal, Base, engine
from app.models import Request, WorkflowState, Workflow

client = TestClient(app)

def run_tests():
    db = SessionLocal()
    with engine.begin() as conn:
        Base.metadata.create_all(conn)

    # Need a workflow and state for requests to be valid
    workflow = Workflow(name="Test Workflow", description="dummy")
    try:
        db.add(workflow)
        db.commit()
        db.refresh(workflow)
        
        state = WorkflowState(workflow_id=workflow.id, name="INIT")
        db.add(state)
        db.commit()
        db.refresh(state)

        req1 = Request(workflow_id=workflow.id, current_state_id=state.id, payload={"type": "income", "amount": 5000, "category": "salary"})
        req2 = Request(workflow_id=workflow.id, current_state_id=state.id, payload={"type": "expense", "amount": 200, "category": "food"})
        req3 = Request(workflow_id=workflow.id, current_state_id=state.id, payload={"income": 1000, "category": "freelance"})
        req4 = Request(workflow_id=workflow.id, current_state_id=state.id, payload={"expense": 150, "category": "travel"})
        db.add_all([req1, req2, req3, req4])
        db.commit()
    except:
        db.rollback()

    response = client.get("/dashboard/summary")
    print("Status:", response.status_code)
    print("Response JSON:")
    print(json.dumps(response.json(), indent=2))
    db.close()

if __name__ == "__main__":
    run_tests()
