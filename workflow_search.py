import heapq

class WorkflowNode:
    def __init__(self, node_id, title, category, duration_minutes, cost, requires_permit=False, noise_level="LOW", description=""):
        self.node_id = node_id
        self.title = title
        self.category = category
        self.duration_minutes = duration_minutes
        self.cost = cost
        self.requires_permit = requires_permit
        self.noise_level = noise_level # LOW, MEDIUM, HIGH
        self.description = description

    def to_dict(self):
        return {
            "node_id": self.node_id,
            "title": self.title,
            "category": self.category,
            "duration_minutes": self.duration_minutes,
            "cost": self.cost,
            "requires_permit": self.requires_permit,
            "noise_level": self.noise_level,
            "description": self.description
        }

class WorkflowEdge:
    def __init__(self, source_id, target_id, condition="", transition_cost=0):
        self.source_id = source_id
        self.target_id = target_id
        self.condition = condition
        self.transition_cost = transition_cost

    def to_dict(self):
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "condition": self.condition,
            "transition_cost": self.transition_cost
        }

class WorkflowSearchEngine:
    """
    Graph-based workflow engine that searches and computes the optimal
    resolution workflow path for any hostel complaint category using A* / Dijkstra.
    """

    def __init__(self):
        self.nodes = {}
        self.edges = {} # source_id -> list of (target_id, edge)
        self.categories = set()
        self._build_domain_graphs()

    def add_node(self, node: WorkflowNode):
        self.nodes[node.node_id] = node
        self.categories.add(node.category)
        if node.node_id not in self.edges:
            self.edges[node.node_id] = []

    def add_edge(self, edge: WorkflowEdge):
        if edge.source_id not in self.edges:
            self.edges[edge.source_id] = []
        self.edges[edge.source_id].append((edge.target_id, edge))

    def _build_domain_graphs(self):
        # 1. ELECTRICAL WORKFLOW
        self.add_node(WorkflowNode("ELEC_START", "Safety Assessment & MCB Power Cut", "Electrical", 15, 0, False, "LOW", "Technician shuts off breaker panel and verifies zero-voltage."))
        self.add_node(WorkflowNode("ELEC_DIAG", "Multimeter & Insulation Test", "Electrical", 20, 50, False, "LOW", "Check line resistance, ground earthing, and detect circuit shorts."))
        self.add_node(WorkflowNode("ELEC_MINOR", "Fuse & Switch Re-wiring", "Electrical", 30, 150, False, "LOW", "Replace burnt capacitor, modular switch, or tripped breaker."))
        self.add_node(WorkflowNode("ELEC_MAJOR", "Internal Conduit Cable Relaying", "Electrical", 90, 800, True, "HIGH", "Requisition new armored wire and pull through floor conduit."))
        self.add_node(WorkflowNode("ELEC_TEST", "Load Balance & Earthing Check", "Electrical", 15, 0, False, "LOW", "Test under maximum appliance load to ensure no heating."))
        self.add_node(WorkflowNode("ELEC_FINISH", "Power Restoration & Sign-off", "Electrical", 10, 0, False, "LOW", "Energize circuit and collect student digital sign-off."))

        self.add_edge(WorkflowEdge("ELEC_START", "ELEC_DIAG", "Circuit isolated"))
        self.add_edge(WorkflowEdge("ELEC_DIAG", "ELEC_MINOR", "Simple component failure"))
        self.add_edge(WorkflowEdge("ELEC_DIAG", "ELEC_MAJOR", "Melted line / conduit burnt"))
        self.add_edge(WorkflowEdge("ELEC_MINOR", "ELEC_TEST", "Wiring replaced"))
        self.add_edge(WorkflowEdge("ELEC_MAJOR", "ELEC_TEST", "Conduit relay complete"))
        self.add_edge(WorkflowEdge("ELEC_TEST", "ELEC_FINISH", "Safety passed"))

        # 2. PLUMBING WORKFLOW
        self.add_node(WorkflowNode("PLUMB_START", "Main Riser Isolation", "Plumbing", 10, 0, False, "LOW", "Turn off ball valve on wing riser to stop active overflow."))
        self.add_node(WorkflowNode("PLUMB_DIAG", "Pressure & Endoscope Leak Inspection", "Plumbing", 20, 100, False, "LOW", "Pinpoint crack origin, joint displacement, or drain obstruction."))
        self.add_node(WorkflowNode("PLUMB_CLEAR", "High-Pressure Snake Drain Clean", "Plumbing", 35, 200, False, "MEDIUM", "Clear hair and debris blockages from shower drain/p-trap."))
        self.add_node(WorkflowNode("PLUMB_REPLACE", "Pipe Joint Solvent Welding", "Plumbing", 60, 450, True, "MEDIUM", "Cut fractured CPVC pipe and bond new socket fittings."))
        self.add_node(WorkflowNode("PLUMB_PRESSURE", "Hydrostatic Leak Test (30min)", "Plumbing", 30, 0, False, "LOW", "Pressurize line to 3 bar and verify no seepage."))
        self.add_node(WorkflowNode("PLUMB_FINISH", "Dry Sanitization & Handover", "Plumbing", 15, 50, False, "LOW", "Disinfect work zone and secure resident sign-off."))

        self.add_edge(WorkflowEdge("PLUMB_START", "PLUMB_DIAG", "Water halted"))
        self.add_edge(WorkflowEdge("PLUMB_DIAG", "PLUMB_CLEAR", "Blockage detected"))
        self.add_edge(WorkflowEdge("PLUMB_DIAG", "PLUMB_REPLACE", "Pipe fissure detected"))
        self.add_edge(WorkflowEdge("PLUMB_CLEAR", "PLUMB_PRESSURE", "Drain clear"))
        self.add_edge(WorkflowEdge("PLUMB_REPLACE", "PLUMB_PRESSURE", "Bonding cured"))
        self.add_edge(WorkflowEdge("PLUMB_PRESSURE", "PLUMB_FINISH", "Pressure holds steady"))

        # 3. WI-FI / NETWORK WORKFLOW
        self.add_node(WorkflowNode("NET_START", "SNMP Telemetry & Port Ping", "Wi-Fi/Network", 5, 0, False, "LOW", "Automated gateway ping and packet drop diagnostic."))
        self.add_node(WorkflowNode("NET_DIAG", "Spectrum Analysis & SSID Jitter Check", "Wi-Fi/Network", 15, 0, False, "LOW", "Check co-channel interference and 5GHz/2.4GHz RSSI."))
        self.add_node(WorkflowNode("NET_REBOOT", "PoE Remote Switch Cycle", "Wi-Fi/Network", 10, 0, False, "LOW", "Power cycle access point remotely via manageable PoE switch."))
        self.add_node(WorkflowNode("NET_HARDWARE", "AP Hardware Swap & Cat6 Re-crimp", "Wi-Fi/Network", 45, 600, False, "LOW", "Replace damaged RJ45 connector or faulty Ubiquiti/Cisco AP."))
        self.add_node(WorkflowNode("NET_TEST", "Speedtest & Latency Verification (>100Mbps)", "Wi-Fi/Network", 10, 0, False, "LOW", "Verify latency < 15ms and bandwidth within QoS bracket."))
        self.add_node(WorkflowNode("NET_FINISH", "Radius Log Validation & Close", "Wi-Fi/Network", 5, 0, False, "LOW", "Verify student device authentication in 802.1x radius."))

        self.add_edge(WorkflowEdge("NET_START", "NET_DIAG", "Telemetry collected"))
        self.add_edge(WorkflowEdge("NET_DIAG", "NET_REBOOT", "Software hang / lease overflow"))
        self.add_edge(WorkflowEdge("NET_DIAG", "NET_HARDWARE", "Hardware PHY link failure"))
        self.add_edge(WorkflowEdge("NET_REBOOT", "NET_TEST", "Reboot complete"))
        self.add_edge(WorkflowEdge("NET_HARDWARE", "NET_TEST", "AP mounted"))
        self.add_edge(WorkflowEdge("NET_TEST", "NET_FINISH", "Speedtest passed"))

        # 4. CARPENTRY / FURNITURE / DOORS WORKFLOW
        self.add_node(WorkflowNode("CARP_START", "Damage Survey & Hinge Audit", "Carpentry", 10, 0, False, "LOW", "Check wood alignment, lock tumbler, or study table structural joint."))
        self.add_node(WorkflowNode("CARP_LUB", "Alignment & Lubrication Service", "Carpentry", 20, 60, False, "LOW", "Adjust hinge screws, graphite powder on lock mechanism."))
        self.add_node(WorkflowNode("CARP_REPAIR", "Mortise Lock Core / Bracket Replacement", "Carpentry", 50, 400, False, "MEDIUM", "Chisel wood pocket and mount hardened steel lock set."))
        self.add_node(WorkflowNode("CARP_FINISH", "Key Duplication & Handover", "Carpentry", 15, 100, False, "LOW", "Provide 2 fresh keys and log in security master register."))

        self.add_edge(WorkflowEdge("CARP_START", "CARP_LUB", "Minor friction/squeak"))
        self.add_edge(WorkflowEdge("CARP_START", "CARP_REPAIR", "Broken cylinder or split wood"))
        self.add_edge(WorkflowEdge("CARP_LUB", "CARP_FINISH", "Smooth movement restored"))
        self.add_edge(WorkflowEdge("CARP_REPAIR", "CARP_FINISH", "New lock installed"))

        # 5. MESS / FOOD WORKFLOW
        self.add_node(WorkflowNode("MESS_START", "Kitchen Batch Quarantine", "Mess/Food", 15, 0, True, "LOW", "Segregate suspect food batch and preserve sample in sterile cold storage."))
        self.add_node(WorkflowNode("MESS_INSPECT", "Catering Hygiene & Water Filter Audit", "Mess/Food", 30, 0, False, "LOW", "Inspect RO water TDS, prep counters, and cook hygiene logs."))
        self.add_node(WorkflowNode("MESS_ACTION", "Vendor Penalty & Alternate Meal Dispatch", "Mess/Food", 45, 1200, True, "LOW", "Invoke contract SLA penalty on catering contractor and serve fresh meal."))
        self.add_node(WorkflowNode("MESS_FINISH", "Mess Committee Report Publication", "Mess/Food", 20, 0, False, "LOW", "Publish transparent report to hostel residents portal."))

        self.add_edge(WorkflowEdge("MESS_START", "MESS_INSPECT", "Samples locked"))
        self.add_edge(WorkflowEdge("MESS_INSPECT", "MESS_ACTION", "Deficiency validated"))
        self.add_edge(WorkflowEdge("MESS_ACTION", "MESS_FINISH", "Corrective measure taken"))

        # 6. CLEANLINESS / HYGIENE WORKFLOW
        self.add_node(WorkflowNode("CLEAN_START", "Sanitation Site Inspection", "Cleanliness/Sanitation", 10, 0, False, "LOW", "Assess mess, garbage accumulation, or spill hazard."))
        self.add_node(WorkflowNode("CLEAN_EXEC", "Deep Industrial Clean & Disinfection", "Cleanliness/Sanitation", 40, 150, False, "MEDIUM", "Chemical degreasing, mop with hospital-grade disinfectant."))
        self.add_node(WorkflowNode("CLEAN_FINISH", "Odor Neutralization & Warden Check", "Cleanliness/Sanitation", 15, 50, False, "LOW", "Supervisor inspection and signoff."))

        self.add_edge(WorkflowEdge("CLEAN_START", "CLEAN_EXEC", "Cleaning crew deployed"))
        self.add_edge(WorkflowEdge("CLEAN_EXEC", "CLEAN_FINISH", "Area sanitized"))

    def get_category_endpoints(self, category: str):
        cat_nodes = [n for n in self.nodes.values() if n.category.lower() == category.lower()]
        if not cat_nodes:
            # Fallback to Electrical
            cat_nodes = [n for n in self.nodes.values() if n.category == "Electrical"]

        start_nodes = [n for n in cat_nodes if n.node_id.endswith("_START")]
        end_nodes = [n for n in cat_nodes if n.node_id.endswith("_FINISH")]

        start_id = start_nodes[0].node_id if start_nodes else cat_nodes[0].node_id
        end_id = end_nodes[0].node_id if end_nodes else cat_nodes[-1].node_id
        return start_id, end_id

    def search_optimal_workflow(self, category: str, criterion: str = "FASTEST", is_curfew_hours: bool = False):
        """
        Searches the workflow graph using A* / Dijkstra search.
        Criteria:
        - FASTEST: Minimizes total duration in minutes.
        - LOW_COST: Minimizes total financial cost.
        - COMPREHENSIVE: Balances quality and safety tests.
        """
        start_id, end_id = self.get_category_endpoints(category)

        # Priority Queue for Dijkstra: (cost_so_far, current_node_id, path_taken)
        pq = [(0, start_id, [start_id])]
        visited = {}

        best_path = None
        best_cost = float('inf')

        while pq:
            current_cost, curr_id, path = heapq.heappop(pq)

            if curr_id in visited and visited[curr_id] <= current_cost:
                continue
            visited[curr_id] = current_cost

            if curr_id == end_id:
                best_path = path
                best_cost = current_cost
                break

            for next_id, edge in self.edges.get(curr_id, []):
                next_node = self.nodes.get(next_id)
                if not next_node:
                    continue

                # Curfew constraint: High noise tasks blocked during curfew hours
                if is_curfew_hours and next_node.noise_level == "HIGH":
                    continue # Bypass high-noise step or penalize heavily

                # Edge cost calculation
                if criterion == "FASTEST":
                    weight = next_node.duration_minutes
                elif criterion == "LOW_COST":
                    weight = next_node.cost + (next_node.duration_minutes * 0.1)
                else: # COMPREHENSIVE
                    weight = next_node.duration_minutes + (next_node.cost * 0.2)

                new_cost = current_cost + weight + edge.transition_cost
                heapq.heappush(pq, (new_cost, next_id, path + [next_id]))

        # In case no path reached (e.g. curfew pruned), fallback to standard
        if not best_path:
            best_path = [start_id, end_id]

        # Calculate metrics for the selected path
        steps_info = []
        total_mins = 0
        total_expense = 0
        requires_permit = False

        for nid in best_path:
            node = self.nodes[nid]
            steps_info.append(node.to_dict())
            total_mins += node.duration_minutes
            total_expense += node.cost
            if node.requires_permit:
                requires_permit = True

        return {
            "category": category,
            "criterion": criterion,
            "start_node": start_id,
            "end_node": end_id,
            "path": best_path,
            "steps": steps_info,
            "total_duration_minutes": total_mins,
            "total_estimated_cost": total_expense,
            "requires_permit": requires_permit
        }

    def get_full_graph_for_category(self, category: str):
        """
        Returns nodes and edges for visual rendering in the UI.
        """
        cat_nodes = [n.to_dict() for n in self.nodes.values() if n.category.lower() == category.lower()]
        node_ids = {n["node_id"] for n in cat_nodes}

        cat_edges = []
        for src_id in node_ids:
            for tgt_id, edge in self.edges.get(src_id, []):
                if tgt_id in node_ids:
                    cat_edges.append(edge.to_dict())

        return {
            "category": category,
            "nodes": cat_nodes,
            "edges": cat_edges
        }

# Global instance
workflow_engine = WorkflowSearchEngine()
