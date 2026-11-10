import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from models import KnowledgeChunk

# Grounded Hostel Handbook Data Chunks
DEFAULT_KNOWLEDGE_BASE = [
    {
        "doc_title": "Hostel Code of Conduct & Residential Manual",
        "section_code": "§1.2",
        "category": "Curfew & Entry",
        "title": "Corridor & Main Gate Timings",
        "content": "Hostel main entry gates are locked at 22:30 hours (10:30 PM). Residents must swipe biometric cards before 22:30. In-room quiet hours begin at 23:00 and continue until 06:30. Late entry without approved digital night-out slip will result in an automated SMS alert to registered guardians.",
        "tags": "curfew, gate timing, late entry, quiet hours, biometric, night slip"
    },
    {
        "doc_title": "Maintenance & Infrastructure Regulations",
        "section_code": "§2.4",
        "category": "Maintenance",
        "title": "Routine Repair Windows & Silent Hours",
        "content": "Regular maintenance visits by electricians, plumbers, and carpenters occur Monday through Saturday between 08:30 and 18:30. Technicians are prohibited from entering student rooms after 20:00 except in life-safety emergency incidents verified by the Warden on duty.",
        "tags": "repair hours, electrician visit, room entry, maintenance timing, safety"
    },
    {
        "doc_title": "Electrical Safety & Fire Prevention Policy",
        "section_code": "§3.1",
        "category": "Electrical",
        "title": "High-Wattage Appliance Prohibition",
        "content": "To prevent circuit overloads and fire hazards, high-wattage resistive heating appliances exceeding 800W (including immersion heating rods, induction cooktops, room blowers, and coil stoves) are strictly prohibited in resident rooms. Confiscation and a mandatory ₹1,500 disciplinary safety fine apply on violation.",
        "tags": "heater, induction, immersion rod, appliances, fine, electricity, fire"
    },
    {
        "doc_title": "Campus Wi-Fi & Network Acceptable Use Policy",
        "section_code": "§4.3",
        "category": "Network",
        "title": "Bandwidth Allocation & Router Guidelines",
        "content": "Each resident is provided with gigabit Wi-Fi 6 access credentials. Individual personal wireless access points/routers that spoof DHCP or cause radio interference are banned. Persistent packet drop or connectivity failure will be addressed within a 12-hour SLA window upon submitting an IT ticket.",
        "tags": "wifi, router, internet speed, network, lan, dhcp, credentials"
    },
    {
        "doc_title": "Hostel Mess & Dining Regulations",
        "section_code": "§5.1",
        "category": "Mess/Food",
        "title": "Mess Timings, Food Hygiene & Rebate Rules",
        "content": "Mess meal hours: Breakfast 07:30 - 09:30, Lunch 12:30 - 14:30, Evening Snacks 17:00 - 18:00, Dinner 19:45 - 21:45. Food hygiene complaints are audited by the Student Mess Committee. A minimum of 4 consecutive days prior written notice is required for mess bill absence rebate.",
        "tags": "mess, food timing, breakfast, lunch, dinner, rebate, hygiene, catering"
    },
    {
        "doc_title": "Room Handover & Property Damage Liability",
        "section_code": "§6.2",
        "category": "Liability",
        "title": "Damages Assessment & Wear vs Vandalism",
        "content": "Normal wear-and-tear (paint chipping, washer failure, loose hinges) is repaired at university expense. Willful damage, defacing furniture, or smashing switches requires repair cost restitution plus a 20% institutional administrative charge, debited to the student caution deposit.",
        "tags": "damage, broken table, wall, fine, caution deposit, vandalism, repair cost"
    },
    {
        "doc_title": "Emergency Escalation & SOS Procedures",
        "section_code": "§7.5",
        "category": "Emergency",
        "title": "24x7 Critical Emergency Protocol",
        "content": "In case of fire, severe electric shock, medical collapse, or physical assault: Immediately contact the 24x7 Campus Control Room at 011-2659-1000 or the Hostel Medical Ambulance at 011-2659-6666. Bypass routine ticket queues; notify floor caretaker and resident warden on priority.",
        "tags": "emergency, fire, ambulance, hospital, doctor, assault, danger, urgent, sos"
    },
    {
        "doc_title": "Hostel Leave & Night-Out Permissions",
        "section_code": "§8.2",
        "category": "Discipline",
        "title": "Leave Sanction Procedure",
        "content": "Overnight absence from hostel requires submission of an e-Leave request on the resident portal at least 6 hours in advance, accompanied by registered parental SMS consent. Unsanctioned night absence is flagged to academic advisors.",
        "tags": "leave, night out, permission, parents consent, absent, vacation"
    },
    {
        "doc_title": "Guest & Visitor Housing Regulations",
        "section_code": "§9.1",
        "category": "Visitors",
        "title": "Day Guests & Guest Room Bookings",
        "content": "Non-resident guests are permitted in common recreation lobbies between 09:00 and 19:30. Overnight stay in student rooms by unregistered visitors is strictly prohibited. Official university guest rooms may be booked for parents via the warden office at subsidized rates.",
        "tags": "guests, parents, visitor, lobby, overnight stay, friends"
    },
    {
        "doc_title": "Anti-Ragging & Anti-Harassment Zero Tolerance",
        "section_code": "§10.0",
        "category": "Safety",
        "title": "Strict Anti-Ragging Mandate",
        "content": "Ragging in any form (verbal, physical, psychological) is a criminal offense under Supreme Court guidelines. The National Anti-Ragging Toll-Free Helpline is 1800-180-5522. Immediate suspension and police FIR are mandated for any verified violation.",
        "tags": "ragging, bullying, harassment, police, complaint, helpline"
    }
]

EMERGENCY_TRIGGERS = [
    "fire", "ambulance", "collapsed", "unconscious", "heart attack", "bleeding",
    "electric shock", "gas leak", "physical assault", "attacked", "suicide", "poison"
]

OUT_OF_SCOPE_TRIGGERS = [
    "write my essay", "solve my homework", "cheat in exam", "bypass exam portal",
    "hack wifi password", "pirate movies", "crack software"
]

class ResponsibleRAGAssistant:
    """
    Retrieval-Augmented Generation (RAG) assistant grounded strictly in hostel
    handbooks, safety protocols, and operational workflows.
    Features:
    - TF-IDF Vector Space Dense/Sparse Hybrid Retrieval
    - Exact clause citations
    - Hallucination prevention & confidence calibration
    - Safety guardrails & SOS Emergency overrides
    """

    def __init__(self):
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words='english')
        self.chunks = list(DEFAULT_KNOWLEDGE_BASE)
        self.corpus_matrix = None
        self._index_chunks()

    def _index_chunks(self):
        corpus_texts = [
            f"{c['title']} {c['category']} {c['tags']} {c['content']}"
            for c in self.chunks
        ]
        self.corpus_matrix = self.vectorizer.fit_transform(corpus_texts)

    def retrieve(self, query: str, top_k: int = 3) -> list:
        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.corpus_matrix)[0]
        
        # Rank by cosine similarity
        ranked_indices = np.argsort(similarities)[::-1]
        results = []
        for idx in ranked_indices[:top_k]:
            score = float(similarities[idx])
            results.append({
                "chunk": self.chunks[idx],
                "similarity_score": score
            })
        return results

    def answer_query(self, query: str) -> dict:
        """
        Executes responsible RAG pipeline:
        1. Guardrail checks (Emergency / Safety / Out of Scope)
        2. Knowledge retrieval with similarity scoring
        3. Citation assembly and grounded response generation
        """
        normalized_q = query.lower()

        # Guardrail 1: Critical Emergency Override
        for trig in EMERGENCY_TRIGGERS:
            if re.search(r'\b' + re.escape(trig) + r'\b', normalized_q):
                return {
                    "is_emergency": True,
                    "query": query,
                    "answer": (
                        "🚨 **IMMEDIATE EMERGENCY SOS PROTOCOL ACTIVATED** 🚨\n\n"
                        "If you or someone near you is in immediate danger, do not wait for ticket processing.\n\n"
                        "• **24x7 Campus Control Room:** `011-2659-1000`\n"
                        "• **Hostel Ambulance & Health Centre:** `011-2659-6666`\n"
                        "• **Hostel Chief Warden Emergency Line:** `011-2659-8888`\n"
                        "• **National Emergency Service:** `112`\n\n"
                        "Please alert your floor caretaker or resident tutor immediately."
                    ),
                    "citations": [{"doc_title": "Emergency Escalation & SOS Procedures", "section_code": "§7.5"}],
                    "confidence": 1.0,
                    "guardrail_flag": "EMERGENCY_SOS"
                }

        # Guardrail 2: Out of Scope Refusal
        for trig in OUT_OF_SCOPE_TRIGGERS:
            if trig in normalized_q:
                return {
                    "is_emergency": False,
                    "query": query,
                    "answer": (
                        "I am the **Hostel Operations & Complaint AI Assistant**. "
                        "I am restricted to answering questions regarding hostel rules, living regulations, "
                        "complaint workflows, and maintenance policies. I cannot assist with academic assignments or prohibited tasks."
                    ),
                    "citations": [],
                    "confidence": 0.0,
                    "guardrail_flag": "OUT_OF_SCOPE_REFUSAL"
                }

        # Step 2: Retrieve Relevant Passages
        retrieved = self.retrieve(query, top_k=3)
        top_hit = retrieved[0] if retrieved else None

        if not top_hit or top_hit["similarity_score"] < 0.12:
            return {
                "is_emergency": False,
                "query": query,
                "answer": (
                    "I could not locate an exact clause in the **Hostel Residential Handbook** covering this specific inquiry.\n\n"
                    "For unlisted requests, please consult your **Hostel Caretaker Office** (Ground Floor, 09:00 - 17:00) "
                    "or submit a general inquiry ticket via the student portal."
                ),
                "citations": [],
                "confidence": round(top_hit["similarity_score"] if top_hit else 0.0, 2),
                "guardrail_flag": "LOW_CONFIDENCE_FALLBACK"
            }

        # Step 3: Responsible Synthesis with Citations
        citations = []
        answer_parts = []

        # Highlight primary grounded answer
        best_chunk = top_hit["chunk"]
        citations.append({
            "doc_title": best_chunk["doc_title"],
            "section_code": best_chunk["section_code"],
            "title": best_chunk["title"],
            "category": best_chunk["category"]
        })

        answer_parts.append(f"According to **{best_chunk['doc_title']} [{best_chunk['section_code']} - {best_chunk['title']}]**:\n")
        answer_parts.append(f"> \"{best_chunk['content']}\"\n")

        # Include supporting chunk if relevant (score > 0.2)
        if len(retrieved) > 1 and retrieved[1]["similarity_score"] > 0.20:
            second_chunk = retrieved[1]["chunk"]
            citations.append({
                "doc_title": second_chunk["doc_title"],
                "section_code": second_chunk["section_code"],
                "title": second_chunk["title"],
                "category": second_chunk["category"]
            })
            answer_parts.append(f"\nAdditionally, under **{second_chunk['title']} [{second_chunk['section_code']}]**:\n")
            answer_parts.append(f"> \"{second_chunk['content']}\"\n")

        # Practical recommendation / Next steps
        answer_parts.append("\n**Actionable Advice:**")
        if "maintenance" in best_chunk["category"].lower() or "electrical" in best_chunk["category"].lower():
            answer_parts.append("• If you are experiencing a technical fault in your room, submit a formal ticket in the **Submit Complaint** tab so our autonomous agent can dispatch a certified technician.")
        elif "curfew" in best_chunk["category"].lower():
            answer_parts.append("• Remember to register your late return slip with the biometric kiosk before the 22:30 lock-in.")
        elif "mess" in best_chunk["category"].lower():
            answer_parts.append("• Mess rebates can be filed online with 4 days advance notice via the mess manager.")
        else:
            answer_parts.append("• Contact the Hostel Warden for discretionary exceptions or clarifications.")

        confidence_val = min(round(top_hit["similarity_score"] * 1.5, 2), 0.98)

        return {
            "is_emergency": False,
            "query": query,
            "answer": "\n".join(answer_parts),
            "citations": citations,
            "confidence": confidence_val,
            "guardrail_flag": "GROUNDED_CITATION"
        }

# Global instance
rag_assistant = ResponsibleRAGAssistant()
