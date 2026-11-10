import datetime
import re
from models import db, Complaint, ComplaintState, SeverityLevel, Technician, IncidentCluster, StateAuditLog
from state_machine import ComplaintStateMachine
from workflow_search import workflow_engine
from rules_engine import rules_engine

CATEGORY_KEYWORDS = {
    "Electrical": ["spark", "shock", "switch", "light", "bulb", "fan", "power", "blackout", "geyser", "wire", "fuse", "mcb", "socket", "short circuit", "electricity"],
    "Plumbing": ["leak", "water", "pipe", "tap", "faucet", "flush", "drain", "sewage", "basin", "clogged", "overflow", "shower", "flush valve", "no water"],
    "Wi-Fi/Network": ["wifi", "wi-fi", "internet", "lan", "router", "network", "speed", "disconnect", "ethernet", "ping", "packet drop", "portal", "login"],
    "Carpentry": ["door", "lock", "key", "window", "cupboard", "almirah", "table", "chair", "bed", "hinge", "handle", "latch", "wood", "drawer"],
    "Mess/Food": ["mess", "food", "dinner", "lunch", "breakfast", "caterer", "hygiene", "rotten", "taste", "stale", "insect", "meal", "diet", "plate"],
    "Cleanliness/Sanitation": ["dirty", "dustbin", "garbage", "trash", "clean", "sweep", "mop", "smell", "odor", "bathroom dirty", "corridor", "sanitation"],
    "Noise/Discipline": ["noise", "loud", "music", "fighting", "shouting", "curfew", "smoking", "ragging", "harassment"]
}

SEVERITY_KEYWORDS = {
    SeverityLevel.CRITICAL: ["fire", "spark", "shock", "smoke", "flood", "flooding", "blackout", "burst", "emergency", "burn", "trapped", "danger", "exploded"],
    SeverityLevel.HIGH: ["no water", "geyser", "urgent", "exam", "lock jammed", "short circuit", "food poisoning", "major leak", "broken window"],
    SeverityLevel.MEDIUM: ["slow", "faucet", "dripping", "table", "chair", "wi-fi", "internet", "light", "fan", "dustbin"],
    SeverityLevel.LOW: ["repaint", "scratched", "creak", "minor", "suggestion", "mirror smudge"]
}

class AutonomousServiceAgent:
    """
    Autonomous Service Agent responsible for:
    - Auto-triage and multi-class classification
    - Urgency scoring and priority synthesis
    - Rule engine interrogation and safety enforcement
    - Incident spatial clustering (duplicate detection)
    - Optimal resolution workflow planning
    - Technician dispatch based on skill and load
    - Continuous SLA monitoring and proactive auto-escalation
    """

    def __init__(self):
        self.agent_name = "HostelBot-Autonomous-Agent-v2.6"

    def classify_category(self, title: str, description: str) -> str:
        combined_text = (title + " " + description).lower()
        scores = {}
        for category, keywords in CATEGORY_KEYWORDS.items():
            matches = sum(1 for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', combined_text))
            scores[category] = matches

        best_category = max(scores, key=scores.get)
        if scores[best_category] > 0:
            return best_category
        return "Cleanliness/Sanitation" # Default fallback

    def compute_urgency_and_severity(self, title: str, description: str, category: str) -> tuple[float, str]:
        combined_text = (title + " " + description).lower()
        
        # Base severity detection
        detected_severity = SeverityLevel.MEDIUM
        base_score = 50.0

        for kw in SEVERITY_KEYWORDS[SeverityLevel.CRITICAL]:
            if kw in combined_text:
                detected_severity = SeverityLevel.CRITICAL
                base_score = 95.0
                break

        if detected_severity != SeverityLevel.CRITICAL:
            for kw in SEVERITY_KEYWORDS[SeverityLevel.HIGH]:
                if kw in combined_text:
                    detected_severity = SeverityLevel.HIGH
                    base_score = 75.0
                    break

        if detected_severity == SeverityLevel.MEDIUM:
            for kw in SEVERITY_KEYWORDS[SeverityLevel.LOW]:
                if kw in combined_text:
                    detected_severity = SeverityLevel.LOW
                    base_score = 25.0
                    break

        # Category specific adjustments
        if category in ["Electrical", "Plumbing"] and detected_severity == SeverityLevel.MEDIUM:
            base_score += 10.0
        elif category == "Cleanliness/Sanitation" and detected_severity == SeverityLevel.MEDIUM:
            base_score -= 10.0

        urgency_score = min(max(base_score, 10.0), 100.0)
        return urgency_score, detected_severity

    def detect_and_link_clusters(self, complaint: Complaint) -> str:
        """
        Detects if multiple complaints on the same floor/block and category exist within the past 12 hours.
        Groups them into an IncidentCluster.
        """
        twelve_hours_ago = datetime.datetime.utcnow() - datetime.timedelta(hours=12)
        
        # Look for active complaints in same block, floor, and category
        similar_tickets = Complaint.query.filter(
            Complaint.hostel_block == complaint.hostel_block,
            Complaint.floor == complaint.floor,
            Complaint.category == complaint.category,
            Complaint.id != complaint.id,
            Complaint.created_at >= twelve_hours_ago,
            Complaint.state.notin_([ComplaintState.RESOLVED, ComplaintState.CLOSED])
        ).all()

        if similar_tickets:
            # Check if any existing ticket already belongs to a cluster
            existing_cluster_id = None
            for t in similar_tickets:
                if t.cluster_id:
                    existing_cluster_id = t.cluster_id
                    break

            if existing_cluster_id:
                cluster = IncidentCluster.query.get(existing_cluster_id)
                if cluster:
                    cluster.ticket_count += 1
                    complaint.cluster_id = cluster.id
                    return cluster.id

            # Create a new cluster
            cluster_id = f"CLUST-{complaint.hostel_block}-F{complaint.floor}-{complaint.category[:4].upper()}"
            cluster = IncidentCluster(
                id=cluster_id,
                title=f"Widespread {complaint.category} Disruption on {complaint.hostel_block} Floor {complaint.floor}",
                category=complaint.category,
                hostel_block=complaint.hostel_block,
                floor=complaint.floor,
                ticket_count=len(similar_tickets) + 1,
                status="ACTIVE",
                root_cause_hypothesis=f"Multiple complaints ({len(similar_tickets) + 1} students) indicate common infrastructure outage."
            )
            db.session.add(cluster)

            # Link existing tickets as well
            for t in similar_tickets:
                t.cluster_id = cluster_id
            complaint.cluster_id = cluster_id
            return cluster_id

        return None

    def match_best_technician(self, category: str) -> Technician:
        """
        Selects best technician for the job based on specialty, availability, and active load.
        """
        # Map complaint category to technician specialty
        specialty_map = {
            "Electrical": "Electrical",
            "Plumbing": "Plumbing",
            "Wi-Fi/Network": "Network",
            "Carpentry": "Carpentry",
            "Mess/Food": "Mess Supervisor",
            "Cleanliness/Sanitation": "Housekeeping",
            "Noise/Discipline": "Hostel Warden"
        }
        target_specialty = specialty_map.get(category, "General Maintenance")

        candidates = Technician.query.filter(
            Technician.specialty.ilike(f"%{target_specialty}%")
        ).all()

        if not candidates:
            # Any available technician
            candidates = Technician.query.all()

        if not candidates:
            return None

        # Sort: available first, then lowest active tickets, then highest rating
        candidates.sort(key=lambda t: (not t.is_available, t.active_tickets, -t.rating))
        return candidates[0]

    def process_new_complaint(self, complaint: Complaint) -> dict:
        """
        Full autonomous pipeline when a new complaint is filed:
        1. Classify / verify category
        2. Score urgency & severity
        3. Evaluate hostel rules
        4. Compute resolution workflow path (A* search)
        5. Cluster spatial duplicates
        6. Dispatch technician
        7. Advance state machine: SUBMITTED -> TRIAGED -> ASSIGNED
        """
        rationale_logs = []

        # 1. Triage & Classify
        inferred_cat = self.classify_category(complaint.title, complaint.description)
        if not complaint.category or complaint.category == "Other":
            complaint.category = inferred_cat
            rationale_logs.append(f"Auto-inferred category as '{inferred_cat}'.")

        urgency, severity = self.compute_urgency_and_severity(complaint.title, complaint.description, complaint.category)
        complaint.urgency_score = urgency
        complaint.severity = severity
        rationale_logs.append(f"Assessed urgency score: {round(urgency, 1)}/100 -> Severity: {severity}.")

        # 2. Rule Reasoning
        rule_context = {
            "title": complaint.title,
            "description": complaint.description,
            "category": complaint.category,
            "severity": complaint.severity,
            "current_hour": datetime.datetime.utcnow().hour
        }
        rule_eval = rules_engine.evaluate_complaint(rule_context)
        if rule_eval["has_policy_flags"]:
            for expl in rule_eval["audit_explanations"]:
                rationale_logs.append(f"Policy Reasoner: {expl}")

            # Apply severity or SLA overrides from rules
            if rule_eval["severity_override"]:
                complaint.severity = rule_eval["severity_override"]
                rationale_logs.append(f"Severity overridden to {rule_eval['severity_override']} per safety regulation.")

        # Calculate SLA
        if rule_eval.get("sla_override"):
            complaint.sla_hours = rule_eval["sla_override"]
            complaint.sla_deadline = datetime.datetime.utcnow() + datetime.timedelta(hours=rule_eval["sla_override"])
        else:
            sla_hrs, deadline = ComplaintStateMachine.calculate_sla_deadline(complaint.severity)
            complaint.sla_hours = sla_hrs
            complaint.sla_deadline = deadline

        # Transition: SUBMITTED -> TRIAGED
        ComplaintStateMachine.transition(
            complaint,
            ComplaintState.TRIAGED,
            actor_type="AI_AGENT",
            actor_name=self.agent_name,
            reason="Autonomous triage complete: priority calculated, policy rules evaluated."
        )

        # 3. Incident Duplicate & Cluster Detection
        cluster_id = self.detect_and_link_clusters(complaint)
        if cluster_id:
            rationale_logs.append(f"Correlated with active wing incident cluster: [{cluster_id}]. Linked for joint resolution.")

        # 4. Search Resolution Workflow
        workflow_plan = workflow_engine.search_optimal_workflow(complaint.category, criterion="FASTEST")
        complaint.optimal_workflow_path = " -> ".join(workflow_plan["path"])
        complaint.active_workflow_step = workflow_plan["start_node"]
        rationale_logs.append(f"Workflow Search Engine: Synthesized optimal {len(workflow_plan['path'])}-step resolution path ({workflow_plan['total_duration_minutes']} mins ETR).")

        # 5. Autonomous Staff Dispatch
        technician = self.match_best_technician(complaint.category)
        if technician:
            complaint.assigned_staff_id = technician.id
            complaint.assigned_staff_name = technician.name
            technician.active_tickets += 1

            # Transition: TRIAGED -> ASSIGNED
            ComplaintStateMachine.transition(
                complaint,
                ComplaintState.ASSIGNED,
                actor_type="AI_AGENT",
                actor_name=self.agent_name,
                reason=f"Auto-dispatched to specialist {technician.name} ({technician.specialty}) based on lowest active ticket load ({technician.active_tickets - 1}) and rating {technician.rating}⭐."
            )
            rationale_logs.append(f"Assigned to {technician.name} ({technician.specialty}). Notification dispatched.")

        db.session.commit()

        return {
            "complaint_id": complaint.id,
            "category": complaint.category,
            "severity": complaint.severity,
            "urgency_score": complaint.urgency_score,
            "sla_hours": complaint.sla_hours,
            "assigned_staff": complaint.assigned_staff_name,
            "cluster_id": complaint.cluster_id,
            "workflow_path": complaint.optimal_workflow_path,
            "rationale_logs": rationale_logs,
            "state": complaint.state
        }

    def run_sla_watchdog(self) -> list:
        """
        Background watchdog cycle:
        Inspects all open complaints.
        Triggers automatic escalation on SLA breach or near-breach warnings.
        """
        now = datetime.datetime.utcnow()
        active_complaints = Complaint.query.filter(
            Complaint.state.notin_([ComplaintState.RESOLVED, ComplaintState.CLOSED])
        ).all()

        actions_taken = []

        for c in active_complaints:
            if not c.sla_deadline:
                continue

            delta = c.sla_deadline - now
            hours_left = delta.total_seconds() / 3600.0

            # Condition 1: Hard breach (deadline expired) and not yet escalated
            if hours_left < 0 and c.state != ComplaintState.ESCALATED:
                success, msg = ComplaintStateMachine.transition(
                    c,
                    ComplaintState.ESCALATED,
                    actor_type="AI_AGENT",
                    actor_name=self.agent_name,
                    reason=f"SLA Breach Watchdog: Target resolution deadline breached by {abs(round(hours_left, 1))}h. Auto-escalated to Level {c.escalation_level + 1} (Hostel Warden)."
                )
                actions_taken.append({
                    "complaint_id": c.id,
                    "type": "ESCALATION_BREACH",
                    "hours_overdue": abs(round(hours_left, 1)),
                    "new_state": c.state,
                    "escalation_level": c.escalation_level
                })

            # Condition 2: Warning threshold (under 25% SLA remaining)
            elif hours_left >= 0 and hours_left <= (c.sla_hours * 0.25):
                actions_taken.append({
                    "complaint_id": c.id,
                    "type": "SLA_WARNING_NEAR_BREACH",
                    "hours_left": round(hours_left, 1),
                    "assigned_staff": c.assigned_staff_name
                })

        db.session.commit()
        return actions_taken

# Global instance
autonomous_agent = AutonomousServiceAgent()
