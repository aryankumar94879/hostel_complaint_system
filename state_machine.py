import datetime
from models import db, Complaint, ComplaintState, StateAuditLog, SeverityLevel

# Allowed transitions map: Current State -> Set of Allowed Next States
VALID_TRANSITIONS = {
    ComplaintState.SUBMITTED: [
        ComplaintState.TRIAGED,
        ComplaintState.ESCALATED,
        ComplaintState.CLOSED
    ],
    ComplaintState.TRIAGED: [
        ComplaintState.ASSIGNED,
        ComplaintState.ESCALATED,
        ComplaintState.CLOSED
    ],
    ComplaintState.ASSIGNED: [
        ComplaintState.IN_PROGRESS,
        ComplaintState.ESCALATED,
        ComplaintState.TRIAGED
    ],
    ComplaintState.IN_PROGRESS: [
        ComplaintState.AWAITING_VERIFICATION,
        ComplaintState.ESCALATED
    ],
    ComplaintState.ESCALATED: [
        ComplaintState.ASSIGNED,
        ComplaintState.IN_PROGRESS,
        ComplaintState.AWAITING_VERIFICATION
    ],
    ComplaintState.AWAITING_VERIFICATION: [
        ComplaintState.RESOLVED,
        ComplaintState.IN_PROGRESS # Student flags issue not resolved
    ],
    ComplaintState.RESOLVED: [
        ComplaintState.CLOSED,
        ComplaintState.IN_PROGRESS # Reopened if recurring
    ],
    ComplaintState.CLOSED: [
        ComplaintState.SUBMITTED # In exceptional cases reopening creates new link
    ]
}

# SLA configurations in hours
SLA_HOURS_BY_SEVERITY = {
    SeverityLevel.CRITICAL: 2.0,
    SeverityLevel.HIGH: 6.0,
    SeverityLevel.MEDIUM: 24.0,
    SeverityLevel.LOW: 48.0
}

class ComplaintStateMachine:
    """
    Finite State Machine governing the lifecycle of hostel complaints.
    Enforces valid state transitions, logs audit trails, and tracks SLAs.
    """

    @staticmethod
    def calculate_sla_deadline(severity: str, start_time: datetime.datetime = None) -> tuple[float, datetime.datetime]:
        start = start_time or datetime.datetime.utcnow()
        sla_hours = SLA_HOURS_BY_SEVERITY.get(severity, 24.0)
        deadline = start + datetime.timedelta(hours=sla_hours)
        return sla_hours, deadline

    @staticmethod
    def can_transition(current_state: str, next_state: str) -> bool:
        allowed = VALID_TRANSITIONS.get(current_state, [])
        return next_state in allowed

    @classmethod
    def transition(
        cls,
        complaint: Complaint,
        next_state: str,
        actor_type: str,
        actor_name: str,
        reason: str = ""
    ) -> tuple[bool, str]:
        """
        Executes a validated state transition, updates complaint timestamps, and writes an audit log.
        """
        current_state = complaint.state

        if current_state == next_state:
            return True, f"Complaint is already in state {next_state}."

        if not cls.can_transition(current_state, next_state):
            valid_targets = ", ".join(VALID_TRANSITIONS.get(current_state, []))
            return False, f"Illegal state transition from {current_state} to {next_state}. Valid transitions: [{valid_targets}]"

        # Apply state-specific side effects
        now = datetime.datetime.utcnow()
        complaint.state = next_state
        complaint.updated_at = now

        if next_state == ComplaintState.ESCALATED:
            complaint.is_escalated = True
            complaint.escalation_level = min(complaint.escalation_level + 1, 3)

        elif next_state == ComplaintState.RESOLVED:
            complaint.resolved_at = now
            if not complaint.resolution_notes:
                complaint.resolution_notes = reason or "Issue resolved and student verified."

        elif next_state == ComplaintState.CLOSED:
            if not complaint.resolved_at:
                complaint.resolved_at = now

        # Create audit log
        log_entry = StateAuditLog(
            complaint_id=complaint.id,
            from_state=current_state,
            to_state=next_state,
            actor_type=actor_type,
            actor_name=actor_name,
            reason=reason or f"Transitioned to {next_state} by {actor_type}"
        )
        db.session.add(log_entry)

        return True, f"Successfully moved complaint from {current_state} to {next_state}."
