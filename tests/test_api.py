import sys
import os
import json
import time
import uuid

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import Workflow

client = TestClient(app)

def test_full_workflow_flow():
    db = SessionLocal()
    workflow = db.query(Workflow).filter(Workflow.name == "Loan Approval").first()
    db.close()

    if not workflow:
        print("Workflow 'Loan Approval' not found. Run seed_data.py first.")
        return

    print("====================================")
    print("Testing Workflow: Loan Approval")
    print("====================================")

    run_id = str(uuid.uuid4())[:8]

    # 1. Test Rejection (Income < 20k)
    response = client.post(
        "/api/requests",
        headers={"Idempotency-Key": f"test-key-reject-{run_id}"},
        json={
            "workflow_id": workflow.id,
            "payload": {
                "user_id": 1,
                "income": 15000,
                "ssn": "123-45-678"
            }
        }
    )
    print(f"Reject POST Status: {response.status_code}")
    req_id = response.json().get("id")

    # Wait for background queue / engine to run
    time.sleep(2)
    
    get_res = client.get(f"/api/requests/{req_id}")
    print(f"Reject GET Final State: {get_res.json().get('current_state')}")

    explain_res = client.get(f"/api/requests/{req_id}/explain")
    print("\nExplain Output for Rejection:")
    print(json.dumps(explain_res.json(), indent=2))
    print("\n--------------------------\n")

    # 2. Test Approval (Good Credit > 700)
    response2 = client.post(
        "/api/requests",
        headers={"Idempotency-Key": f"test-key-approve-{run_id}"},
        json={
            "workflow_id": workflow.id,
            "payload": {
                "user_id": 2,
                "income": 50000,
                "ssn": "999-99-999" # Let's assume the mock service will give a random score. We might have to run it a few times to get > 700, or we could just pass credit_score explicitly to bypass ssn mock.
            }
        }
    )
    req_id2 = response2.json()["id"]
    time.sleep(2)
    explain_res2 = client.get(f"/api/requests/{req_id2}/explain")
    print("Explain Output for Random SSN Payload:")
    print(json.dumps(explain_res2.json(), indent=2))
    print("\n--------------------------\n")

    # 3. Test Manual Review (No SSN, High Income, No rules matched)
    response3 = client.post(
        "/api/requests",
        headers={"Idempotency-Key": f"test-key-manual-{run_id}"},
        json={
            "workflow_id": workflow.id,
            "payload": {
                "user_id": 3,
                "income": 60000
                # No credit score, no SSN to fetch it
            }
        }
    )
    req_id3 = response3.json()["id"]
    time.sleep(2)
    explain_res3 = client.get(f"/api/requests/{req_id3}/explain")
    print("Explain Output for Manual Review:")
    print(json.dumps(explain_res3.json(), indent=2))


if __name__ == "__main__":
    test_full_workflow_flow()
