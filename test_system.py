import sys
import unittest
import json
import datetime
from app import app, db
from models import Complaint, ComplaintState, SeverityLevel, StateAuditLog, Technician, IncidentCluster
from state_machine import ComplaintStateMachine
from workflow_search import workflow_engine
from rules_engine import rules_engine
from autonomous_agent import autonomous_agent
from rag_engine import rag_assistant

class TestHostelComplaintSystem(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    # 1. TEST STATE MACHINE
    def test_state_machine_valid_and_invalid_transitions(self):
        complaint = Complaint(
            id="TEST-CMP-01",
            student_id="STU-001",
            student_name="Test Student",
            hostel_block="Block A",
            room_number="101",
            category="Electrical",
            title="Fan making noise",
            description="Ceiling fan bearing is jammed",
            state=ComplaintState.SUBMITTED
        )
        db.session.add(complaint)
        db.session.commit()

        # Valid transition: SUBMITTED -> TRIAGED
        ok, msg = ComplaintStateMachine.transition(complaint, ComplaintState.TRIAGED, "AI_AGENT", "TestAgent", "Triage step")
        self.assertTrue(ok)
        self.assertEqual(complaint.state, ComplaintState.TRIAGED)

        # Invalid transition: TRIAGED -> RESOLVED (must be assigned, in_progress, awaiting_verification first)
        ok, msg = ComplaintStateMachine.transition(complaint, ComplaintState.RESOLVED, "STUDENT", "Test Student", "Illegal jump")
        self.assertFalse(ok)
        self.assertEqual(complaint.state, ComplaintState.TRIAGED)

        # Audit log written
        logs = StateAuditLog.query.filter_by(complaint_id="TEST-CMP-01").all()
        self.assertGreaterEqual(len(logs), 1)

    # 2. TEST WORKFLOW SEARCH ENGINE (A* / DIJKSTRA)
    def test_workflow_graph_search(self):
        plan_fastest = workflow_engine.search_optimal_workflow("Electrical", criterion="FASTEST")
        self.assertIn("ELEC_START", plan_fastest["path"])
        self.assertIn("ELEC_FINISH", plan_fastest["path"])
        self.assertGreater(plan_fastest["total_duration_minutes"], 0)

        # Curfew test
        plan_curfew = workflow_engine.search_optimal_workflow("Electrical", criterion="FASTEST", is_curfew_hours=True)
        # Verify noisy step ELEC_MAJOR is not in curfew path
        self.assertNotIn("ELEC_MAJOR", plan_curfew["path"])

    # 3. TEST HOSTEL RULES REPRESENTATION & REASONING
    def test_hostel_rules_reasoning(self):
        # Electrical spark hazard
        ctx_hazard = {
            "title": "Sparking switch with smoke",
            "description": "Black smoke coming out of bedroom socket",
            "category": "Electrical",
            "severity": "MEDIUM",
            "current_hour": 14
        }
        res_hazard = rules_engine.evaluate_complaint(ctx_hazard)
        self.assertTrue(res_hazard["has_policy_flags"])
        self.assertEqual(res_hazard["severity_override"], "CRITICAL")

        # Prohibited appliance (immersion rod)
        ctx_banned = {
            "title": "Power socket tripped",
            "description": "My immersion rod caused the room light to turn off",
            "category": "Electrical",
            "severity": "LOW",
            "current_hour": 15
        }
        res_banned = rules_engine.evaluate_complaint(ctx_banned)
        self.assertTrue(any("RULE_APPLIANCE_03" in r["rule_id"] for r in res_banned["triggered_rules"]))
        self.assertTrue(len(res_banned["penalties"]) > 0)

    # 4. TEST AUTONOMOUS SERVICE AGENT
    def test_autonomous_service_agent_processing(self):
        new_cmp = Complaint(
            id="TEST-CMP-02",
            student_id="STU-002",
            student_name="Autonomous Test User",
            hostel_block="Block B",
            floor="2",
            room_number="208",
            category="Plumbing",
            title="Bathroom tap leaking water continuously",
            description="Water is dripping rapidly and won't shut off completely.",
            state=ComplaintState.SUBMITTED
        )
        db.session.add(new_cmp)
        db.session.commit()

        analysis = autonomous_agent.process_new_complaint(new_cmp)
        self.assertEqual(new_cmp.state, ComplaintState.ASSIGNED)
        self.assertIsNotNone(new_cmp.assigned_staff_name)
        self.assertGreater(len(new_cmp.optimal_workflow_path), 0)

    # 5. TEST RESPONSIBLE RAG ASSISTANT
    def test_rag_assistant_grounding_and_guardrails(self):
        # Test 1: Grounded retrieval with clause citation
        ans_curfew = rag_assistant.answer_query("What time do hostel gates close and when is curfew?")
        self.assertFalse(ans_curfew["is_emergency"])
        self.assertGreaterEqual(len(ans_curfew["citations"]), 1)
        self.assertEqual(ans_curfew["citations"][0]["section_code"], "§1.2")
        self.assertIn("22:30", ans_curfew["answer"])

        # Test 2: Emergency SOS trigger
        ans_sos = rag_assistant.answer_query("There is a fire in the corridor and someone collapsed!")
        self.assertTrue(ans_sos["is_emergency"])
        self.assertIn("011-2659-1000", ans_sos["answer"])
        self.assertEqual(ans_sos["guardrail_flag"], "EMERGENCY_SOS")

        # Test 3: Out-of-scope refusal
        ans_refusal = rag_assistant.answer_query("Please write my essay on computer networks")
        self.assertEqual(ans_refusal["guardrail_flag"], "OUT_OF_SCOPE_REFUSAL")

    # 6. TEST REST API
    def test_api_endpoints(self):
        res = self.client.get('/api/stats')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('total_tickets', data)
        self.assertIn('resolution_rate_percent', data)

        res_rules = self.client.get('/api/rules')
        self.assertEqual(res_rules.status_code, 200)
        self.assertGreaterEqual(len(res_rules.get_json()), 5)

if __name__ == '__main__':
    unittest.main()
