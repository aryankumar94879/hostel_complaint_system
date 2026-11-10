import datetime
from models import db, Complaint, ComplaintState, SeverityLevel, StateAuditLog, Technician, HostelRule, IncidentCluster, KnowledgeChunk
from rag_engine import DEFAULT_KNOWLEDGE_BASE
from rules_engine import rules_engine

def seed_database():
    """Seeds initial dataset for technicians, rules, and realistic complaints."""
    # 1. Technicians
    if Technician.query.count() == 0:
        technicians = [
            Technician(id="TECH-001", name="Ramesh Sharma", specialty="Electrical", phone="+91 98111-23401", active_tickets=2, is_available=True, shift_hours="08:00 - 18:00", rating=4.9),
            Technician(id="TECH-002", name="Karan Verma", specialty="Plumbing", phone="+91 98111-23402", active_tickets=1, is_available=True, shift_hours="08:00 - 18:00", rating=4.7),
            Technician(id="TECH-003", name="Anil Patel", specialty="Network", phone="+91 98111-23403", active_tickets=2, is_available=True, shift_hours="09:00 - 19:00", rating=4.8),
            Technician(id="TECH-004", name="Suresh Gupta", specialty="Carpentry", phone="+91 98111-23404", active_tickets=0, is_available=True, shift_hours="08:30 - 17:30", rating=4.6),
            Technician(id="TECH-005", name="Vikas Yadav", specialty="Housekeeping", phone="+91 98111-23405", active_tickets=1, is_available=True, shift_hours="06:30 - 15:30", rating=4.8),
            Technician(id="TECH-006", name="Sunita Devi", specialty="Mess Supervisor", phone="+91 98111-23406", active_tickets=1, is_available=True, shift_hours="07:00 - 21:00", rating=4.9),
            Technician(id="TECH-007", name="Dr. R. K. Mukherjee", specialty="Hostel Warden", phone="+91 98111-23407", active_tickets=1, is_available=True, shift_hours="24x7 On-Call", rating=5.0)
        ]
        db.session.add_all(technicians)
        db.session.commit()

    # 2. Hostel Rules
    if HostelRule.query.count() == 0:
        for r in rules_engine.list_all_rules():
            rule_entry = HostelRule(
                rule_id=r["rule_id"],
                title=r["title"],
                clause_code=r["clause_code"],
                category=r["category"],
                description=r["description"],
                constraint_type=r["constraint_type"]
            )
            db.session.add(rule_entry)
        db.session.commit()

    # 3. Knowledge Base Chunks
    if KnowledgeChunk.query.count() == 0:
        for c in DEFAULT_KNOWLEDGE_BASE:
            chunk = KnowledgeChunk(
                doc_title=c["doc_title"],
                section_code=c["section_code"],
                category=c["category"],
                content=c["content"],
                tags=c["tags"]
            )
            db.session.add(chunk)
        db.session.commit()

    # 4. Incident Clusters
    if IncidentCluster.query.count() == 0:
        c1 = IncidentCluster(
            id="CLUST-BLOCK-B-F3-PLUMB",
            title="3rd Floor Main Line Pressure Drop & Dry Taps",
            category="Plumbing",
            hostel_block="Block B",
            floor="3",
            ticket_count=3,
            status="ACTIVE",
            root_cause_hypothesis="Overhead tank valve #4 stuck in half-closed position affecting all odd rooms."
        )
        db.session.add(c1)
        db.session.commit()

    # 5. Complaints
    if Complaint.query.count() == 0:
        now = datetime.datetime.utcnow()

        sample_complaints = [
            Complaint(
                id="CMP-1001",
                student_id="2024CS0142",
                student_name="Aryan Sharma",
                student_contact="+91 99901-11223",
                hostel_block="Block A",
                room_number="214",
                floor="2",
                category="Electrical",
                title="Continuous sparking from main switchboard near study desk",
                description="Whenever I plug in my laptop charger, sparks fly from behind the wall plate and there is a burning ozone smell.",
                state=ComplaintState.ESCALATED,
                severity=SeverityLevel.CRITICAL,
                urgency_score=96.0,
                sla_hours=2.0,
                sla_deadline=now - datetime.timedelta(minutes=30), # Breached SLA
                is_escalated=True,
                escalation_level=2,
                assigned_staff_id="TECH-001",
                assigned_staff_name="Ramesh Sharma",
                optimal_workflow_path="ELEC_START -> ELEC_DIAG -> ELEC_MINOR -> ELEC_TEST -> ELEC_FINISH",
                active_workflow_step="ELEC_DIAG",
                created_at=now - datetime.timedelta(hours=3),
                updated_at=now - datetime.timedelta(minutes=30)
            ),
            Complaint(
                id="CMP-1002",
                student_id="2023EE0089",
                student_name="Priya Patel",
                student_contact="+91 99901-44556",
                hostel_block="Block B",
                room_number="305",
                floor="3",
                category="Plumbing",
                title="No running water in shower and tap",
                description="Tap completely dry since morning 7 AM. Other rooms on 3rd floor also seem to have no water pressure.",
                state=ComplaintState.IN_PROGRESS,
                severity=SeverityLevel.HIGH,
                urgency_score=78.0,
                sla_hours=6.0,
                sla_deadline=now + datetime.timedelta(hours=3, minutes=15),
                is_escalated=False,
                escalation_level=0,
                assigned_staff_id="TECH-002",
                assigned_staff_name="Karan Verma",
                cluster_id="CLUST-BLOCK-B-F3-PLUMB",
                optimal_workflow_path="PLUMB_START -> PLUMB_DIAG -> PLUMB_REPLACE -> PLUMB_PRESSURE -> PLUMB_FINISH",
                active_workflow_step="PLUMB_DIAG",
                created_at=now - datetime.timedelta(hours=2, minutes=45),
                updated_at=now - datetime.timedelta(hours=1)
            ),
            Complaint(
                id="CMP-1003",
                student_id="2022ME0211",
                student_name="Rohit Sundaram",
                student_contact="+91 99901-77889",
                hostel_block="Block B",
                room_number="309",
                floor="3",
                category="Plumbing",
                title="Low water pressure and sputtering air from pipes",
                description="Water trickles down very slowly, brown color sediment coming out intermittently.",
                state=ComplaintState.ASSIGNED,
                severity=SeverityLevel.HIGH,
                urgency_score=72.0,
                sla_hours=6.0,
                sla_deadline=now + datetime.timedelta(hours=4),
                is_escalated=False,
                escalation_level=0,
                assigned_staff_id="TECH-002",
                assigned_staff_name="Karan Verma",
                cluster_id="CLUST-BLOCK-B-F3-PLUMB",
                optimal_workflow_path="PLUMB_START -> PLUMB_DIAG -> PLUMB_CLEAR -> PLUMB_PRESSURE -> PLUMB_FINISH",
                active_workflow_step="PLUMB_START",
                created_at=now - datetime.timedelta(hours=2),
                updated_at=now - datetime.timedelta(hours=1, minutes=45)
            ),
            Complaint(
                id="CMP-1004",
                student_id="2024CS0302",
                student_name="Sneha Sen",
                student_contact="+91 99901-33221",
                hostel_block="Block C",
                room_number="108",
                floor="1",
                category="Wi-Fi/Network",
                title="Hostel Wi-Fi disconnecting every 2 minutes with high packet loss",
                description="Access point 'HostelC_Fl1' drops connection during online labs. Ping shows 60% packet loss to gateway 10.42.1.1.",
                state=ComplaintState.IN_PROGRESS,
                severity=SeverityLevel.MEDIUM,
                urgency_score=55.0,
                sla_hours=24.0,
                sla_deadline=now + datetime.timedelta(hours=18),
                is_escalated=False,
                escalation_level=0,
                assigned_staff_id="TECH-003",
                assigned_staff_name="Anil Patel",
                optimal_workflow_path="NET_START -> NET_DIAG -> NET_REBOOT -> NET_TEST -> NET_FINISH",
                active_workflow_step="NET_REBOOT",
                created_at=now - datetime.timedelta(hours=6),
                updated_at=now - datetime.timedelta(hours=2)
            ),
            Complaint(
                id="CMP-1005",
                student_id="2023CH0018",
                student_name="Devendra Joshi",
                student_contact="+91 99901-88990",
                hostel_block="Block A",
                room_number="412",
                floor="4",
                category="Carpentry",
                title="Room door mortise lock key cylinder stuck",
                description="Key enters halfway but won't turn. Resident unable to lock room when leaving for classes.",
                state=ComplaintState.AWAITING_VERIFICATION,
                severity=SeverityLevel.HIGH,
                urgency_score=70.0,
                sla_hours=6.0,
                sla_deadline=now + datetime.timedelta(hours=2),
                is_escalated=False,
                escalation_level=0,
                assigned_staff_id="TECH-004",
                assigned_staff_name="Suresh Gupta",
                optimal_workflow_path="CARP_START -> CARP_REPAIR -> CARP_FINISH",
                active_workflow_step="CARP_FINISH",
                resolution_notes="Mortise core replaced with new Yale tumbler set. 2 master keys issued to resident.",
                created_at=now - datetime.timedelta(hours=4),
                updated_at=now - datetime.timedelta(minutes=15)
            ),
            Complaint(
                id="CMP-1006",
                student_id="2021BT0055",
                student_name="Ananya Nair",
                student_contact="+91 99901-55443",
                hostel_block="Block Mess Hall",
                room_number="Dining Bay 2",
                floor="G",
                category="Mess/Food",
                title="Undercooked food and unhygienic water cooler tray",
                description="The dinner lentils were undercooked and the water cooler filter tray had green algae buildup.",
                state=ComplaintState.RESOLVED,
                severity=SeverityLevel.HIGH,
                urgency_score=75.0,
                sla_hours=12.0,
                sla_deadline=now - datetime.timedelta(hours=14),
                is_escalated=False,
                escalation_level=0,
                assigned_staff_id="TECH-006",
                assigned_staff_name="Sunita Devi",
                optimal_workflow_path="MESS_START -> MESS_INSPECT -> MESS_ACTION -> MESS_FINISH",
                active_workflow_step="MESS_FINISH",
                resolution_notes="Water cooler deep cleaned and filter cartridge replaced. Mess committee issued caution note to head chef.",
                rating=5,
                feedback="Super fast action by Sunita ma'am! The cooler is sparkling clean now.",
                created_at=now - datetime.timedelta(hours=26),
                updated_at=now - datetime.timedelta(hours=12),
                resolved_at=now - datetime.timedelta(hours=12)
            )
        ]

        db.session.add_all(sample_complaints)
        db.session.commit()

        # Seed corresponding audit logs
        logs = [
            StateAuditLog(complaint_id="CMP-1001", from_state="SUBMITTED", to_state="TRIAGED", actor_type="AI_AGENT", actor_name="HostelBot-Autonomous-Agent", reason="AI detected 'spark' keyword. Urgency 96/100, elevated to CRITICAL under Rule §7.1."),
            StateAuditLog(complaint_id="CMP-1001", from_state="TRIAGED", to_state="ASSIGNED", actor_type="AI_AGENT", actor_name="HostelBot-Autonomous-Agent", reason="Auto-assigned to Ramesh Sharma (Senior Electrician)."),
            StateAuditLog(complaint_id="CMP-1001", from_state="ASSIGNED", to_state="IN_PROGRESS", actor_type="TECHNICIAN", actor_name="Ramesh Sharma", reason="Checked in at Block A Room 214 with multimeter."),
            StateAuditLog(complaint_id="CMP-1001", from_state="IN_PROGRESS", to_state="ESCALATED", actor_type="AI_AGENT", actor_name="HostelBot-Autonomous-Agent", reason="SLA Watchdog: Critical 2.0hr SLA breached by 30 mins. Auto-escalated to Level 2 (Hostel Warden)."),

            StateAuditLog(complaint_id="CMP-1002", from_state="SUBMITTED", to_state="TRIAGED", actor_type="AI_AGENT", actor_name="HostelBot-Autonomous-Agent", reason="AI auto-triage: Plumbing category verified, Urgency 78/100."),
            StateAuditLog(complaint_id="CMP-1002", from_state="TRIAGED", to_state="ASSIGNED", actor_type="AI_AGENT", actor_name="HostelBot-Autonomous-Agent", reason="Grouped into cluster CLUST-BLOCK-B-F3-PLUMB. Assigned to Karan Verma."),
            StateAuditLog(complaint_id="CMP-1002", from_state="ASSIGNED", to_state="IN_PROGRESS", actor_type="TECHNICIAN", actor_name="Karan Verma", reason="Technician checking 3rd floor riser pipe valve."),

            StateAuditLog(complaint_id="CMP-1005", from_state="IN_PROGRESS", to_state="AWAITING_VERIFICATION", actor_type="TECHNICIAN", actor_name="Suresh Gupta", reason="Installed new lock core. Awaiting student signature/verification in portal.")
        ]
        db.session.add_all(logs)
        db.session.commit()
