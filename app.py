import os
import datetime
import uuid
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from models import db, Complaint, ComplaintState, SeverityLevel, StateAuditLog, Technician, HostelRule, IncidentCluster
from state_machine import ComplaintStateMachine
from workflow_search import workflow_engine
from rules_engine import rules_engine
from autonomous_agent import autonomous_agent
from rag_engine import rag_assistant
from data_seed import seed_database

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config['SECRET_KEY'] = 'hostel-ai-complaint-system-secret-key-2026'

# Setup SQLite database path
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hostel_system.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app)
db.init_app(app)

with app.app_context():
    db.create_all()
    seed_database()

# ----------------- UI ROUTE -----------------
@app.route('/')
def index():
    return render_template('index.html')

# ----------------- COMPLAINTS API -----------------
@app.route('/api/complaints', methods=['GET'])
def list_complaints():
    state_filter = request.args.get('state')
    category_filter = request.args.get('category')
    severity_filter = request.args.get('severity')
    block_filter = request.args.get('block')
    search = request.args.get('q', '').strip().lower()

    query = Complaint.query

    if state_filter and state_filter != 'ALL':
        query = query.filter(Complaint.state == state_filter)
    if category_filter and category_filter != 'ALL':
        query = query.filter(Complaint.category == category_filter)
    if severity_filter and severity_filter != 'ALL':
        query = query.filter(Complaint.severity == severity_filter)
    if block_filter and block_filter != 'ALL':
        query = query.filter(Complaint.hostel_block == block_filter)

    complaints = query.order_by(Complaint.created_at.desc()).all()

    if search:
        complaints = [
            c for c in complaints 
            if search in c.id.lower() or search in c.title.lower() or search in c.student_name.lower() or search in c.room_number.lower()
        ]

    return jsonify([c.to_dict() for c in complaints])

@app.route('/api/complaints', methods=['POST'])
def submit_complaint():
    data = request.get_json() or {}
    
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    student_name = data.get('student_name', '').strip()
    student_id = data.get('student_id', '').strip()
    hostel_block = data.get('hostel_block', '').strip()
    room_number = data.get('room_number', '').strip()
    category = data.get('category', '').strip()
    floor = data.get('floor', '1').strip()
    student_contact = data.get('student_contact', '').strip()

    if not title or not description or not student_name or not room_number:
        return jsonify({"error": "Missing required fields (title, description, student_name, room_number)"}), 400

    # Generate sequential or unique ID
    count = Complaint.query.count() + 1001
    complaint_id = f"CMP-{count}"

    new_complaint = Complaint(
        id=complaint_id,
        student_id=student_id or f"STU-{uuid.uuid4().hex[:6].upper()}",
        student_name=student_name,
        student_contact=student_contact,
        hostel_block=hostel_block or "Block A",
        room_number=room_number,
        floor=floor,
        category=category or "Other",
        title=title,
        description=description,
        state=ComplaintState.SUBMITTED
    )

    db.session.add(new_complaint)
    db.session.commit()

    # Log submission audit
    initial_log = StateAuditLog(
        complaint_id=new_complaint.id,
        from_state="NONE",
        to_state=ComplaintState.SUBMITTED,
        actor_type="STUDENT",
        actor_name=student_name,
        reason="Initial complaint ticket filed via student portal."
    )
    db.session.add(initial_log)
    db.session.commit()

    # Hand off to Autonomous Service Agent
    agent_result = autonomous_agent.process_new_complaint(new_complaint)

    return jsonify({
        "message": "Complaint submitted and autonomously processed successfully.",
        "complaint": new_complaint.to_dict(),
        "agent_analysis": agent_result
    }), 201

@app.route('/api/complaints/<complaint_id>', methods=['GET'])
def get_complaint_detail(complaint_id):
    complaint = Complaint.query.get(complaint_id)
    if not complaint:
        return jsonify({"error": "Complaint not found"}), 404

    logs = StateAuditLog.query.filter_by(complaint_id=complaint.id).order_by(StateAuditLog.timestamp.asc()).all()
    
    # Rule evaluation snapshot
    rule_eval = rules_engine.evaluate_complaint({
        "title": complaint.title,
        "description": complaint.description,
        "category": complaint.category,
        "severity": complaint.severity,
        "current_hour": datetime.datetime.utcnow().hour
    })

    # Workflow graph details
    wf_graph = workflow_engine.get_full_graph_for_category(complaint.category)

    return jsonify({
        "complaint": complaint.to_dict(),
        "audit_logs": [l.to_dict() for l in logs],
        "rule_evaluation": rule_eval,
        "workflow_graph": wf_graph
    })

@app.route('/api/complaints/<complaint_id>/transition', methods=['POST'])
def transition_complaint_state(complaint_id):
    complaint = Complaint.query.get(complaint_id)
    if not complaint:
        return jsonify({"error": "Complaint not found"}), 404

    data = request.get_json() or {}
    target_state = data.get('target_state')
    actor_type = data.get('actor_type', 'WARDEN')
    actor_name = data.get('actor_name', 'System Admin')
    reason = data.get('reason', '')
    rating = data.get('rating')
    feedback = data.get('feedback')

    if rating:
        complaint.rating = int(rating)
    if feedback:
        complaint.feedback = feedback

    success, msg = ComplaintStateMachine.transition(
        complaint=complaint,
        next_state=target_state,
        actor_type=actor_type,
        actor_name=actor_name,
        reason=reason
    )

    if not success:
        return jsonify({"error": msg}), 400

    # If resolved or closed, decrement technician active tickets
    if target_state in [ComplaintState.RESOLVED, ComplaintState.CLOSED] and complaint.assigned_staff_id:
        tech = Technician.query.get(complaint.assigned_staff_id)
        if tech and tech.active_tickets > 0:
            tech.active_tickets -= 1

    db.session.commit()
    return jsonify({
        "message": msg,
        "complaint": complaint.to_dict()
    })

@app.route('/api/complaints/<complaint_id>/workflow-step', methods=['POST'])
def update_workflow_step(complaint_id):
    complaint = Complaint.query.get(complaint_id)
    if not complaint:
        return jsonify({"error": "Complaint not found"}), 404

    data = request.get_json() or {}
    step_id = data.get('step_id')
    
    complaint.active_workflow_step = step_id
    db.session.commit()

    return jsonify({
        "message": f"Updated active workflow step to {step_id}",
        "active_workflow_step": step_id
    })

# ----------------- WORKFLOW SEARCH API -----------------
@app.route('/api/workflow/graph/<category>', methods=['GET'])
def get_workflow_graph(category):
    graph_data = workflow_engine.get_full_graph_for_category(category)
    optimal_plan = workflow_engine.search_optimal_workflow(category, criterion="FASTEST")
    return jsonify({
        "graph": graph_data,
        "optimal_plan": optimal_plan
    })

@app.route('/api/workflow/search', methods=['POST'])
def search_workflow_plan():
    data = request.get_json() or {}
    category = data.get('category', 'Electrical')
    criterion = data.get('criterion', 'FASTEST') # FASTEST, LOW_COST, COMPREHENSIVE
    is_curfew_hours = bool(data.get('is_curfew_hours', False))

    result = workflow_engine.search_optimal_workflow(
        category=category,
        criterion=criterion,
        is_curfew_hours=is_curfew_hours
    )
    return jsonify(result)

# ----------------- RULES ENGINE API -----------------
@app.route('/api/rules', methods=['GET'])
def list_rules():
    return jsonify(rules_engine.list_all_rules())

@app.route('/api/rules/evaluate', methods=['POST'])
def evaluate_rules():
    data = request.get_json() or {}
    result = rules_engine.evaluate_complaint(data)
    return jsonify(result)

# ----------------- AUTONOMOUS AGENT API -----------------
@app.route('/api/agent/watchdog', methods=['POST'])
def run_agent_watchdog():
    actions = autonomous_agent.run_sla_watchdog()
    return jsonify({
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "actions_taken_count": len(actions),
        "actions": actions
    })

# ----------------- RESPONSIBLE RAG API -----------------
@app.route('/api/rag/chat', methods=['POST'])
def rag_chat():
    data = request.get_json() or {}
    query = data.get('query', '').strip()
    if not query:
        return jsonify({"error": "Empty question query"}), 400

    response = rag_assistant.answer_query(query)
    return jsonify(response)

# ----------------- TECHNICIANS & CLUSTERS API -----------------
@app.route('/api/technicians', methods=['GET'])
def list_technicians():
    techs = Technician.query.all()
    return jsonify([t.to_dict() for t in techs])

@app.route('/api/clusters', methods=['GET'])
def list_clusters():
    clusters = IncidentCluster.query.all()
    return jsonify([c.to_dict() for c in clusters])

# ----------------- DASHBOARD METRICS API -----------------
@app.route('/api/stats', methods=['GET'])
def get_dashboard_stats():
    now = datetime.datetime.utcnow()
    total = Complaint.query.count()
    submitted = Complaint.query.filter_by(state=ComplaintState.SUBMITTED).count()
    triaged = Complaint.query.filter_by(state=ComplaintState.TRIAGED).count()
    assigned = Complaint.query.filter_by(state=ComplaintState.ASSIGNED).count()
    in_progress = Complaint.query.filter_by(state=ComplaintState.IN_PROGRESS).count()
    escalated = Complaint.query.filter_by(state=ComplaintState.ESCALATED).count()
    awaiting_verif = Complaint.query.filter_by(state=ComplaintState.AWAITING_VERIFICATION).count()
    resolved = Complaint.query.filter_by(state=ComplaintState.RESOLVED).count()
    closed = Complaint.query.filter_by(state=ComplaintState.CLOSED).count()

    active = total - (resolved + closed)
    critical = Complaint.query.filter(
        Complaint.severity == SeverityLevel.CRITICAL,
        Complaint.state.notin_([ComplaintState.RESOLVED, ComplaintState.CLOSED])
    ).count()

    # Calculate SLA breaches
    open_tickets = Complaint.query.filter(
        Complaint.state.notin_([ComplaintState.RESOLVED, ComplaintState.CLOSED])
    ).all()
    sla_breaches = sum(1 for t in open_tickets if t.sla_deadline and t.sla_deadline < now)

    # Resolution rate
    res_rate = round((resolved + closed) / max(total, 1) * 100, 1)

    return jsonify({
        "total_tickets": total,
        "active_tickets": active,
        "critical_tickets": critical,
        "sla_breaches": sla_breaches,
        "resolution_rate_percent": res_rate,
        "counts_by_state": {
            "SUBMITTED": submitted,
            "TRIAGED": triaged,
            "ASSIGNED": assigned,
            "IN_PROGRESS": in_progress,
            "ESCALATED": escalated,
            "AWAITING_VERIFICATION": awaiting_verif,
            "RESOLVED": resolved,
            "CLOSED": closed
        }
    })

import socket

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

if __name__ == '__main__':
    local_ip = get_local_ip()
    port = 5000
    print("\n" + "=" * 68)
    print("HostelSense AI Web Server is RUNNING!")
    print(f">> On THIS PC, open:        http://localhost:{port}  or  http://127.0.0.1:{port}")
    print(f">> On ANOTHER PC, open:     http://{local_ip}:{port}")
    print("=" * 68)
    print("NOTE FOR CONNECTING FROM ANOTHER PC:")
    print(" 1. Both devices must be connected to the SAME Wi-Fi or LAN.")
    print(f" 2. On the other PC browser, type:  http://{local_ip}:{port}")
    print(" 3. If it does not load, allow Python or Port 5000 in Windows Firewall.")
    print("=" * 68 + "\n")
    app.run(host='0.0.0.0', port=port, debug=False)
