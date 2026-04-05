from pydantic import BaseModel, ConfigDict, Field
from typing import Dict, Any, List, Optional
from datetime import datetime

class RequestCreate(BaseModel):
    workflow_id: str
    payload: Dict[str, Any]

class RequestResponse(BaseModel):
    id: str
    workflow_id: str
    current_state: str  # We will map current_state_id to state name in API
    retry_count: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class WorkflowStateBase(BaseModel):
    name: str

class WorkflowStateCreate(WorkflowStateBase):
    pass

class WorkflowStateResponse(WorkflowStateBase):
    id: str
    model_config = ConfigDict(from_attributes=True)

class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = None
    states: List[str]  # Just state names to bootstrap

class WorkflowResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    states: List[WorkflowStateResponse]
    model_config = ConfigDict(from_attributes=True)

class RuleCondition(BaseModel):
    field: str
    operator: str  # > , < , == , !=, contains
    value: Any

class RuleCreate(BaseModel):
    workflow_id: str
    name: str
    conditions: Dict[str, Any]  # e.g., {"field": "income", "operator": "<", "value": 20000} OR {"AND": [...]}

class RuleResponse(RuleCreate):
    id: str
    model_config = ConfigDict(from_attributes=True)

class TransitionCreate(BaseModel):
    workflow_id: str
    from_state_id: str
    to_state_id: str
    rule_id: Optional[str] = None
    priority: int = 0

class TransitionResponse(TransitionCreate):
    id: str
    model_config = ConfigDict(from_attributes=True)

class AuditLogResponse(BaseModel):
    id: str
    request_id: str
    from_state: Optional[str] = None
    to_state: str
    reason: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class RuleExecutionLogResponse(BaseModel):
    rule_name: str
    passed: bool
    details: Optional[Dict[str, Any]]
    executed_at: datetime

class ExplainResponse(BaseModel):
    request_id: str
    input_snapshot: Dict[str, Any]
    final_state: str
    decision_reason: str
    rules_evaluated: List[RuleExecutionLogResponse]
    state_history: List[AuditLogResponse]
