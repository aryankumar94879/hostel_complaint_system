import datetime
import json
import re

class HostelRuleDefinition:
    def __init__(self, rule_id, clause_code, title, category, description, constraint_type, condition_fn, action_fn):
        self.rule_id = rule_id
        self.clause_code = clause_code
        self.title = title
        self.category = category
        self.description = description
        self.constraint_type = constraint_type
        self.condition_fn = condition_fn
        self.action_fn = action_fn

class HostelRulesEngine:
    """
    Expert rules engine representing and reasoning over university hostel policies,
    constraints, curfew times, damages liability, and escalation matrices.
    """

    def __init__(self):
        self.rules = []
        self._register_default_rules()

    def register_rule(self, rule: HostelRuleDefinition):
        self.rules.append(rule)

    def _register_default_rules(self):
        # Rule 1: Curfew and Quiet Hours In-Room Access
        def curfew_condition(ctx):
            # Quiet hours: 22:00 to 07:00
            current_hour = ctx.get("current_hour", datetime.datetime.utcnow().hour)
            is_night = (current_hour >= 22 or current_hour < 7)
            is_critical = (ctx.get("severity") == "CRITICAL")
            return is_night and not is_critical

        def curfew_action(ctx):
            return {
                "flag": "CURFEW_RESTRICTION",
                "severity_override": None,
                "requires_permit": "Warden Special Night Entry Permit",
                "message": "Routine in-room repairs are strictly prohibited between 22:00 and 07:00 under §2.4. Rescheduling to 08:30 AM unless elevated to Emergency CRITICAL."
            }

        self.register_rule(HostelRuleDefinition(
            rule_id="RULE_CURFEW_01",
            clause_code="§2.4",
            title="Quiet Hours & In-Room Repair Restriction",
            category="Curfew & Access",
            description="No staff entry or loud repair work in residential corridors between 22:00 and 07:00 unless emergency life-safety hazard.",
            constraint_type="RESTRICTION",
            condition_fn=curfew_condition,
            action_fn=curfew_action
        ))

        # Rule 2: Emergency Electrical Hazard Override
        def elec_hazard_condition(ctx):
            text = (ctx.get("title", "") + " " + ctx.get("description", "")).lower()
            keywords = ["spark", "fire", "smoke", "shock", "blackout", "burning wire", "short circuit"]
            return ctx.get("category") == "Electrical" and any(k in text for k in keywords)

        def elec_hazard_action(ctx):
            return {
                "flag": "EMERGENCY_LIFE_SAFETY",
                "severity_override": "CRITICAL",
                "sla_hours_override": 1.5,
                "requires_permit": "Immediate MCB Shutdown Authorization",
                "message": "Hazardous electrical fault detected under §7.1. Auto-elevated to CRITICAL with 90-minute expedited SLA and emergency duty electrician alert."
            }

        self.register_rule(HostelRuleDefinition(
            rule_id="RULE_ELEC_SAFETY_02",
            clause_code="§7.1",
            title="Electrical Shock & Fire Hazard Protocol",
            category="Safety",
            description="Any report mentioning active sparks, burning smells, or live electrical shocks must bypass queue and escalate to CRITICAL within 90 minutes.",
            constraint_type="SLA_OVERRIDE",
            condition_fn=elec_hazard_condition,
            action_fn=elec_hazard_action
        ))

        # Rule 3: Unauthorized High-Wattage Appliance Check
        def appliance_condition(ctx):
            text = (ctx.get("description", "") + " " + ctx.get("title", "")).lower()
            banned_items = ["heater", "immersion rod", "induction", "air conditioner", "hot plate", "electric kettle >1000w"]
            return any(item in text for item in banned_items)

        def appliance_action(ctx):
            return {
                "flag": "POLICY_VIOLATION_UNAUTHORIZED_APPLIANCE",
                "penalty_applicable": "Confiscation + ₹1,000 fine under §4.8",
                "requires_permit": "Disciplinary Warden Inspection",
                "message": "Complaint references banned electrical heating devices. Warden notified under §4.8 regarding equipment confiscation and safety review."
            }

        self.register_rule(HostelRuleDefinition(
            rule_id="RULE_APPLIANCE_03",
            clause_code="§4.8",
            title="Unauthorized High-Wattage Heating Appliance Prohibition",
            category="Discipline",
            description="Use of high-draw heating elements (heaters, immersion coils, hotplates) is banned due to fire circuit hazards. Triggers disciplinary inspection.",
            constraint_type="PENALTY",
            condition_fn=appliance_condition,
            action_fn=appliance_action
        ))

        # Rule 4: Damage Liability & Willful Destruction
        def vandalism_condition(ctx):
            text = (ctx.get("description", "") + " " + ctx.get("title", "")).lower()
            damage_words = ["broken door", "kicked", "smashed", "shattered mirror", "punched wall", "forced lock"]
            return any(w in text for w in damage_words)

        def vandalism_action(ctx):
            return {
                "flag": "DAMAGE_LIABILITY_AUDIT",
                "requires_permit": "Caretaker Joint Inventory Assessment",
                "penalty_applicable": "Replacement cost + 20% administrative surcharge",
                "message": "Potential non-wear-and-tear property damage noted under §5.2. Requires dual-signoff inspection before repair dispatch."
            }

        self.register_rule(HostelRuleDefinition(
            rule_id="RULE_VANDALISM_04",
            clause_code="§5.2",
            title="Property Damage & Resident Liability Assessment",
            category="Liability",
            description="Structural or asset breakages not attributable to routine aging require Caretaker inspection report and liability determination.",
            constraint_type="APPROVAL_GATE",
            condition_fn=vandalism_condition,
            action_fn=vandalism_action
        ))

        # Rule 5: Mess Hygiene & Mass Contamination Outbreak
        def mess_outbreak_condition(ctx):
            category = ctx.get("category", "")
            text = (ctx.get("title", "") + " " + ctx.get("description", "")).lower()
            food_hazards = ["food poisoning", "insects in food", "spoiled food", "stale", "vomit", "foul smell", "rotten"]
            return category == "Mess/Food" and any(h in text for h in food_hazards)

        def mess_outbreak_action(ctx):
            return {
                "flag": "MESS_FOOD_HEALTH_ALERT",
                "severity_override": "HIGH",
                "requires_permit": "Mess Committee & Chief Warden Immediate Audit",
                "message": "Potential food safety/hygiene breach flagged under §6.3. Kitchen vendor contract SLA clause activated with mandatory lab sample preservation."
            }

        self.register_rule(HostelRuleDefinition(
            rule_id="RULE_MESS_05",
            clause_code="§6.3",
            title="Mess Food Safety & Contamination Protocol",
            category="Health & Mess",
            description="Food quality grievances involving foreign objects or spoilage trigger immediate batch quarantine and Mess Committee audit.",
            constraint_type="APPROVAL_GATE",
            condition_fn=mess_outbreak_condition,
            action_fn=mess_outbreak_action
        ))

        # Rule 6: Water Contamination / Major Flooding
        def water_flood_condition(ctx):
            text = (ctx.get("title", "") + " " + ctx.get("description", "")).lower()
            return ctx.get("category") == "Plumbing" and any(k in text for k in ["flooding", "pipe burst", "overflowing sewage", "submerged"])

        def water_flood_action(ctx):
            return {
                "flag": "WATER_FLOOD_DISASTER",
                "severity_override": "CRITICAL",
                "sla_hours_override": 2.0,
                "requires_permit": "Main Sump Isolation Order",
                "message": "Major plumbing deluge threatening hostel floor electrical conduits under §7.3. Immediate main valve shutoff mandated."
            }

        self.register_rule(HostelRuleDefinition(
            rule_id="RULE_PLUMB_FLOOD_06",
            clause_code="§7.3",
            title="Plumbing Flooding & Sewage Emergency Protocol",
            category="Infrastructure Safety",
            description="Burst supply lines or sewage overflows require immediate water cut-off within 15 minutes and floor drainage squad deployment.",
            constraint_type="SLA_OVERRIDE",
            condition_fn=water_flood_condition,
            action_fn=water_flood_action
        ))

    def evaluate_complaint(self, complaint_context: dict) -> dict:
        """
        Executes forward reasoning on complaint context, evaluating all rules.
        Returns triggered rules, flags, overrides, and explanatory audit statements.
        """
        triggered_rules = []
        requires_permits = []
        penalties = []
        severity_override = None
        sla_override = None
        audit_explanations = []

        for rule in self.rules:
            try:
                if rule.condition_fn(complaint_context):
                    result = rule.action_fn(complaint_context)
                    triggered_rules.append({
                        "rule_id": rule.rule_id,
                        "clause_code": rule.clause_code,
                        "title": rule.title,
                        "category": rule.category,
                        "constraint_type": rule.constraint_type,
                        "result": result
                    })

                    if result.get("requires_permit"):
                        requires_permits.append(result["requires_permit"])
                    if result.get("penalty_applicable"):
                        penalties.append(result["penalty_applicable"])
                    if result.get("severity_override"):
                        severity_override = result["severity_override"]
                    if result.get("sla_hours_override"):
                        sla_override = result["sla_hours_override"]
                    if result.get("message"):
                        audit_explanations.append(f"[{rule.clause_code} - {rule.title}]: {result['message']}")
            except Exception as e:
                print(f"Error evaluating rule {rule.rule_id}: {e}")

        return {
            "has_policy_flags": len(triggered_rules) > 0,
            "triggered_rules": triggered_rules,
            "requires_permits": list(set(requires_permits)),
            "penalties": penalties,
            "severity_override": severity_override,
            "sla_override": sla_override,
            "audit_explanations": audit_explanations
        }

    def list_all_rules(self):
        return [{
            "rule_id": r.rule_id,
            "clause_code": r.clause_code,
            "title": r.title,
            "category": r.category,
            "description": r.description,
            "constraint_type": r.constraint_type
        } for r in self.rules]

# Global instance
rules_engine = HostelRulesEngine()
