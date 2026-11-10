/* ========================================================
   HostelSense AI — Frontend Controller & Interactivity
   ======================================================== */

// Global App State
const state = {
  activeTab: 'dashboard',
  complaints: [],
  technicians: [],
  clusters: [],
  rules: [],
  currentWorkflowCategory: 'Electrical',
  currentWorkflowCriterion: 'FASTEST',
  isCurfewHours: false
};

// DOM Content Loaded Initializer
document.addEventListener('DOMContentLoaded', () => {
  setupNavigation();
  setupEventListeners();
  loadInitialData();
  startLivePolling();
});

// Setup Tab Navigation
function setupNavigation() {
  const tabs = document.querySelectorAll('.nav-tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const target = tab.getAttribute('data-tab');
      switchTab(target);
    });
  });
}

function switchTab(tabId) {
  state.activeTab = tabId;
  document.querySelectorAll('.nav-tab').forEach(t => {
    t.classList.toggle('active', t.getAttribute('data-tab') === tabId);
  });
  document.querySelectorAll('.tab-pane').forEach(pane => {
    pane.classList.toggle('active', pane.id === `tab-${tabId}`);
  });

  // Refresh tab-specific views
  if (tabId === 'dashboard') {
    loadDashboardStats();
    loadIncidentClusters();
  } else if (tabId === 'student-portal') {
    renderStudentTickets();
  } else if (tabId === 'workflow-engine') {
    loadWorkflowGraph(state.currentWorkflowCategory, state.currentWorkflowCriterion, state.isCurfewHours);
    loadRules();
  } else if (tabId === 'staff-dispatch') {
    loadTechnicians();
    renderKanbanBoard();
  } else if (tabId === 'rag-assistant') {
    loadKnowledgeChunks();
  }
}

// Setup Event Listeners
function setupEventListeners() {
  // Complaint Form Submission
  const complaintForm = document.getElementById('complaintForm');
  if (complaintForm) {
    complaintForm.addEventListener('submit', handleComplaintSubmit);
  }

  // Real-time AI Pre-Check as user types
  const titleInput = document.getElementById('inputTitle');
  const descInput = document.getElementById('inputDescription');
  const categoryInput = document.getElementById('inputCategory');

  let debounceTimer = null;
  const triggerPrecheck = () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(runAIFormPrecheck, 400);
  };

  if (titleInput) titleInput.addEventListener('input', triggerPrecheck);
  if (descInput) descInput.addEventListener('input', triggerPrecheck);
  if (categoryInput) categoryInput.addEventListener('change', triggerPrecheck);

  // Workflow Controls
  const wfCategorySelect = document.getElementById('wfCategorySelect');
  const wfCriterionSelect = document.getElementById('wfCriterionSelect');
  const wfCurfewToggle = document.getElementById('wfCurfewToggle');
  const btnComputeWorkflow = document.getElementById('btnComputeWorkflow');

  if (btnComputeWorkflow) {
    btnComputeWorkflow.addEventListener('click', () => {
      state.currentWorkflowCategory = wfCategorySelect.value;
      state.currentWorkflowCriterion = wfCriterionSelect.value;
      state.isCurfewHours = wfCurfewToggle.checked;
      loadWorkflowGraph(state.currentWorkflowCategory, state.currentWorkflowCriterion, state.isCurfewHours);
    });
  }

  // SLA Watchdog
  const btnWatchdog = document.getElementById('btnRunWatchdog');
  if (btnWatchdog) {
    btnWatchdog.addEventListener('click', triggerSlaWatchdog);
  }

  // Kanban Filter
  const kanbanFilter = document.getElementById('kanbanCategoryFilter');
  if (kanbanFilter) {
    kanbanFilter.addEventListener('change', renderKanbanBoard);
  }

  // Student Tickets Search
  const trackerSearch = document.getElementById('trackerSearch');
  if (trackerSearch) {
    trackerSearch.addEventListener('input', (e) => {
      const q = e.target.value.toLowerCase();
      const filtered = state.complaints.filter(c => 
        c.title.toLowerCase().includes(q) || 
        c.id.toLowerCase().includes(q) || 
        c.category.toLowerCase().includes(q)
      );
      renderTicketList(filtered, 'studentTicketsList');
    });
  }

  // RAG Chat Input
  const btnSendChat = document.getElementById('btnSendChat');
  const chatInput = document.getElementById('chatInput');
  if (btnSendChat && chatInput) {
    btnSendChat.addEventListener('click', sendChatMessage);
    chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') sendChatMessage();
    });
  }
}

// Initial Data Loading
async function loadInitialData() {
  await Promise.all([
    loadDashboardStats(),
    loadComplaints(),
    loadIncidentClusters(),
    loadTechnicians(),
    loadRules(),
    loadKnowledgeChunks()
  ]);
  // Pre-load default workflow graph
  loadWorkflowGraph('Electrical', 'FASTEST', false);
}

// Real-time polling every 12 seconds for live SLA & ticket updates
function startLivePolling() {
  setInterval(async () => {
    await loadComplaints(false); // silent reload
    if (state.activeTab === 'dashboard') {
      loadDashboardStats();
    } else if (state.activeTab === 'staff-dispatch') {
      renderKanbanBoard();
    }
  }, 12000);
}

// ================= API CALLS & LOADERS =================

async function loadDashboardStats() {
  try {
    const res = await fetch('/api/stats');
    const data = await res.json();

    document.getElementById('metricActiveTickets').textContent = data.active_tickets;
    document.getElementById('metricCriticalHazards').textContent = data.critical_tickets;
    document.getElementById('metricSlaBreaches').textContent = data.sla_breaches;
    document.getElementById('metricResolutionRate').textContent = `${data.resolution_rate_percent}%`;

    // Render FSM Pipeline
    renderFsmPipeline(data.counts_by_state);
  } catch (err) {
    console.error('Error fetching dashboard stats:', err);
  }
}

function renderFsmPipeline(counts) {
  const container = document.getElementById('fsmPipelineContainer');
  if (!container) return;

  const statesOrder = [
    { key: 'SUBMITTED', label: '1. Submitted', color: 'var(--text-muted)' },
    { key: 'TRIAGED', label: '2. Triaged', color: 'var(--cyan)' },
    { key: 'ASSIGNED', label: '3. Assigned', color: 'var(--purple)' },
    { key: 'IN_PROGRESS', label: '4. In Progress', color: 'var(--blue)' },
    { key: 'ESCALATED', label: '5. Escalated', color: 'var(--rose)' },
    { key: 'AWAITING_VERIFICATION', label: '6. Verification', color: 'var(--amber)' },
    { key: 'RESOLVED', label: '7. Resolved', color: 'var(--emerald)' },
    { key: 'CLOSED', label: '8. Closed', color: '#64748b' }
  ];

  container.innerHTML = statesOrder.map(s => `
    <div class="fsm-step-card">
      <div class="fsm-step-count" style="color: ${s.color}">${counts[s.key] || 0}</div>
      <div class="fsm-step-name">${s.label}</div>
    </div>
  `).join('');
}

async function loadComplaints(showToastOnUpdate = false) {
  try {
    const res = await fetch('/api/complaints');
    state.complaints = await res.json();

    renderPriorityTickets();
    renderStudentTickets();
    renderKanbanBoard();

    if (showToastOnUpdate) {
      showToast('Complaints refreshed successfully', 'info');
    }
  } catch (err) {
    console.error('Error loading complaints:', err);
  }
}

function renderPriorityTickets() {
  const container = document.getElementById('priorityTicketsList');
  if (!container) return;

  const urgentTickets = state.complaints.filter(c => 
    c.severity === 'CRITICAL' || c.is_escalated || c.sla_breached
  );

  if (urgentTickets.length === 0) {
    container.innerHTML = '<div class="empty-state">✅ No urgent or breached tickets currently. All SLAs healthy.</div>';
    return;
  }

  container.innerHTML = urgentTickets.map(t => `
    <div class="priority-ticket-card" onclick="openComplaintModal('${t.id}')">
      <div class="ticket-header-row">
        <span class="ticket-id">${t.id}</span>
        <div>
          ${t.sla_breached ? '<span class="badge badge-rose"><i class="fa-solid fa-triangle-exclamation"></i> SLA BREACH</span>' : ''}
          <span class="badge ${getSeverityBadgeClass(t.severity)}">${t.severity}</span>
        </div>
      </div>
      <div class="ticket-title">${escapeHtml(t.title)}</div>
      <div class="ticket-footer-row">
        <span><i class="fa-solid fa-location-dot"></i> ${t.hostel_block} (Room ${t.room_number})</span>
        <span><i class="fa-solid fa-user-clock"></i> SLA: ${formatSlaRemaining(t)}</span>
        <span class="badge ${getStateBadgeClass(t.state)}">${t.state}</span>
      </div>
    </div>
  `).join('');
}

function renderStudentTickets() {
  renderTicketList(state.complaints, 'studentTicketsList');
}

function renderTicketList(tickets, containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  if (tickets.length === 0) {
    container.innerHTML = '<div class="empty-state">No complaints matching filter.</div>';
    return;
  }

  container.innerHTML = tickets.map(t => `
    <div class="student-ticket-item" onclick="openComplaintModal('${t.id}')">
      <div class="ticket-header-row">
        <span class="ticket-id">${t.id}</span>
        <div>
          <span class="badge badge-outline">${t.category}</span>
          <span class="badge ${getSeverityBadgeClass(t.severity)}">${t.severity}</span>
          <span class="badge ${getStateBadgeClass(t.state)}">${t.state}</span>
        </div>
      </div>
      <div class="ticket-title">${escapeHtml(t.title)}</div>
      <div class="ticket-footer-row">
        <span><i class="fa-solid fa-user"></i> ${escapeHtml(t.student_name)} | ${t.hostel_block} #${t.room_number}</span>
        <span><i class="fa-solid fa-wrench"></i> ${t.assigned_staff_name || 'Autonomous Agent'}</span>
        <span><i class="fa-regular fa-clock"></i> ${formatDate(t.created_at)}</span>
      </div>
    </div>
  `).join('');
}

async function loadIncidentClusters() {
  try {
    const res = await fetch('/api/clusters');
    state.clusters = await res.json();

    const countBadge = document.getElementById('clusterCountBadge');
    if (countBadge) countBadge.textContent = `${state.clusters.length} Outage Clusters`;

    const container = document.getElementById('clustersList');
    if (!container) return;

    if (state.clusters.length === 0) {
      container.innerHTML = '<div class="empty-state">No widespread multi-room incidents detected.</div>';
      return;
    }

    container.innerHTML = state.clusters.map(c => `
      <div class="cluster-card">
        <div class="cluster-title">
          <span><i class="fa-solid fa-circle-exclamation text-purple"></i> ${escapeHtml(c.title)}</span>
          <span class="badge badge-purple">${c.ticket_count} Students Affected</span>
        </div>
        <div class="cluster-hypothesis">
          <strong>Autonomous Hypothesis:</strong> ${escapeHtml(c.root_cause_hypothesis)}
        </div>
        <div class="cluster-meta">
          <span><i class="fa-solid fa-building"></i> ${c.hostel_block} (Floor ${c.floor})</span>
          <span><i class="fa-solid fa-tag"></i> ${c.category}</span>
          <span><i class="fa-solid fa-wave-square"></i> Status: ${c.status}</span>
        </div>
      </div>
    `).join('');
  } catch (err) {
    console.error('Error loading clusters:', err);
  }
}

async function loadTechnicians() {
  try {
    const res = await fetch('/api/technicians');
    state.technicians = await res.json();

    const badge = document.getElementById('activeTechCount');
    if (badge) badge.textContent = `${state.technicians.length} Staff on Roster`;

    const container = document.getElementById('technicianCardsGrid');
    if (!container) return;

    container.innerHTML = state.technicians.map(tech => `
      <div class="tech-card">
        <div class="tech-avatar">
          <i class="fa-solid fa-user-gear"></i>
        </div>
        <div class="tech-info">
          <div class="tech-name">${escapeHtml(tech.name)}</div>
          <div class="tech-specialty">${tech.specialty} • ${tech.rating}⭐</div>
          <div class="tech-workload">
            <span class="badge ${tech.active_tickets > 2 ? 'badge-amber' : 'badge-emerald'}">
              ${tech.active_tickets} Active Tickets
            </span>
            <span class="text-xs text-muted ml-1">${tech.shift_hours}</span>
          </div>
        </div>
      </div>
    `).join('');
  } catch (err) {
    console.error('Error loading technicians:', err);
  }
}

function renderKanbanBoard() {
  const container = document.getElementById('kanbanBoard');
  if (!container) return;

  const categoryFilter = document.getElementById('kanbanCategoryFilter')?.value || 'ALL';

  const columns = [
    { state: 'ASSIGNED', title: 'Assigned', color: 'var(--purple)' },
    { state: 'IN_PROGRESS', title: 'In Progress', color: 'var(--blue)' },
    { state: 'ESCALATED', title: 'Escalated (Warden)', color: 'var(--rose)' },
    { state: 'AWAITING_VERIFICATION', title: 'Awaiting Sign-off', color: 'var(--amber)' },
    { state: 'RESOLVED', title: 'Resolved & Closed', color: 'var(--emerald)' }
  ];

  let filtered = state.complaints;
  if (categoryFilter !== 'ALL') {
    filtered = filtered.filter(c => c.category === categoryFilter);
  }

  container.innerHTML = columns.map(col => {
    const ticketsInCol = filtered.filter(c => {
      if (col.state === 'RESOLVED') {
        return c.state === 'RESOLVED' || c.state === 'CLOSED';
      }
      return c.state === col.state;
    });

    return `
      <div class="kanban-col">
        <div class="kanban-col-header">
          <span style="color: ${col.color}">${col.title}</span>
          <span class="badge badge-outline">${ticketsInCol.length}</span>
        </div>
        <div class="kanban-cards-container">
          ${ticketsInCol.map(t => `
            <div class="kanban-ticket-card" onclick="openComplaintModal('${t.id}')">
              <div class="ticket-header-row">
                <span class="ticket-id">${t.id}</span>
                <span class="badge ${getSeverityBadgeClass(t.severity)}">${t.severity}</span>
              </div>
              <div class="ticket-title" style="font-size: 0.82rem;">${escapeHtml(t.title)}</div>
              <div class="ticket-footer-row">
                <span>${t.hostel_block} #${t.room_number}</span>
                <span style="color: var(--cyan);">${t.assigned_staff_name ? t.assigned_staff_name.split(' ')[0] : 'Auto'}</span>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }).join('');
}

// ================= AI FORM PRE-EVALUATION =================

async function runAIFormPrecheck() {
  const title = document.getElementById('inputTitle')?.value || '';
  const desc = document.getElementById('inputDescription')?.value || '';
  const cat = document.getElementById('inputCategory')?.value || '';
  const precheckCard = document.getElementById('aiPreCheckCard');
  const detailsBox = document.getElementById('aiPreCheckDetails');

  if (title.length < 5 && desc.length < 5) {
    precheckCard.classList.add('hidden');
    return;
  }

  try {
    const res = await fetch('/api/rules/evaluate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: title,
        description: desc,
        category: cat,
        current_hour: new Date().getHours()
      })
    });
    const evalData = await res.json();

    precheckCard.classList.remove('hidden');

    let outputHtml = [];
    if (evalData.has_policy_flags) {
      outputHtml.push(`<div class="text-amber"><strong>⚠️ Policy Warnings Triggered:</strong></div>`);
      evalData.audit_explanations.forEach(expl => {
        outputHtml.push(`<div>• ${escapeHtml(expl)}</div>`);
      });
      if (evalData.requires_permits.length > 0) {
        outputHtml.push(`<div class="text-rose mt-1"><strong>Permits Required:</strong> ${evalData.requires_permits.join(', ')}</div>`);
      }
    } else {
      outputHtml.push(`<div>✅ Standard routine request. No curfew or property damage violations flagged.</div>`);
    }

    if (evalData.severity_override) {
      outputHtml.push(`<div class="text-cyan mt-1"><strong>Safety Rule Auto-Elevation:</strong> Severity elevated to ${evalData.severity_override}</div>`);
    }

    detailsBox.innerHTML = outputHtml.join('');
  } catch (err) {
    console.error('Precheck error:', err);
  }
}

// Handle Form Submission
async function handleComplaintSubmit(e) {
  e.preventDefault();
  const btn = document.getElementById('btnSubmitComplaint');
  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Autonomous Agent Triaging & Routing...`;

  const payload = {
    student_name: document.getElementById('inputStudentName').value,
    student_id: document.getElementById('inputStudentId').value,
    hostel_block: document.getElementById('inputBlock').value,
    floor: document.getElementById('inputFloor').value,
    room_number: document.getElementById('inputRoom').value,
    category: document.getElementById('inputCategory').value,
    title: document.getElementById('inputTitle').value,
    description: document.getElementById('inputDescription').value,
    student_contact: document.getElementById('inputContact').value
  };

  try {
    const res = await fetch('/api/complaints', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const result = await res.json();

    if (!res.ok) {
      showToast(result.error || 'Failed to submit complaint', 'error');
      return;
    }

    showToast(`Complaint ${result.complaint.id} created & auto-assigned to ${result.complaint.assigned_staff_name}!`, 'success');

    // Reset Form
    document.getElementById('inputTitle').value = '';
    document.getElementById('inputDescription').value = '';
    document.getElementById('aiPreCheckCard').classList.add('hidden');

    // Refresh Data
    await loadComplaints();
    await loadDashboardStats();
    await loadIncidentClusters();

    // Open detail modal to show what the agent reasoned
    openComplaintModal(result.complaint.id);

  } catch (err) {
    console.error('Submit error:', err);
    showToast('Failed to connect to server', 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="fa-solid fa-paper-plane"></i> Submit & Trigger Autonomous Resolution`;
  }
}

// ================= WORKFLOW GRAPH VISUALIZATION =================

async function loadWorkflowGraph(category, criterion, isCurfew) {
  try {
    const res = await fetch('/api/workflow/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        category: category,
        criterion: criterion,
        is_curfew_hours: isCurfew
      })
    });
    const plan = await res.json();

    renderWorkflowMetrics(plan);
    renderWorkflowVisualGraph(plan);
  } catch (err) {
    console.error('Error fetching workflow plan:', err);
  }
}

function renderWorkflowMetrics(plan) {
  const badge = document.getElementById('wfPathStepsBadge');
  if (badge) badge.textContent = `${plan.steps.length} Sequenced Steps`;

  const strip = document.getElementById('wfMetricsStrip');
  if (!strip) return;

  strip.innerHTML = `
    <div class="wf-metric-pill">
      <span>Category:</span> <strong>${plan.category}</strong>
    </div>
    <div class="wf-metric-pill">
      <span>Optimization:</span> <strong>${plan.criterion}</strong>
    </div>
    <div class="wf-metric-pill">
      <span>Total Estimated Duration:</span> <strong>${plan.total_duration_minutes} Mins</strong>
    </div>
    <div class="wf-metric-pill">
      <span>Estimated Cost:</span> <strong>₹${plan.total_estimated_cost}</strong>
    </div>
    <div class="wf-metric-pill">
      <span>Permits Gate:</span> <strong>${plan.requires_permit ? '⚠️ Warden Permit Required' : 'None'}</strong>
    </div>
  `;
}

function renderWorkflowVisualGraph(plan) {
  const container = document.getElementById('workflowGraphContainer');
  if (!container) return;

  container.innerHTML = `
    <div class="workflow-graph-flow">
      ${plan.steps.map((step, idx) => `
        <div class="wf-node optimal">
          <div class="wf-node-title">${escapeHtml(step.title)}</div>
          <div class="wf-node-meta">
            <span>⏱️ ${step.duration_minutes}m</span> • 
            <span>💰 ₹${step.cost}</span>
          </div>
          <div class="text-xs text-muted mt-1" style="font-size: 0.7rem;">${escapeHtml(step.description)}</div>
        </div>
        ${idx < plan.steps.length - 1 ? '<div class="wf-connector"><i class="fa-solid fa-arrow-right-long"></i></div>' : ''}
      `).join('')}
    </div>
  `;
}

async function loadRules() {
  try {
    const res = await fetch('/api/rules');
    state.rules = await res.json();

    const container = document.getElementById('rulesGrid');
    if (!container) return;

    container.innerHTML = state.rules.map(r => `
      <div class="rule-card">
        <div class="rule-clause">${r.clause_code} • ${r.category}</div>
        <div class="rule-title">${escapeHtml(r.title)}</div>
        <div class="rule-desc">${escapeHtml(r.description)}</div>
        <div class="mt-2">
          <span class="badge ${r.constraint_type === 'RESTRICTION' ? 'badge-rose' : r.constraint_type === 'SLA_OVERRIDE' ? 'badge-cyan' : 'badge-amber'}">
            ${r.constraint_type}
          </span>
        </div>
      </div>
    `).join('');
  } catch (err) {
    console.error('Error loading rules:', err);
  }
}

// ================= SLA WATCHDOG =================

async function triggerSlaWatchdog() {
  const btn = document.getElementById('btnRunWatchdog');
  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Checking SLAs...`;

  try {
    const res = await fetch('/api/agent/watchdog', { method: 'POST' });
    const data = await res.json();

    if (data.actions_taken_count > 0) {
      showToast(`SLA Watchdog escalated ${data.actions_taken_count} ticket(s) to Warden hierarchy!`, 'error');
    } else {
      showToast(`SLA Watchdog heartbeat passed. All active tickets within acceptable time bounds.`, 'success');
    }

    await loadComplaints();
    await loadDashboardStats();
  } catch (err) {
    console.error('Watchdog error:', err);
    showToast('Failed to run watchdog', 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="fa-solid fa-shield-halved"></i> <span>Run SLA Watchdog</span>`;
  }
}

// ================= RESPONSIBLE RAG ASSISTANT =================

async function sendChatMessage() {
  const input = document.getElementById('chatInput');
  const query = input.value.trim();
  if (!query) return;

  input.value = '';
  appendUserMessage(query);

  const botLoadingId = appendBotLoading();

  try {
    const res = await fetch('/api/rag/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query })
    });
    const result = await res.json();

    removeBotLoading(botLoadingId);
    appendBotMessage(result);
  } catch (err) {
    console.error('Chat error:', err);
    removeBotLoading(botLoadingId);
    appendBotMessage({
      answer: "I experienced a connection issue while searching the knowledge base. Please try again.",
      citations: [],
      confidence: 0.0
    });
  }
}

function sendQuickPrompt(promptText) {
  const input = document.getElementById('chatInput');
  input.value = promptText;
  sendChatMessage();
}

function appendUserMessage(text) {
  const container = document.getElementById('chatMessages');
  const div = document.createElement('div');
  div.className = 'chat-message user-message';
  div.innerHTML = `
    <div class="message-bubble">${escapeHtml(text)}</div>
    <div class="message-meta"><span class="meta-tag">You • Just now</span></div>
  `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function appendBotLoading() {
  const container = document.getElementById('chatMessages');
  const id = `loading-${Date.now()}`;
  const div = document.createElement('div');
  div.id = id;
  div.className = 'chat-message bot-message';
  div.innerHTML = `
    <div class="message-bubble">
      <i class="fa-solid fa-microchip fa-spin text-cyan"></i> Retrieving handbook clauses and verifying citations...
    </div>
  `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return id;
}

function removeBotLoading(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function appendBotMessage(result) {
  const container = document.getElementById('chatMessages');
  const div = document.createElement('div');
  div.className = 'chat-message bot-message';

  let citationsHtml = '';
  if (result.citations && result.citations.length > 0) {
    citationsHtml = `
      <div class="citations-container mt-2 pt-2 border-top">
        <span class="text-xs text-muted"><strong>Official Citations Grounding:</strong></span>
        <div class="d-flex gap-2 flex-wrap mt-1">
          ${result.citations.map(c => `
            <span class="badge badge-cyan" title="${c.doc_title}">
              <i class="fa-solid fa-bookmark"></i> ${c.section_code} ${c.title || ''}
            </span>
          `).join('')}
        </div>
      </div>
    `;
  }

  // Parse markdown bold and quotes
  let formattedAnswer = escapeHtml(result.answer)
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code style="background: rgba(255,255,255,0.1); padding: 2px 5px; border-radius: 4px;">$1</code>')
    .replace(/&gt; (.*)/g, '<blockquote>$1</blockquote>')
    .replace(/\n/g, '<br>');

  div.innerHTML = `
    <div class="message-bubble">
      ${formattedAnswer}
      ${citationsHtml}
    </div>
    <div class="message-meta">
      <span class="meta-tag">
        <i class="fa-solid fa-shield-check text-emerald"></i> 
        Grounding Confidence: ${Math.round((result.confidence || 0.85) * 100)}%
      </span>
      <span class="meta-tag">• ${result.guardrail_flag || 'VERIFIED'}</span>
    </div>
  `;

  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

async function loadKnowledgeChunks() {
  const container = document.getElementById('knowledgeChunksList');
  if (!container) return;

  // We can show default 10 grounded handbook items
  const chunks = [
    { section: '§1.2', title: 'Corridor & Main Gate Timings', text: 'Main entry locked at 22:30. In-room quiet hours begin at 23:00 to 06:30.' },
    { section: '§2.4', title: 'Routine Repair Windows & Silent Hours', text: 'Repairs permitted 08:30 to 18:30 Mon-Sat. Technicians barred after 20:00.' },
    { section: '§3.1', title: 'High-Wattage Appliance Prohibition', text: 'Immersion rods and room blowers >800W prohibited. ₹1,500 fine and confiscation.' },
    { section: '§4.3', title: 'Campus Wi-Fi & Network Acceptable Use', text: 'Wi-Fi 6 access provided. Personal spoofing routers banned. 12h resolution SLA.' },
    { section: '§5.1', title: 'Mess Timings, Food Hygiene & Rebate Rules', text: 'Food complaints audited by student committee. 4-day notice for mess rebate.' },
    { section: '§6.2', title: 'Room Handover & Property Damage Liability', text: 'Wear and tear is university responsibility. Willful damage billed at cost + 20% surcharge.' },
    { section: '§7.5', title: '24x7 Critical Emergency Protocol', text: 'Fire, shock, or collapse: Dial 011-2659-1000 or ambulance 011-2659-6666.' },
    { section: '§8.2', title: 'Leave Sanction & Digital Permissions', text: 'Overnight absence requires 6h advance portal request and parental SMS consent.' },
    { section: '§9.1', title: 'Day Guests & Visitor Housing Regulations', text: 'Guests allowed in common lobbies 09:00-19:30. No overnight stays in rooms.' },
    { section: '§10.0', title: 'Strict Anti-Ragging Mandate', text: 'Zero tolerance policy. National Helpline 1800-180-5522. Mandatory police FIR.' }
  ];

  container.innerHTML = chunks.map(c => `
    <div class="knowledge-chunk-card">
      <div class="chunk-header">
        <span class="chunk-section">${c.section}</span>
        <i class="fa-solid fa-shield-halved text-cyan text-xs"></i>
      </div>
      <div class="chunk-title">${c.title}</div>
      <div class="chunk-text">${c.text}</div>
    </div>
  `).join('');
}

// ================= MODAL: COMPLAINT DETAILS & ACTIONS =================

async function openComplaintModal(complaintId) {
  const modal = document.getElementById('complaintDetailModal');
  const title = document.getElementById('modalComplaintTitle');
  const body = document.getElementById('modalComplaintBody');

  title.textContent = `Ticket Details — ${complaintId}`;
  body.innerHTML = `<div class="empty-state"><i class="fa-solid fa-spinner fa-spin"></i> Fetching audit logs & workflow state...</div>`;
  modal.classList.remove('hidden');

  try {
    const res = await fetch(`/api/complaints/${complaintId}`);
    const data = await res.json();
    const c = data.complaint;

    body.innerHTML = `
      <div style="display: flex; flex-direction: column; gap: 1.25rem;">
        <!-- Top Info Header -->
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
          <div>
            <div style="font-size: 1.15rem; font-weight: 700;">${escapeHtml(c.title)}</div>
            <div class="text-xs text-muted mt-1">
              <span>Submitted by <strong>${escapeHtml(c.student_name)}</strong> (${c.student_id})</span> • 
              <span>${c.hostel_block} (Room ${c.room_number})</span>
            </div>
          </div>
          <div style="display: flex; gap: 6px;">
            <span class="badge ${getSeverityBadgeClass(c.severity)}">${c.severity}</span>
            <span class="badge ${getStateBadgeClass(c.state)}">${c.state}</span>
          </div>
        </div>

        <!-- Description Box -->
        <div style="background: rgba(11, 17, 32, 0.6); padding: 0.9rem; border-radius: var(--radius-md); border: 1px solid var(--border-subtle);">
          <div class="text-xs text-muted mb-1"><strong>DESCRIPTION:</strong></div>
          <div style="font-size: 0.88rem;">${escapeHtml(c.description)}</div>
        </div>

        <!-- Key Metrics Strip -->
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;">
          <div style="background: var(--bg-input); padding: 0.6rem; border-radius: var(--radius-md); text-align: center;">
            <div class="text-xs text-muted">URGENCY SCORE</div>
            <div style="font-family: var(--font-mono); font-weight: 700; color: var(--cyan);">${c.urgency_score}/100</div>
          </div>
          <div style="background: var(--bg-input); padding: 0.6rem; border-radius: var(--radius-md); text-align: center;">
            <div class="text-xs text-muted">SLA TARGET</div>
            <div style="font-family: var(--font-mono); font-weight: 700; color: var(--amber);">${c.sla_hours} Hours</div>
          </div>
          <div style="background: var(--bg-input); padding: 0.6rem; border-radius: var(--radius-md); text-align: center;">
            <div class="text-xs text-muted">ASSIGNED STAFF</div>
            <div style="font-weight: 700; font-size: 0.8rem;">${c.assigned_staff_name || 'Unassigned'}</div>
          </div>
          <div style="background: var(--bg-input); padding: 0.6rem; border-radius: var(--radius-md); text-align: center;">
            <div class="text-xs text-muted">SLA REMAINING</div>
            <div style="font-family: var(--font-mono); font-weight: 700; color: ${c.sla_breached ? 'var(--rose)' : 'var(--emerald)'};">
              ${c.sla_remaining_hours !== null ? `${c.sla_remaining_hours}h` : 'N/A'}
            </div>
          </div>
        </div>

        <!-- Workflow Step -->
        ${c.optimal_workflow_path ? `
          <div>
            <div class="text-xs text-muted mb-1"><strong>OPTIMAL RESOLUTION PATH (A* GRAPH SEARCH):</strong></div>
            <div style="font-family: var(--font-mono); font-size: 0.78rem; background: rgba(6, 182, 212, 0.08); padding: 8px; border-radius: var(--radius-md); color: var(--cyan);">
              ${c.optimal_workflow_path}
            </div>
          </div>
        ` : ''}

        <!-- State Machine Action Bar -->
        <div style="background: rgba(15, 23, 42, 0.8); border: 1px solid var(--border-subtle); padding: 1rem; border-radius: var(--radius-md);">
          <div style="font-size: 0.85rem; font-weight: 700; margin-bottom: 0.5rem;">Advance Complaint Lifecycle (State Transition):</div>
          <div style="display: flex; gap: 8px; flex-wrap: wrap;">
            ${renderStateActionButtons(c)}
          </div>
        </div>

        <!-- Student Verification Section if Awaiting Verification -->
        ${c.state === 'AWAITING_VERIFICATION' ? `
          <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid var(--emerald); padding: 1rem; border-radius: var(--radius-md);">
            <div style="font-weight: 700; color: var(--emerald); margin-bottom: 0.4rem;">
              <i class="fa-solid fa-signature"></i> Student Work Satisfaction Sign-Off:
            </div>
            <p class="text-xs text-secondary mb-2">Technician reported repair completion: "${escapeHtml(c.resolution_notes || 'Complete')}". Please rate the quality to officially resolve this complaint.</p>
            <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 8px;">
              <span class="text-xs">Rating:</span>
              <select id="modalRatingSelect" class="form-control form-control-sm" style="width: 140px;">
                <option value="5">⭐⭐⭐⭐⭐ (5/5)</option>
                <option value="4">⭐⭐⭐⭐ (4/5)</option>
                <option value="3">⭐⭐⭐ (3/5)</option>
                <option value="2">⭐⭐ (2/5)</option>
                <option value="1">⭐ (1/5)</option>
              </select>
              <input type="text" id="modalFeedbackInput" class="form-control form-control-sm flex-1" placeholder="Optional comments on repair quality...">
            </div>
            <div style="display: flex; gap: 8px;">
              <button class="btn btn-sm btn-primary" onclick="confirmStudentVerification('${c.id}', true)">
                <i class="fa-solid fa-check"></i> Accept & Mark Resolved
              </button>
              <button class="btn btn-sm btn-outline" onclick="confirmStudentVerification('${c.id}', false)">
                <i class="fa-solid fa-xmark"></i> Issue Not Fixed (Reopen)
              </button>
            </div>
          </div>
        ` : ''}

        <!-- Audit Trail Logs -->
        <div>
          <div class="text-xs text-muted mb-2"><strong>FINITE STATE MACHINE AUDIT LOGS (${data.audit_logs.length}):</strong></div>
          <div style="display: flex; flex-direction: column; gap: 6px; max-height: 200px; overflow-y: auto;">
            ${data.audit_logs.map(log => `
              <div style="font-size: 0.78rem; background: var(--bg-card); padding: 6px 10px; border-radius: var(--radius-sm); border-left: 3px solid var(--cyan);">
                <div style="display: flex; justify-content: space-between;">
                  <strong>${log.from_state} ➔ ${log.to_state}</strong>
                  <span class="text-muted text-xs">${formatDate(log.timestamp)}</span>
                </div>
                <div class="text-secondary">${escapeHtml(log.reason)}</div>
                <div class="text-muted text-xs">Actor: ${log.actor_name} (${log.actor_type})</div>
              </div>
            `).join('')}
          </div>
        </div>
      </div>
    `;

  } catch (err) {
    console.error('Modal error:', err);
    body.innerHTML = `<div class="empty-state text-rose">Failed to load ticket details.</div>`;
  }
}

function renderStateActionButtons(c) {
  const btns = [];
  if (c.state === 'ASSIGNED') {
    btns.push(`<button class="btn btn-xs btn-primary" onclick="transitionState('${c.id}', 'IN_PROGRESS', 'TECHNICIAN', 'Technician started physical inspection.')"><i class="fa-solid fa-play"></i> Start Work (In Progress)</button>`);
  }
  if (c.state === 'IN_PROGRESS') {
    btns.push(`<button class="btn btn-xs btn-primary" onclick="transitionState('${c.id}', 'AWAITING_VERIFICATION', 'TECHNICIAN', 'Repair completed on-site. Waiting for student verification.')"><i class="fa-solid fa-check-double"></i> Mark Completed (Awaiting Signoff)</button>`);
  }
  if (c.state !== 'ESCALATED' && c.state !== 'RESOLVED' && c.state !== 'CLOSED') {
    btns.push(`<button class="btn btn-xs btn-outline-warning" onclick="transitionState('${c.id}', 'ESCALATED', 'WARDEN', 'Manual Warden Escalation triggered for priority resolution.')"><i class="fa-solid fa-arrow-trend-up"></i> Escalate to Warden</button>`);
  }
  if (c.state === 'RESOLVED') {
    btns.push(`<button class="btn btn-xs btn-outline" onclick="transitionState('${c.id}', 'CLOSED', 'WARDEN', 'Archived and closed.')"><i class="fa-solid fa-lock"></i> Close & Archive Ticket</button>`);
  }
  return btns.join('') || '<span class="text-muted text-xs">No pending state actions available.</span>';
}

async function transitionState(complaintId, targetState, actorType, reason) {
  try {
    const res = await fetch(`/api/complaints/${complaintId}/transition`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target_state: targetState,
        actor_type: actorType,
        actor_name: actorType === 'TECHNICIAN' ? 'On-Duty Specialist' : 'Hostel Warden',
        reason: reason
      })
    });
    const result = await res.json();

    if (!res.ok) {
      showToast(result.error || 'Transition denied', 'error');
      return;
    }

    showToast(`Ticket state transitioned to ${targetState}`, 'success');
    await loadComplaints();
    await loadDashboardStats();
    openComplaintModal(complaintId); // refresh modal
  } catch (err) {
    console.error('Transition error:', err);
    showToast('Failed to transition state', 'error');
  }
}

async function confirmStudentVerification(complaintId, accepted) {
  const rating = document.getElementById('modalRatingSelect')?.value || 5;
  const feedback = document.getElementById('modalFeedbackInput')?.value || '';

  const targetState = accepted ? 'RESOLVED' : 'IN_PROGRESS';
  const reason = accepted ? 'Student signed off and verified complete repair.' : 'Student rejected repair: Issue persists.';

  try {
    const res = await fetch(`/api/complaints/${complaintId}/transition`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target_state: targetState,
        actor_type: 'STUDENT',
        actor_name: 'Resident Student',
        reason: reason,
        rating: accepted ? rating : null,
        feedback: feedback
      })
    });
    const result = await res.json();

    if (!res.ok) {
      showToast(result.error || 'Verification failed', 'error');
      return;
    }

    showToast(accepted ? 'Complaint successfully resolved & verified!' : 'Complaint returned to In Progress for rework.', 'success');
    await loadComplaints();
    await loadDashboardStats();
    openComplaintModal(complaintId);
  } catch (err) {
    console.error('Sign-off error:', err);
    showToast('Failed to record verification', 'error');
  }
}

function closeModal() {
  document.getElementById('complaintDetailModal').classList.add('hidden');
}

// ================= UTILITIES & HELPERS =================

function getSeverityBadgeClass(sev) {
  switch (sev) {
    case 'CRITICAL': return 'badge-critical';
    case 'HIGH': return 'badge-high';
    case 'MEDIUM': return 'badge-medium';
    case 'LOW': return 'badge-low';
    default: return 'badge-outline';
  }
}

function getStateBadgeClass(st) {
  switch (st) {
    case 'SUBMITTED': return 'badge-outline';
    case 'TRIAGED': return 'badge-cyan';
    case 'ASSIGNED': return 'badge-purple';
    case 'IN_PROGRESS': return 'badge-medium';
    case 'ESCALATED': return 'badge-rose';
    case 'AWAITING_VERIFICATION': return 'badge-amber';
    case 'RESOLVED': return 'badge-emerald';
    case 'CLOSED': return 'badge-outline';
    default: return 'badge-outline';
  }
}

function formatSlaRemaining(ticket) {
  if (ticket.state === 'RESOLVED' || ticket.state === 'CLOSED') {
    return 'Resolved';
  }
  if (ticket.sla_breached) {
    return `${Math.abs(ticket.sla_remaining_hours || 0)}h OVERDUE`;
  }
  if (ticket.sla_remaining_hours !== null) {
    return `${ticket.sla_remaining_hours}h left`;
  }
  return 'Calculated';
}

function formatDate(isoStr) {
  if (!isoStr) return '';
  const d = new Date(isoStr);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ', ' + d.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  
  let icon = 'fa-info-circle text-cyan';
  if (type === 'success') icon = 'fa-check-circle text-emerald';
  if (type === 'error') icon = 'fa-exclamation-circle text-rose';

  toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${escapeHtml(message)}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}
