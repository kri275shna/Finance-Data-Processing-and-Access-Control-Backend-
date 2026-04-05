# Configurable Workflow Decision Platform

A production-grade backend engineered to provide dynamic, configuration-driven state machines and rule evaluation without requiring code changes for new business processes. 

Built with **FastAPI**, **SQLAlchemy** (SQLite), and **Pydantic**.

## Core Features
1. **Configurable Workflows**: Create arbitrary workflows and state mappings via API.
2. **Dynamic Rule Engine**: Configure logic boundaries (e.g. `income < 20000 -> Reject`) stored in the Database.
3. **Idempotent APIs**: Protect against duplicate requests using standard Idempotency-Key headers.
4. **Resilience & Retry Queue**: External integration failures move requests to a `RETRY` state with an exponential backoff worker polling system.
5. **Full Auditability**: Trace exactly *why* a decision was made down to the rule matching variables payload.

## Architecture Structure
- `main.py`: App creation and startup workers.
- `database.py` & `models.py`: Defines SQLite configurations and core ORM models (Workflow, Rule, Transitions, Requests, Audit, Executions).
- `schemas.py`: Request & Response models for rigorous REST API validation.
- `routes/`: Encapsulate different functional areas (Intake vs. Admin).
- `engine/`: PURE function implementation for evaluating inputs and transitioning data states.
- `queue/`: Background task to recover failed calls automatically in an asyncio loop.

## Setup & Running Locally

1. Create a virtual environment and install requirements:
   ```bash
   pip install fastapi uvicorn sqlalchemy pydantic requests
   ```

2. Seed Demo Data in SQLite:
   ```bash
   python tests/seed_data.py
   ```

3. Run API Server:
   ```bash
   uvicorn app.main:app --reload
   ```
   > Head to `http://127.0.0.1:8000/docs` to see the generated OpenAPI specs.

4. Run End-to-End Simulation:
   ```bash
   python tests/test_api.py
   ```

## APIs

**Admin APIs**
- `POST /api/admin/workflows`
- `POST /api/admin/rules`
- `POST /api/admin/transitions`

**Request Intake APIs**
- `POST /api/requests` (Requires `Idempotency-Key` Header)
- `GET /api/requests/{id}`
- `GET /api/requests/{id}/history`
- `GET /api/requests/{id}/explain` (Displays rules executed, variables at the time, and final decisions)
