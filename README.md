# HostelSense AI — Intelligent Hostel Complaint Resolution System

An intelligent, full-stack complaint resolution and policy reasoning system designed for university and residential hostels. Built with Python (Flask, SQLAlchemy, scikit-learn, NumPy) and a modern dark-themed single-page web interface.

---

## 🌟 Core Technical Capabilities

1. **Complaint State Machine (FSM)**:
   - 8-stage deterministic state machine: `SUBMITTED` ➔ `TRIAGED` ➔ `ASSIGNED` ➔ `IN_PROGRESS` ➔ `ESCALATED` ➔ `AWAITING_VERIFICATION` ➔ `RESOLVED` ➔ `CLOSED`.
   - Strict transition guards preventing illegal state jumps.
   - Real-time SLA tracking (Critical: 2h, High: 6h, Medium: 24h, Low: 48h).
   - Immutable audit trail logging actor (`AI_AGENT`, `STUDENT`, `TECHNICIAN`, `WARDEN`), timestamp, and rationale.

2. **Graph-Based Resolution Workflow Search**:
   - Maintenance tasks represented as a Directed Graph with dependencies, execution times, costs, and safety permit requirements.
   - A* and Dijkstra pathfinding engine capable of finding optimal pathways based on criteria: `FASTEST` (minimum time), `LOW_COST` (minimum financial expense), and `COMPREHENSIVE` (maximum safety testing).
   - Constraint-based pruning: High-noise repair procedures (e.g. wall drilling, conduit hammering) are automatically pruned during curfew quiet hours (22:00 - 07:00).
   - Interactive SVG/visual flow rendered in the web UI.

3. **Hostel Rules Representation & Reasoning Engine**:
   - Declarative knowledge base representing university guidelines:
     - Curfew & Quiet Hours in-room repair ban (§2.4).
     - Emergency electrical spark/fire hazard override (§7.1).
     - Prohibited high-wattage heating appliance confiscation & fines (§4.8).
     - Willful property vandalism vs wear-and-tear liability (§5.2).
     - Mess food contamination outbreak and kitchen audit protocol (§6.3).
     - Water flooding containment protocol (§7.3).
   - Real-time pre-check evaluates drafts as the student types in the portal.

4. **Autonomous Service Agent**:
   - NLP category classification and urgency scoring (0–100 index).
   - **Spatial & Temporal Incident Clustering**: Detects multi-student outages on the same floor/wing (e.g., 3rd floor water outage or block router failure) and clusters them under a single master incident.
   - **Intelligent Staff Dispatch**: Balances technician specialty, current ticket workload, and rating to auto-assign staff.
   - **Continuous SLA Watchdog**: Background process that automatically escalates tickets exceeding SLA thresholds directly to the Hostel Warden hierarchy.

5. **Responsible RAG-Based Assistant**:
   - Grounded strictly in the official *Hostel Residential Code of Conduct & Maintenance Manual*.
   - TF-IDF Vector Space Model & Dense/Sparse hybrid retrieval using `scikit-learn`.
   - **Responsible AI Guardrails**:
     - Clause-level citations (e.g. `[§1.2 - Main Gate Timings]`, `[§3.1 - High-Wattage Appliances]`).
     - Hallucination prevention with confidence calibration.
     - Out-of-scope refusal for non-hostel queries.
     - 24x7 Critical Emergency SOS trigger (immediate ambulance & campus control room hotlines).

6. **Modern Dark-Themed Web Application**:
   - Dark aesthetic with glassmorphic cards, glowing status indicators, and responsive layouts.
   - 5 full-featured views:
     - **Dashboard**: Real-time KPI counters, FSM lifecycle breakdown, incident clusters, urgent tickets.
     - **Student Portal**: Smart submission with live AI reasoning preview and ticket verification sign-off with star ratings.
     - **Workflow & Rules Hub**: Interactive graph search visualizer and policy rule inspector.
     - **Staff Dispatch**: Technician workload roster and Kanban transition board.
     - **Responsible RAG**: Grounded AI chatbot with one-click quick prompts.

---

## 🚀 How to Run

### Run Locally:
```bash
cd "C:\Users\aryan\.gemini\antigravity\scratch\hostel_complaint_system"
python app.py
```

Open your browser and navigate to:
```
http://127.0.0.1:5000
```

### Run Unit Tests:
```bash
python test_system.py
```
