import datetime
import uuid
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class ComplaintState:
    SUBMITTED = "SUBMITTED"
    TRIAGED = "TRIAGED"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    ESCALATED = "ESCALATED"
    AWAITING_VERIFICATION = "AWAITING_VERIFICATION"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"

    ALL_STATES = [
        SUBMITTED, TRIAGED, ASSIGNED, IN_PROGRESS,
        ESCALATED, AWAITING_VERIFICATION, RESOLVED, CLOSED
    ]

class SeverityLevel:
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class Complaint(db.Model):
    __tablename__ = 'complaints'

    id = db.Column(db.String(32), primary_key=True)
    student_id = db.Column(db.String(32), nullable=False)
    student_name = db.Column(db.String(100), nullable=False)
    student_contact = db.Column(db.String(32), default="")
    hostel_block = db.Column(db.String(20), nullable=False)
    room_number = db.Column(db.String(20), nullable=False)
    floor = db.Column(db.String(10), default="1")
    
    category = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    
    state = db.Column(db.String(32), default=ComplaintState.SUBMITTED, nullable=False)
    severity = db.Column(db.String(20), default=SeverityLevel.MEDIUM)
    urgency_score = db.Column(db.Float, default=50.0) # 0 - 100
    
    sla_hours = db.Column(db.Float, default=24.0)
    sla_deadline = db.Column(db.DateTime, nullable=True)
    is_escalated = db.Column(db.Boolean, default=False)
    escalation_level = db.Column(db.Integer, default=0) # 0: none, 1: Caretaker, 2: Warden, 3: Chief Warden
    
    assigned_staff_id = db.Column(db.String(32), nullable=True)
    assigned_staff_name = db.Column(db.String(100), nullable=True)
    
    optimal_workflow_path = db.Column(db.Text, default="")
    active_workflow_step = db.Column(db.String(100), default="")
    resolution_notes = db.Column(db.Text, default="")
    cluster_id = db.Column(db.String(64), nullable=True)
    
    rating = db.Column(db.Integer, nullable=True)
    feedback = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        now = datetime.datetime.utcnow()
        time_remaining = None
        sla_breached = False
        if self.sla_deadline:
            delta = self.sla_deadline - now
            time_remaining = round(delta.total_seconds() / 3600, 1)
            if self.state not in [ComplaintState.RESOLVED, ComplaintState.CLOSED]:
                sla_breached = (delta.total_seconds() < 0)

        return {
            "id": self.id,
            "student_id": self.student_id,
            "student_name": self.student_name,
            "student_contact": self.student_contact,
            "hostel_block": self.hostel_block,
            "room_number": self.room_number,
            "floor": self.floor,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "state": self.state,
            "severity": self.severity,
            "urgency_score": round(self.urgency_score, 1),
            "sla_hours": self.sla_hours,
            "sla_deadline": self.sla_deadline.isoformat() if self.sla_deadline else None,
            "sla_remaining_hours": time_remaining,
            "sla_breached": sla_breached,
            "is_escalated": self.is_escalated,
            "escalation_level": self.escalation_level,
            "assigned_staff_id": self.assigned_staff_id,
            "assigned_staff_name": self.assigned_staff_name,
            "optimal_workflow_path": self.optimal_workflow_path,
            "active_workflow_step": self.active_workflow_step,
            "resolution_notes": self.resolution_notes,
            "cluster_id": self.cluster_id,
            "rating": self.rating,
            "feedback": self.feedback,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None
        }

class StateAuditLog(db.Model):
    __tablename__ = 'state_audit_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    complaint_id = db.Column(db.String(32), db.ForeignKey('complaints.id'), nullable=False)
    from_state = db.Column(db.String(32), nullable=False)
    to_state = db.Column(db.String(32), nullable=False)
    actor_type = db.Column(db.String(32), nullable=False) # AI_AGENT, STUDENT, TECHNICIAN, WARDEN
    actor_name = db.Column(db.String(100), default="Autonomous Agent")
    reason = db.Column(db.Text, default="")
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "complaint_id": self.complaint_id,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "actor_type": self.actor_type,
            "actor_name": self.actor_name,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat()
        }

class Technician(db.Model):
    __tablename__ = 'technicians'

    id = db.Column(db.String(32), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    specialty = db.Column(db.String(50), nullable=False) # Electrical, Plumbing, Network, Carpentry, etc.
    phone = db.Column(db.String(20), default="")
    active_tickets = db.Column(db.Integer, default=0)
    is_available = db.Column(db.Boolean, default=True)
    shift_hours = db.Column(db.String(50), default="08:00 - 18:00")
    rating = db.Column(db.Float, default=4.8)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "specialty": self.specialty,
            "phone": self.phone,
            "active_tickets": self.active_tickets,
            "is_available": self.is_available,
            "shift_hours": self.shift_hours,
            "rating": self.rating
        }

class HostelRule(db.Model):
    __tablename__ = 'hostel_rules'

    rule_id = db.Column(db.String(32), primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    clause_code = db.Column(db.String(32), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    constraint_type = db.Column(db.String(50), default="RESTRICTION") # RESTRICTION, PENALTY, APPROVAL_GATE, SLA_OVERRIDE
    parameters = db.Column(db.Text, default="{}") # JSON parameters
    is_active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            "rule_id": self.rule_id,
            "title": self.title,
            "clause_code": self.clause_code,
            "category": self.category,
            "description": self.description,
            "constraint_type": self.constraint_type,
            "parameters": self.parameters,
            "is_active": self.is_active
        }

class IncidentCluster(db.Model):
    __tablename__ = 'incident_clusters'

    id = db.Column(db.String(64), primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    hostel_block = db.Column(db.String(20), nullable=False)
    floor = db.Column(db.String(10), nullable=False)
    ticket_count = db.Column(db.Integer, default=1)
    status = db.Column(db.String(32), default="ACTIVE")
    root_cause_hypothesis = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "hostel_block": self.hostel_block,
            "floor": self.floor,
            "ticket_count": self.ticket_count,
            "status": self.status,
            "root_cause_hypothesis": self.root_cause_hypothesis,
            "created_at": self.created_at.isoformat()
        }

class KnowledgeChunk(db.Model):
    __tablename__ = 'knowledge_chunks'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    doc_title = db.Column(db.String(200), nullable=False)
    section_code = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    tags = db.Column(db.String(200), default="")

    def to_dict(self):
        return {
            "id": self.id,
            "doc_title": self.doc_title,
            "section_code": self.section_code,
            "category": self.category,
            "content": self.content,
            "tags": self.tags
        }
