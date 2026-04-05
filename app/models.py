import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean, JSON, JSON
from sqlalchemy.orm import relationship
from .database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)
    
    states = relationship("WorkflowState", back_populates="workflow", cascade="all, delete-orphan")
    transitions = relationship("Transition", back_populates="workflow", cascade="all, delete-orphan")
    rules = relationship("Rule", back_populates="workflow", cascade="all, delete-orphan")
    requests = relationship("Request", back_populates="workflow")

class WorkflowState(Base):
    __tablename__ = "workflow_states"

    id = Column(String, primary_key=True, default=generate_uuid)
    workflow_id = Column(String, ForeignKey("workflows.id"))
    name = Column(String, index=True) # e.g. "INIT", "APPROVED"

    workflow = relationship("Workflow", back_populates="states")

class Rule(Base):
    __tablename__ = "rules"

    id = Column(String, primary_key=True, default=generate_uuid)
    workflow_id = Column(String, ForeignKey("workflows.id"))
    name = Column(String)
    
    # Store condition as JSON, e.g. {"field": "income", "operator": "<", "value": 20000}
    # Or {"logic": "AND", "conditions": [...]}
    conditions = Column(JSON, nullable=False)

    workflow = relationship("Workflow", back_populates="rules")
    transitions = relationship("Transition", back_populates="rule")

class Transition(Base):
    __tablename__ = "transitions"

    id = Column(String, primary_key=True, default=generate_uuid)
    workflow_id = Column(String, ForeignKey("workflows.id"))
    from_state_id = Column(String, ForeignKey("workflow_states.id"))
    to_state_id = Column(String, ForeignKey("workflow_states.id"))
    
    # If null, it's an unconditional or fallback transition
    rule_id = Column(String, ForeignKey("rules.id"), nullable=True)
    
    # Lower number = higher priority to evaluate first
    priority = Column(Integer, default=0)

    workflow = relationship("Workflow", back_populates="transitions")
    from_state = relationship("WorkflowState", foreign_keys=[from_state_id])
    to_state = relationship("WorkflowState", foreign_keys=[to_state_id])
    rule = relationship("Rule", back_populates="transitions")

class Request(Base):
    __tablename__ = "requests"

    id = Column(String, primary_key=True, default=generate_uuid)
    workflow_id = Column(String, ForeignKey("workflows.id"))
    current_state_id = Column(String, ForeignKey("workflow_states.id"))
    payload = Column(JSON, nullable=False)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    workflow = relationship("Workflow", back_populates="requests")
    current_state = relationship("WorkflowState")
    audit_logs = relationship("AuditLog", back_populates="request", cascade="all, delete-orphan", order_by="AuditLog.created_at")
    rule_execution_logs = relationship("RuleExecutionLog", back_populates="request", cascade="all, delete-orphan")

class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    id = Column(String, primary_key=True, default=generate_uuid)
    key = Column(String, unique=True, index=True)
    request_id = Column(String, ForeignKey("requests.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    request = relationship("Request")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    request_id = Column(String, ForeignKey("requests.id"))
    from_state_id = Column(String, ForeignKey("workflow_states.id"), nullable=True)
    to_state_id = Column(String, ForeignKey("workflow_states.id"))
    reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    request = relationship("Request", back_populates="audit_logs")
    from_state = relationship("WorkflowState", foreign_keys=[from_state_id])
    to_state = relationship("WorkflowState", foreign_keys=[to_state_id])

class RuleExecutionLog(Base):
    __tablename__ = "rule_execution_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    request_id = Column(String, ForeignKey("requests.id"))
    rule_id = Column(String, ForeignKey("rules.id"))
    passed = Column(Boolean, nullable=False)
    details = Column(JSON, nullable=True)  # Snapshot of variables or specific checks
    executed_at = Column(DateTime, default=datetime.utcnow)

    request = relationship("Request", back_populates="rule_execution_logs")
    rule = relationship("Rule")
