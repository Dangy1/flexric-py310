import { chipRow, escapeHtml, formatTimestamp, resourceListText, setBanner, shortId, statusPill } from './js/common.js';

let portalState = {
  overview: null,
  selectedAgentId: null,
  selectedPageId: "overview",
  refreshTimer: null,
  workflowRuns: [],
  selectedWorkflowRunId: null,
  workflowDetail: null,
  workflowLaunchState: {},
  workflowApprovalState: {},
  workflowSaveState: {},
  savedWorkflows: [],
  platformActionState: {},
  runtimeSafety: null,
  comparisonLiveFigures: null,
  comparisonBusy: {},
  comparisonSnapshots: loadComparisonSnapshots(),
};

function workflowRouteFor(runId) {
  return runId ? `/workflows/${runId}` : "/";
}

function platformRoute() {
  return "/platform";
}

function comparisonRoute() {
  return "/comparison";
}

function schedulerRoute() {
  return "/scheduler";
}

function loadComparisonSnapshots() {
  try {
    const raw = window.localStorage.getItem("flexric-comparison-snapshots");
    const parsed = raw ? JSON.parse(raw) : {};
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch (error) {
    return {};
  }
}

function saveComparisonSnapshots() {
  try {
    window.localStorage.setItem("flexric-comparison-snapshots", JSON.stringify(portalState.comparisonSnapshots || {}));
  } catch (error) {
    console.error(error);
  }
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const detail = await response.text();
    let message = detail || `Request failed: ${response.status}`;
    try {
      const parsed = JSON.parse(detail);
      if (parsed && typeof parsed === "object" && parsed.detail) {
        message = String(parsed.detail);
      }
    } catch (error) {
      // Keep the raw text when the response is not JSON.
    }
    throw new Error(message);
  }
  return response.json();
}

function runtimeSafetyState(safety) {
  if (!safety) {
    return {status: "warning", title: "Safety data unavailable", body: "Runtime safety could not be loaded."};
  }
  if (safety.safe_for_enforced) {
    return {status: "ready", title: "Safe for a new test", body: (safety.warnings || [])[0] || "Runtime is idle and the core services are ready."};
  }
  return {status: "attention", title: "Reset or wait before enforced runs", body: (safety.blockers || [])[0] || "The runtime still has active work or missing services."};
}

async function resetRuntime(clearSaved = false) {
  portalState.platformActionState.reset = true;
  const resetButton = document.getElementById("reset-runtime-button");
  if (resetButton) {
    resetButton.disabled = true;
    resetButton.textContent = "Resetting...";
  }
  if (portalState.overview) {
    renderPortal(portalState.overview);
  }
  setBanner("Running emergency reset: stopping active local actions and clearing portal-managed runtime state...");
  try {
    const result = await fetchJson("/api/runtime/reset", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({clear_saved_workflows: clearSaved}),
    });
    portalState.workflowRuns = [];
    portalState.workflowDetail = null;
    portalState.selectedWorkflowRunId = null;
    portalState.workflowLaunchState = {};
    portalState.workflowApprovalState = {};
    portalState.comparisonSnapshots = {};
    saveComparisonSnapshots();
    await loadPortal(null);
    if (!portalState.selectedAgentId) {
      const target = portalState.selectedPageId === "platform" ? platformRoute() : routeFor(null, null, portalState.selectedPageId);
      window.history.pushState({}, "", target);
    }
    setBanner(`Runtime reset complete. Stopped ${result.stopped_run_count || 0} active run(s).`, "success");
  } catch (error) {
    setBanner(error.message, "warning");
  } finally {
    portalState.platformActionState.reset = false;
    if (resetButton) {
      resetButton.disabled = false;
      resetButton.textContent = "Emergency Reset";
    }
    if (portalState.overview) {
      renderPortal(portalState.overview);
    }
  }
}


async function runWorkflowControl(runId, action) {
  if (!runId || !action) {
    return;
  }
  const key = `${action}:${runId}`;
  portalState.platformActionState[key] = true;
  if (portalState.workflowDetail) {
    renderWorkflowDetail(portalState.workflowDetail, portalState.selectedPageId === "platform" ? "platform-workflow-detail-panel" : "workflow-detail-panel");
  }
  setBanner(`${action === "cancel" ? "Cancelling" : "Draining"} workflow ${shortId(runId)}...`);
  try {
    await fetchJson(`/api/workflows/${runId}/${action}`, {method: "POST"});
    await loadPortal(runId);
    setBanner(`Workflow ${shortId(runId)} ${action === "cancel" ? "cancelled" : "drained"}.`, "success");
  } catch (error) {
    setBanner(error.message, "warning");
  } finally {
    delete portalState.platformActionState[key];
    if (portalState.workflowDetail) {
      renderWorkflowDetail(portalState.workflowDetail, portalState.selectedPageId === "platform" ? "platform-workflow-detail-panel" : "workflow-detail-panel");
    }
  }
}

function renderLeaseFeed(leases, rootId = "platform-lease-feed") {
  const root = document.getElementById(rootId);
  if (!root) {
    return;
  }
  root.innerHTML = !leases || leases.length === 0
    ? `<div class="message-item">No active workflow leases right now.</div>`
    : leases.map((lease) => `
      <div class="message-item">
        <strong>${escapeHtml(lease.resource_id || "resource")}</strong>
        <div class="muted">${escapeHtml(lease.mode || "mode")} · ${escapeHtml(lease.workflow_label || lease.workflow_id || shortId(lease.run_id))}</div>
        <div>Run ${escapeHtml(shortId(lease.run_id))} · acquired ${escapeHtml(formatTimestamp(lease.acquired_at))}</div>
      </div>
    `).join("");
}

function renderQueueFeed(queues, rootId = "platform-queue-feed") {
  const root = document.getElementById(rootId);
  if (!root) {
    return;
  }
  root.innerHTML = !queues || queues.length === 0
    ? `<div class="message-item">No workflow is waiting in the scheduler queue.</div>`
    : queues.map((entry) => `
      <div class="message-item">
        <strong>${escapeHtml(entry.label || entry.workflow_id || "workflow")}</strong>
        <div class="muted">position ${escapeHtml(String(entry.queue_position || "n/a"))} · ${escapeHtml(entry.mode || "advisory")}</div>
        <div>${escapeHtml(entry.blocked_reason || "Waiting for resource admission.")}</div>
        <div class="workflow-detail-meta">Resources: ${escapeHtml(resourceListText(entry.required_resources || []))}</div>
      </div>
    `).join("");
}

function renderAuditFeed(items, rootId, emptyMessage, kindLabel) {
  const root = document.getElementById(rootId);
  if (!root) {
    return;
  }
  root.innerHTML = !items || items.length === 0
    ? `<div class="message-item">${escapeHtml(emptyMessage)}</div>`
    : items.map((item) => `
      <div class="message-item">
        <strong>${escapeHtml(item.title || item.action || kindLabel || "entry")}</strong>
        <div class="muted">${escapeHtml(item.actor || item.result || kindLabel || "log")} · ${escapeHtml(formatTimestamp(item.created_at))}</div>
        <div>${escapeHtml(item.detail || "No detail recorded.")}</div>
        ${item.run_id ? `<div class="workflow-detail-meta">Run ${escapeHtml(shortId(item.run_id))}</div>` : ""}
      </div>
    `).join("");
}

function formatMetricValue(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "n/a";
  }
  const numeric = Number(value);
  if (Math.abs(numeric) >= 100) {
    return numeric.toFixed(0);
  }
  if (Math.abs(numeric) >= 10) {
    return numeric.toFixed(1);
  }
  return numeric.toFixed(2);
}

function formatIsoTimestamp(value) {
  if (!value) {
    return "n/a";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return String(value);
  }
  return parsed.toLocaleTimeString();
}

function linePath(points, width, height, minValue, maxValue) {
  if (!points || points.length === 0) {
    return "";
  }
  const valueSpan = maxValue - minValue || 1;
  return points.map((point, index) => {
    const x = points.length === 1 ? width / 2 : (index / Math.max(points.length - 1, 1)) * width;
    const y = height - (((point.y - minValue) / valueSpan) * height);
    return `${index === 0 ? "M" : "L"}${x.toFixed(2)} ${y.toFixed(2)}`;
  }).join(" ");
}

function renderFigureSvg(figure) {
  const allPoints = (figure.series || []).flatMap((series) => series.points || []);
  if (allPoints.length === 0) {
    return `<div class="figure-empty">No telemetry points have been collected for this figure yet.</div>`;
  }
  const width = 360;
  const height = 160;
  const values = allPoints.map((point) => Number(point.y));
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const yTop = maxValue === minValue ? maxValue + 1 : maxValue;
  const yBottom = maxValue === minValue ? Math.max(0, minValue - 1) : minValue;
  const gridLines = [0, 1, 2, 3, 4].map((step) => {
    const y = (height / 4) * step;
    return `<line class="figure-grid-line" x1="0" y1="${y}" x2="${width}" y2="${y}"></line>`;
  }).join("");
  const paths = (figure.series || []).map((series) => {
    const path = linePath(series.points || [], width, height, yBottom, yTop);
    if (!path) {
      return "";
    }
    const latestPoint = (series.points || [])[series.points.length - 1];
    const markerX = series.points.length === 1 ? width / 2 : width;
    const valueSpan = yTop - yBottom || 1;
    const markerY = height - (((latestPoint.y - yBottom) / valueSpan) * height);
    return `
      <path d="${path}" fill="none" stroke="${series.color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"></path>
      <circle cx="${markerX.toFixed(2)}" cy="${markerY.toFixed(2)}" r="4" fill="${series.color}"></circle>
    `;
  }).join("");
  return `
    <svg class="figure-svg" viewBox="0 0 ${width} ${height + 18}" role="img" aria-label="${escapeHtml(figure.title)}">
      ${gridLines}
      ${paths}
      <text class="figure-axis-label" x="0" y="${height + 14}">${escapeHtml(String(yBottom.toFixed(1)))}</text>
      <text class="figure-axis-label" x="${width - 48}" y="${height + 14}">${escapeHtml(String(yTop.toFixed(1)))}</text>
    </svg>
  `;
}

function renderKpmFigureCard(figure) {
  const legend = (figure.series || []).map((series) => `
    <div class="figure-legend-item">
      <span class="figure-swatch" style="background:${series.color}"></span>
      <div>
        <strong>${escapeHtml(series.label || series.measurement || series.id)}</strong>
        <div class="figure-series-meta">${(series.points || []).length} samples</div>
      </div>
    </div>
  `).join("");
  const latest = (figure.latest_values || []).length === 0
    ? `<div class="figure-empty">Waiting for live values from the shared subscription.</div>`
    : `<div class="figure-summary-grid">${figure.latest_values.map((item) => `
        <div class="figure-summary-chip">
          <span class="figure-meta">${escapeHtml(item.measurement.split('.').slice(-1)[0] || item.measurement)}</span>
          <strong>${escapeHtml(formatMetricValue(item.value))}</strong>
          <span class="figure-series-meta">seq ${escapeHtml(String(item.seq || "n/a"))} · ${escapeHtml(formatIsoTimestamp(item.ts))}</span>
        </div>
      `).join("")}</div>`;
  return `
    <div class="figure-card">
      <div class="figure-card-head">
        <div>
          <h3>${escapeHtml(figure.title)}</h3>
          <p class="figure-meta">${escapeHtml(figure.description || "")}</p>
        </div>
        <div class="figure-source-meta">${escapeHtml(String(figure.sample_count || 0))} points · ${escapeHtml(figure.unit || "")}</div>
      </div>
      ${renderFigureSvg(figure)}
      <div class="figure-legend">${legend}</div>
      ${latest}
    </div>
  `;
}

function renderKpmFiguresPanel(payload) {
  const section = document.getElementById("agent-figure-section");
  const panel = document.getElementById("agent-figure-panel");
  if (!section || !panel) {
    return;
  }
  section.classList.remove("hidden");
  const figures = Array.isArray(payload.figures) ? payload.figures : [];
  const recent = Array.isArray(payload.recent_measurements) ? payload.recent_measurements : [];
  const source = payload.source || {};
  const recentHtml = recent.length === 0
    ? `<div class="figure-empty">No recent measurements captured yet.</div>`
    : `<div class="figure-card">
        <div class="figure-card-head">
          <div>
            <h3>Recent Measurements</h3>
            <p class="figure-meta">Newest parsed KPM samples from the shared bus.</p>
          </div>
          <div class="figure-source-meta">${escapeHtml(String(source.record_count || 0))} parsed records</div>
        </div>
        <div class="figure-recent-list">
          ${recent.map((item) => `
            <div class="message-item">
              <strong>${escapeHtml(item.measurement)}</strong><br>
              value=${escapeHtml(formatMetricValue(item.value))} · ue=${escapeHtml(item.ue_id || "n/a")} · seq=${escapeHtml(String(item.seq || "n/a"))}<br>
              <span class="muted">${escapeHtml(formatIsoTimestamp(item.ts))}</span>
            </div>
          `).join("")}
        </div>
      </div>`;
  panel.innerHTML = `
    <div class="figure-card accent-card">
      <div class="figure-card-head">
        <div>
          <h3>Shared KPM Bus</h3>
          <p class="figure-meta">${escapeHtml(payload.detail || "Live KPM data ready.")}</p>
        </div>
        ${statusPill(payload.status || "warning")}
      </div>
      <div class="figure-summary-grid">
        <div class="figure-summary-chip">
          <span class="figure-meta">Source</span>
          <strong>${escapeHtml(source.service || "kpm_bus")}</strong>
          <span class="figure-series-meta">${escapeHtml(source.url || "")}</span>
        </div>
        <div class="figure-summary-chip">
          <span class="figure-meta">Indications</span>
          <strong>${escapeHtml(String(source.indication_count || 0))}</strong>
          <span class="figure-series-meta">subscription events seen</span>
        </div>
        <div class="figure-summary-chip">
          <span class="figure-meta">Parsed records</span>
          <strong>${escapeHtml(String(source.record_count || 0))}</strong>
          <span class="figure-series-meta">ready for plotting</span>
        </div>
        <div class="figure-summary-chip">
          <span class="figure-meta">Last update</span>
          <strong>${escapeHtml(formatIsoTimestamp(source.last_ts))}</strong>
          <span class="figure-series-meta">shared bus refresh</span>
        </div>
      </div>
    </div>
    ${figures.map((figure) => renderKpmFigureCard(figure)).join("")}
    ${recentHtml}
  `;
}

async function loadAgentFigures(agent) {
  const section = document.getElementById("agent-figure-section");
  const panel = document.getElementById("agent-figure-panel");
  if (!section || !panel) {
    return;
  }
  if (!agent || agent.id !== "kpm") {
    section.classList.add("hidden");
    panel.innerHTML = "";
    return;
  }
  section.classList.remove("hidden");
  panel.innerHTML = `<div class="figure-empty">Loading live KPM figures from the shared subscription...</div>`;
  try {
    const payload = await fetchJson(`/api/agents/${agent.id}/figures`);
    if (!portalState.selectedAgentId || portalState.selectedAgentId !== agent.id) {
      return;
    }
    renderKpmFiguresPanel(payload);
  } catch (error) {
    panel.innerHTML = `<div class="figure-empty">Unable to load KPM figures: ${escapeHtml(error.message)}</div>`;
  }
}

function workflowLaunchPayload() {
  const goalInput = document.getElementById("workflow-goal");
  const modeInput = document.getElementById("workflow-mode");
  const durationInput = document.getElementById("workflow-duration");
  return {
    goal: (goalInput ? goalInput.value : "").trim() || "Optimize the near-RT RIC using live telemetry and control loops.",
    mode: (modeInput ? modeInput.value : "advisory") || "advisory",
    duration_s: Math.max(15, Number(durationInput ? durationInput.value : 45) || 45),
  };
}

function workflowIssueCount(run) {
  if (!run) {
    return 0;
  }
  const workflowErrors = Array.isArray(run.errors) ? run.errors.length : 0;
  const failedSteps = Array.isArray(run.steps)
    ? run.steps.filter((step) => step.status === "failed").length
    : 0;
  return workflowErrors + failedSteps;
}

function latestWorkflowRunForTemplate(workflowId) {
  return (portalState.workflowRuns || []).find((run) => run.workflow_id === workflowId) || null;
}

function workflowCardState(workflowId) {
  if (portalState.workflowLaunchState[workflowId]) {
    return {
      label: "Starting...",
      variant: "launching",
      disabled: true,
      detail: "Submitting the workflow to the backend.",
      run: latestWorkflowRunForTemplate(workflowId),
    };
  }

  const latestRun = latestWorkflowRunForTemplate(workflowId);
  if (!latestRun) {
    return {
      label: "Run Chain",
      variant: "idle",
      disabled: false,
      detail: "Ready to start a new coordinated workflow.",
      run: null,
    };
  }

  const status = String(latestRun.status || "pending");
  if (["running", "starting", "active", "admitted"].includes(status)) {
    return {
      label: "Running",
      variant: "running",
      disabled: true,
      detail: `Run ${shortId(latestRun.id)} is active in ${latestRun.mode || "advisory"} mode.`,
      run: latestRun,
    };
  }
  if (["queued", "waiting_for_approval"].includes(status)) {
    return {
      label: status === "queued" ? "Queued" : "Awaiting Approval",
      variant: "queued",
      disabled: false,
      detail: status === "queued"
        ? `Run ${shortId(latestRun.id)} is waiting for resources.`
        : `Run ${shortId(latestRun.id)} is waiting for approval before action launch.`,
      run: latestRun,
    };
  }
  const issueCount = workflowIssueCount(latestRun);
  if (["completed", "completed_with_issues", "success", "exited", "cancelled", "expired"].includes(status)) {
    return {
      label: "Completed",
      variant: issueCount > 0 || ["completed_with_issues", "cancelled", "expired"].includes(status) ? "warning" : "completed",
      disabled: false,
      detail: issueCount > 0 || ["completed_with_issues", "cancelled", "expired"].includes(status)
        ? `Run ${shortId(latestRun.id)} finished with ${Math.max(issueCount, 1)} issue(s).`
        : `Run ${shortId(latestRun.id)} completed in ${latestRun.mode || "advisory"} mode.`,
      run: latestRun,
    };
  }
  return {
    label: "Run Chain",
    variant: "idle",
    disabled: false,
    detail: `Last run ${shortId(latestRun.id)} is ${status}.`,
    run: latestRun,
  };
}

function workflowApprovalUi(run) {
  const selectedActions = Array.isArray(run && run.selected_actions) ? run.selected_actions : [];
  const launchedActions = Array.isArray(run && run.run_results) ? run.run_results : [];
  if (selectedActions.length === 0) {
    return {visible: false, disabled: true, label: "No Actions", variant: "done", note: "This workflow does not map to concrete actions."};
  }
  if (portalState.workflowApprovalState[run.id]) {
    return {visible: true, disabled: true, label: "Approving...", variant: "pending", note: "Launching the selected actions from the backend now."};
  }
  if (launchedActions.length > 0) {
    return {visible: true, disabled: true, label: "Actions Launched", variant: "done", note: `${launchedActions.length} action run(s) have already been launched for this workflow.`};
  }
  if (run.approved === true) {
    return {visible: true, disabled: true, label: "Approved", variant: "done", note: "This workflow is already approved. Refresh if the action state has not appeared yet."};
  }
  return {
    visible: true,
    disabled: false,
    label: run.mode === "advisory" ? "Approve And Run Actions" : "Approve Override And Run",
    variant: "ready",
    note: `${selectedActions.length} selected action(s) are waiting for operator approval.`,
  };
}

function workflowModeBadge(run) {
  if (!run) {
    return {label: "Workflow", variant: "neutral"};
  }
  if (run.mode === "advisory") {
    if (run.approved === true) {
      return {label: "Manual Approval", variant: "manual"};
    }
    return {label: "Recommend-only", variant: "advisory"};
  }
  return {label: "Enforced", variant: "enforced"};
}

function routeFor(agentId, workflowRunId = null, pageId = "overview") {
  if (agentId) {
    return `/agents/${agentId}`;
  }
  if (pageId === "platform") {
    return workflowRunId ? workflowRouteFor(workflowRunId) : platformRoute();
  }
  if (pageId === "comparison") {
    return comparisonRoute();
  }
  if (pageId === "scheduler") {
    return schedulerRoute();
  }
  return "/";
}

function currentRouteState() {
  const agentMatch = window.location.pathname.match(/^\/agents\/([^/]+)$/);
  if (agentMatch) {
    return {agentId: agentMatch[1], workflowRunId: null, pageId: "agent"};
  }
  const workflowMatch = window.location.pathname.match(/^\/workflows\/([^/]+)$/);
  if (workflowMatch) {
    return {agentId: null, workflowRunId: workflowMatch[1], pageId: "platform"};
  }
  if (window.location.pathname === "/platform") {
    return {agentId: null, workflowRunId: null, pageId: "platform"};
  }
  if (window.location.pathname === "/comparison") {
    return {agentId: null, workflowRunId: null, pageId: "comparison"};
  }
  if (window.location.pathname === "/scheduler") {
    return {agentId: null, workflowRunId: null, pageId: "scheduler"};
  }
  return {agentId: null, workflowRunId: null, pageId: "overview"};
}

function selectView(agentId, pageId = "overview", push = true) {
  portalState.selectedAgentId = agentId;
  portalState.selectedPageId = agentId ? "agent" : pageId;
  document.getElementById("dashboard-view").classList.toggle("hidden", Boolean(agentId) || portalState.selectedPageId !== "overview");
  document.getElementById("platform-view").classList.toggle("hidden", Boolean(agentId) || portalState.selectedPageId !== "platform");
  document.getElementById("comparison-view").classList.toggle("hidden", Boolean(agentId) || portalState.selectedPageId !== "comparison");
  document.getElementById("scheduler-view").classList.toggle("hidden", Boolean(agentId) || portalState.selectedPageId !== "scheduler");
  document.getElementById("agent-view").classList.toggle("hidden", !agentId);
  renderTopMenu(portalState.overview ? portalState.overview.agents : []);
  if (push) {
    window.history.pushState({}, "", routeFor(agentId, portalState.selectedWorkflowRunId, portalState.selectedPageId));
  }
  if (portalState.overview) {
    renderPortal(portalState.overview);
  }
}

function renderTopMenu(agents) {
  const root = document.getElementById("top-menu-tabs");
  const items = [
    {id: "overview", name: "Overview", kind: "page"},
    {id: "platform", name: "LangGraph", kind: "page"},
    ...agents.map((agent) => ({id: agent.id, name: agent.name, kind: "agent"})),
    {id: "scheduler", name: "Scheduler", kind: "page"},
    {id: "comparison", name: "Comparison", kind: "page"},
  ];
  root.innerHTML = items.map((item) => {
    const active = item.kind === "agent"
      ? portalState.selectedAgentId === item.id
      : !portalState.selectedAgentId && portalState.selectedPageId === item.id;
    return `
      <button class="menu-tab ${active ? "active" : ""}" data-kind="${item.kind}" data-id="${item.id}">
        ${item.name}
      </button>
    `;
  }).join("");

  root.querySelectorAll("[data-id]").forEach((button) => {
    button.addEventListener("click", () => {
      const kind = button.dataset.kind;
      const id = button.dataset.id;
      if (kind === "agent") {
        selectView(id, "agent", true);
      } else {
        selectView(null, id || "overview", true);
      }
    });
  });
}

function renderProviders(providers, rootId = "provider-grid") {
  const root = document.getElementById(rootId);
  if (!root) {
    return;
  }
  root.innerHTML = providers.map((provider) => `
    <article class="provider-card">
      <p class="card-eyebrow">${provider.label}</p>
      <h3>${provider.model}</h3>
      ${statusPill(provider.enabled ? "ready" : "warning")}
      <p class="muted">${provider.notes}</p>
      <div class="chip-row">
        <div class="chip"><strong>Endpoint</strong><br>${provider.endpoint}</div>
        <div class="chip"><strong>Tasks</strong><br>${provider.supports_tasks ? "enabled" : "not configured"}</div>
      </div>
    </article>
  `).join("");
}

function renderStackHealth(summary, safety, scheduler) {
  const root = document.getElementById("stack-grid");
  if (!summary) {
    root.innerHTML = `<div class="message-item">Stack summary is unavailable.</div>`;
    return;
  }

  const safetyState = runtimeSafetyState(safety);
  const safetyCard = `
    <article class="stack-card">
      <p class="card-eyebrow">Runtime Safety</p>
      <h3>${escapeHtml(safetyState.title)}</h3>
      ${statusPill(safetyState.status)}
      <p class="muted">${escapeHtml(safetyState.body)}</p>
      <div class="chip-row">
        <div class="chip"><strong>Core services</strong><br>${escapeHtml(String((safety && safety.essential_ready_count) || 0))}/${escapeHtml(String((safety && safety.essential_service_count) || 0))}</div>
        <div class="chip"><strong>Active actions</strong><br>${escapeHtml(String((safety && safety.active_action_count) || 0))}</div>
        <div class="chip"><strong>Active workflows</strong><br>${escapeHtml(String((safety && safety.active_workflow_count) || 0))}</div>
      </div>
    </article>
  `;

  const schedulerCard = scheduler ? `
    <article class="stack-card">
      <p class="card-eyebrow">Scheduler</p>
      <h3>Workflow Control</h3>
      ${statusPill((scheduler.queued_workflow_count || scheduler.active_lease_count) ? "queued" : "ready")}
      <p class="muted">${escapeHtml((scheduler.blocked_reasons || [])[0] || "No workflow is blocked right now.")}</p>
      <div class="chip-row">
        <div class="chip"><strong>Active leases</strong><br>${escapeHtml(String(scheduler.active_lease_count || 0))}</div>
        <div class="chip"><strong>Queued</strong><br>${escapeHtml(String(scheduler.queued_workflow_count || 0))}</div>
      </div>
    </article>
  ` : "";

  const latestWorkflow = summary.latest_workflow
    ? `
      <div class="stack-card accent-card">
        <p class="card-eyebrow">Latest Workflow</p>
        <h3>${summary.latest_workflow.label}</h3>
        ${statusPill(summary.latest_workflow.status || "ready")}
        <p class="muted">${escapeHtml(summary.latest_workflow.goal || "No goal recorded.")}</p>
        <div class="chip-row">
          <div class="chip"><strong>Steps</strong><br>${summary.latest_workflow.steps.length}</div>
          <div class="chip"><strong>Actions</strong><br>${summary.latest_workflow.action_run_count || 0}</div>
          <div class="chip"><strong>Completed</strong><br>${summary.latest_workflow.completed_step_count || 0}/${summary.latest_workflow.steps.length}</div>
          <div class="chip"><strong>Active runs</strong><br>${summary.latest_workflow.active_run_count || 0}</div>
          <div class="chip"><strong>Backend</strong><br>${escapeHtml(summary.latest_workflow.graph_backend || summary.graph_backend || "unknown")}</div>
          <div class="chip"><strong>Mode</strong><br>${escapeHtml(summary.latest_workflow.mode || "advisory")}</div>
          <div class="chip"><strong>Started</strong><br>${formatTimestamp(summary.latest_workflow.started_at)}</div>
        </div>
      </div>
    `
    : `
      <div class="stack-card accent-card">
        <p class="card-eyebrow">Latest Workflow</p>
        <h3>No workflow yet</h3>
        ${statusPill("warning")}
        <p class="muted">Run a workflow or use Test All Agents to exercise the multi-agent path.</p>
      </div>
    `;

  const serviceCards = (summary.services || []).map((service) => `
    <article class="stack-card">
      <p class="card-eyebrow">${service.label}</p>
      <h3>${service.id.toUpperCase()}</h3>
      ${statusPill(service.status)}
      <p class="muted">${escapeHtml(service.detail || "No detail")}</p>
      <div class="chip-row">
        <div class="chip"><strong>URL</strong><br>${escapeHtml(service.url)}</div>
        <div class="chip"><strong>Latency</strong><br>${service.latency_ms == null ? "n/a" : `${service.latency_ms} ms`}</div>
      </div>
    </article>
  `).join("");

  root.innerHTML = `
    <article class="stack-card stack-summary">
      <p class="card-eyebrow">Multi-Agent Summary</p>
      <h3>Verification status</h3>
      ${statusPill(summary.status)}
      <div class="chip-row">
        <div class="chip"><strong>Healthy services</strong><br>${summary.ready_service_count}/${summary.service_count}</div>
        <div class="chip"><strong>Workflow runs</strong><br>${summary.workflow_run_count}</div>
        <div class="chip"><strong>Messages</strong><br>${summary.message_count}</div>
        <div class="chip"><strong>Tasks</strong><br>${summary.task_count}</div>
        <div class="chip"><strong>Active runs</strong><br>${summary.active_run_count}</div>
        <div class="chip"><strong>Agents exercised</strong><br>${summary.agents_with_runs.length}/${summary.agents_with_actions.length}</div>
        <div class="chip"><strong>Graph backend</strong><br>${escapeHtml(summary.graph_backend || "unknown")}</div>
      </div>
    </article>
    ${safetyCard}
    ${schedulerCard}
    ${latestWorkflow}
    ${serviceCards}
  `;
}

function renderWorkflows(workflows) {
  const root = document.getElementById("workflow-grid");
  root.innerHTML = Object.entries(workflows).map(([id, workflow]) => {
    const buttonState = workflowCardState(id);
    const latestRun = buttonState.run;
    return `
      <article class="workflow-card">
        <p class="card-eyebrow">${id}</p>
        <h3>${workflow.label}</h3>
        <p class="muted">${workflow.description}</p>
        <div class="chip-row">${chipRow(workflow.steps)}</div>
        <div class="workflow-card-footer">
          ${latestRun ? `<div class="workflow-inline-status">${statusPill(latestRun.status || "pending")}<span class="workflow-inline-meta">${escapeHtml(buttonState.detail)}</span></div>` : `<div class="workflow-inline-meta">${escapeHtml(buttonState.detail)}</div>`}
          <button class="workflow-button ${buttonState.variant}" data-workflow="${id}" ${buttonState.disabled ? "disabled" : ""}>${buttonState.label}</button>
        </div>
      </article>
    `;
  }).join("");

  root.querySelectorAll("[data-workflow]").forEach((button) => {
    button.addEventListener("click", async () => {
      const workflowId = button.dataset.workflow;
      portalState.workflowLaunchState[workflowId] = true;
      renderWorkflows(workflows);
      setBanner(`Running workflow ${workflowId}...`);
      try {
        const payload = workflowLaunchPayload();
        const result = await fetchJson(`/api/workflows/${workflowId}/run`, {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload),
        });
        const run = result.run || {};
        delete portalState.workflowLaunchState[workflowId];
        await loadPortal(run.id || null);
        const actualWindow = run.duration_s || payload.duration_s;
        const adjusted = actualWindow !== payload.duration_s ? ` (window auto-set to ${actualWindow}s)` : "";
        setBanner(`Workflow ${workflowId} started in ${payload.mode} mode for ${actualWindow}s${adjusted}${run.id ? ` (run ${run.id.slice(0, 8)})` : ""}.`, "success");
      } catch (error) {
        delete portalState.workflowLaunchState[workflowId];
        renderWorkflows(workflows);
        setBanner(error.message, "warning");
      }
    });
  });
}

function renderWorkflowEvents(summary) {
  const root = document.getElementById("workflow-event-feed");
  if (!root) {
    return;
  }
  const events = (summary && summary.latest_workflow_events) || [];
  root.innerHTML = events.length === 0
    ? `<div class="message-item">No workflow events yet. Run a graph-backed workflow to see stages, approvals, and launches.</div>`
    : events.slice().reverse().map((event) => `
      <div class="message-item workflow-event-item">
        <strong>${escapeHtml(event.stage || "stage")}</strong>
        <div class="muted">${escapeHtml(event.kind || "event")} · ${escapeHtml(event.agent_id || "orchestrator")}</div>
        <div>${escapeHtml(event.content || "")}</div>
      </div>
    `).join("");
}

function renderAgents(agents, rootId = "agent-grid") {
  const root = document.getElementById(rootId);
  if (!root) {
    return;
  }
  root.innerHTML = agents.map((agent) => `
    <article class="agent-card">
      <p class="card-eyebrow">${agent.service_model}</p>
      <h3>${agent.name}</h3>
      ${statusPill(agent.status)}
      <p class="muted">${agent.description}</p>
      <div class="chip-row">
        <div class="chip"><strong>Skills</strong><br>${agent.skills.length}</div>
        <div class="chip"><strong>Measurements</strong><br>${agent.measurements.length}</div>
      </div>
      <p><strong>Activity:</strong> ${agent.activity}</p>
      <button class="card-link menu-link" data-open-agent="${agent.id}">Open workspace</button>
    </article>
  `).join("");

  root.querySelectorAll("[data-open-agent]").forEach((button) => {
    button.addEventListener("click", () => {
      selectView(button.dataset.openAgent, "agent", true);
    });
  });
}

function renderMessages(messages, rootId = "message-feed") {
  const root = document.getElementById(rootId);
  if (!root) {
    return;
  }
  root.innerHTML = messages.length === 0
    ? `<div class="message-item">No recent agent messages yet.</div>`
    : messages.map((message) => `
      <div class="message-item">
        <strong>${message.source_id}</strong> -> <strong>${message.target_id}</strong>
        <div class="muted">${message.kind}</div>
        <div>${message.content}</div>
      </div>
    `).join("");
}

function renderTasks(tasks, rootId = "task-feed") {
  const root = document.getElementById(rootId);
  if (!root) {
    return;
  }
  root.innerHTML = tasks.length === 0
    ? `<div class="message-item">No provider-backed tasks yet.</div>`
    : tasks.map((task) => `
      <div class="message-item">
        <strong>${task.agent_id}</strong> via <strong>${task.provider_id}</strong>
        <div class="muted">${task.status}</div>
        <div>${escapeHtml((task.response || task.error || "No output").slice(0, 280))}</div>
      </div>
    `).join("");
}

function renderRuns(runs, rootId = "run-feed") {
  const root = document.getElementById(rootId);
  if (!root) {
    return;
  }
  root.innerHTML = runs.length === 0
    ? `<div class="message-item">No suite runs yet.</div>`
    : runs.map((run) => `
      <div class="message-item">
        <strong>${run.agent_id}</strong> ran <strong>${run.label}</strong>
        <div class="muted">${run.status}</div>
        <div>${run.cmd.join(" ")}</div>
      </div>
    `).join("");
}

function synthesizeGraphSteps(run) {
  if (Array.isArray(run.graph_steps) && run.graph_steps.length > 0) {
    return run.graph_steps;
  }
  return (run.steps || []).map((step) => ({
    id: step.agent_id,
    label: step.agent_id.toUpperCase(),
    agent_id: step.agent_id,
    status: step.status || "pending",
    summary: step.message || "No detail recorded.",
    outputs: [
      ...(step.output ? [{label: "Output", content: step.output}] : []),
      ...(step.action_id ? [{label: "Action", content: step.action_id, action_id: step.action_id, run_id: step.run_id, status: step.run_status}] : []),
      ...(step.error ? [{label: "Error", content: step.error, detail: step.detail, run_id: step.run_id, status: step.run_status, returncode: step.returncode}] : []),
    ],
    events: step.events || [],
  }));
}

function renderRuntimeScopePanel(scope, kind = "workflow") {
  if (!scope) {
    return `<div class="message-item">Runtime scope data is unavailable.</div>`;
  }
  const items = Array.isArray(scope.portal_managed_state) ? scope.portal_managed_state : [];
  const childRuns = Array.isArray(scope.local_child_runs) ? scope.local_child_runs : [];
  return `
    <div class="message-item workflow-detail-block runtime-scope-block">
      <strong>Runtime Scope</strong>
      <p>${escapeHtml(scope.reset_scope || "Portal-managed runtime scope is available for this view.")}</p>
      <div class="chip-row">
        <div class="chip"><strong>Local child runs</strong><br>${escapeHtml(String(scope.local_child_run_count || 0))}</div>
        <div class="chip"><strong>Active local runs</strong><br>${escapeHtml(String(scope.active_local_child_run_count || 0))}</div>
        ${kind === "workflow" ? `<div class="chip"><strong>Queue entries</strong><br>${escapeHtml(String(scope.queue_entry_count || 0))}</div><div class="chip"><strong>Leases</strong><br>${escapeHtml(String(scope.lease_count || 0))}</div>` : `<div class="chip"><strong>Tasks</strong><br>${escapeHtml(String(scope.task_count || 0))}</div>${scope.latest_task_status ? `<div class="chip"><strong>Latest task</strong><br>${escapeHtml(scope.latest_task_status)}</div>` : ""}`}
      </div>
      ${items.length ? `<div class="workflow-detail-meta">Portal-managed state: ${escapeHtml(items.join("; "))}</div>` : ""}
      ${renderActionRunList(childRuns, {
        emptyMessage: "No local child runs are recorded right now.",
        initial: 3,
        detailsLabel: "local child runs",
        showCommand: false,
      })}
      <div class="workflow-detail-meta">${escapeHtml(scope.restart_scope || "Restarting services affects nearRT-RIC, emulator, portal, RPC, MCP, and KPM bus.")}</div>
      <div class="workflow-detail-meta">Service restart scope: ${escapeHtml((scope.service_restart_components || []).join(", "))}</div>
    </div>
  `;
}


function renderWorkflowOutputs(outputs) {
  if (!outputs || outputs.length === 0) {
    return `<div class="message-item">No step outputs recorded.</div>`;
  }
  return `<div class="workflow-output-list">${outputs.map((output) => {
    const meta = [
      output.agent_id ? `agent ${escapeHtml(output.agent_id)}` : null,
      output.action_id ? `action ${escapeHtml(output.action_id)}` : null,
      output.run_id ? `run ${escapeHtml(shortId(output.run_id))}` : null,
      output.status ? `status ${escapeHtml(output.status)}` : null,
      output.returncode != null ? `rc ${escapeHtml(output.returncode)}` : null,
    ].filter(Boolean).join(" · ");
    return `
      <div class="message-item workflow-output-item">
        <strong>${escapeHtml(output.label || "Output")}</strong>
        <div>${escapeHtml(output.content || "")}</div>
        ${output.detail ? `<div class="muted workflow-detail-meta">${escapeHtml(output.detail)}</div>` : ""}
        ${meta ? `<div class="muted workflow-detail-meta">${meta}</div>` : ""}
      </div>
    `;
  }).join("")}</div>`;
}

function normalizeTextGroups(items, providedGroups) {
  if (Array.isArray(providedGroups) && providedGroups.length > 0) {
    return providedGroups
      .map((group) => ({
        text: String(group.text || "").trim(),
        count: Math.max(1, Number(group.count) || 1),
      }))
      .filter((group) => group.text);
  }
  const groups = [];
  const indexByText = new Map();
  (Array.isArray(items) ? items : []).forEach((item) => {
    const text = String(item || "").trim();
    if (!text) {
      return;
    }
    const existing = indexByText.get(text);
    if (existing == null) {
      indexByText.set(text, groups.length);
      groups.push({text, count: 1});
    } else {
      groups[existing].count += 1;
    }
  });
  return groups;
}

function compactCommand(cmd) {
  const parts = Array.isArray(cmd) ? cmd.filter(Boolean).map((item) => String(item)) : [];
  if (parts.length === 0) {
    return "No command recorded.";
  }
  if (parts.length <= 6) {
    return parts.join(" ");
  }
  return `${parts.slice(0, 4).join(" ")} ... ${parts[parts.length - 1]}`;
}

function summarizeRunStatuses(runResults) {
  const counts = new Map();
  (Array.isArray(runResults) ? runResults : []).forEach((result) => {
    const status = String((result && result.status) || "unknown");
    counts.set(status, (counts.get(status) || 0) + 1);
  });
  const preferredOrder = ["running", "launching", "starting", "queued", "blocked_by_conflict", "exited", "completed", "success", "failed", "timed_out", "cancelled", "unknown"];
  const statuses = Array.from(counts.entries()).map(([status, count]) => ({status, count}));
  statuses.sort((left, right) => {
    const leftIndex = preferredOrder.indexOf(left.status);
    const rightIndex = preferredOrder.indexOf(right.status);
    return (leftIndex === -1 ? preferredOrder.length : leftIndex) - (rightIndex === -1 ? preferredOrder.length : rightIndex);
  });
  return statuses;
}

function renderGroupedTextList(items, providedGroups, emptyMessage, options = {}) {
  const groups = normalizeTextGroups(items, providedGroups);
  if (groups.length === 0) {
    return `<p class="muted">${escapeHtml(emptyMessage)}</p>`;
  }
  const initial = Math.max(1, Number(options.initial) || 4);
  const label = options.label || "items";
  const totalCount = groups.reduce((sum, group) => sum + group.count, 0);
  const visible = groups.slice(0, initial);
  const hidden = groups.slice(initial);
  const renderList = (list) => `
    <ul class="workflow-bullet-list workflow-compact-bullets">
      ${list.map((group) => `
        <li class="workflow-group-row">
          <span>${escapeHtml(group.text)}</span>
          ${group.count > 1 ? `<span class="workflow-count-badge">x${escapeHtml(group.count)}</span>` : ""}
        </li>
      `).join("")}
    </ul>
  `;
  return `
    <div class="workflow-grouped-list">
      <div class="workflow-detail-meta">${escapeHtml(String(groups.length))} unique ${escapeHtml(label)} · ${escapeHtml(String(totalCount))} total</div>
      ${renderList(visible)}
      ${hidden.length ? `
        <details class="workflow-collapsible">
          <summary>Show ${escapeHtml(String(hidden.length))} more ${escapeHtml(label)}</summary>
          ${renderList(hidden)}
        </details>
      ` : ""}
    </div>
  `;
}

function renderActionStatusSummary(runResults) {
  const statuses = summarizeRunStatuses(runResults);
  if (statuses.length === 0) {
    return "";
  }
  return `
    <div class="chip-row workflow-compact-chip-row">
      ${statuses.map((item) => `
        <div class="chip compact-chip">
          <strong>${escapeHtml(String(item.count))}</strong><br>${escapeHtml(item.status)}
        </div>
      `).join("")}
    </div>
  `;
}

function renderActionRunCards(runResults, options = {}) {
  const items = Array.isArray(runResults) ? runResults : [];
  const initial = Math.max(1, Number(options.initial) || 6);
  const showCommand = options.showCommand !== false;
  const visible = items.slice(0, initial);
  const hidden = items.slice(initial);
  const renderCards = (list) => `
    <div class="workflow-output-list">
      ${list.map((runResult) => `
        <div class="message-item workflow-output-item">
          <strong>${escapeHtml(runResult.agent_id || "agent")} · ${escapeHtml(runResult.label || runResult.action_id || "action")}</strong>
          ${showCommand ? `<div>${escapeHtml(compactCommand(runResult.cmd || []))}</div>` : ""}
          <div class="muted workflow-detail-meta">action ${escapeHtml(runResult.action_id || "n/a")}${runResult.id ? ` · run ${escapeHtml(shortId(runResult.id))}` : runResult.run_id ? ` · run ${escapeHtml(shortId(runResult.run_id))}` : ""} · status ${escapeHtml(runResult.status || "unknown")}${runResult.returncode != null ? ` · rc ${escapeHtml(runResult.returncode)}` : ""}</div>
          ${runResult.detail ? `<div class="muted workflow-detail-meta">${escapeHtml(runResult.detail)}</div>` : ""}
        </div>
      `).join("")}
    </div>
  `;
  return `
    ${renderActionStatusSummary(items)}
    ${items.length === 0 ? `<p class="muted">${escapeHtml(options.emptyMessage || "No action runs were launched.")}</p>` : renderCards(visible)}
    ${hidden.length ? `
      <details class="workflow-collapsible">
        <summary>Show ${escapeHtml(String(hidden.length))} more ${escapeHtml(options.detailsLabel || "action runs")}</summary>
        ${renderCards(hidden)}
      </details>
    ` : ""}
  `;
}

function renderActionRunList(runResults, options = {}) {
  return renderActionRunCards(runResults, options);
}

function renderEventHistory(events, emptyMessage, options = {}) {
  if (!events || events.length === 0) {
    return `<div class="message-item">${emptyMessage}</div>`;
  }
  const ordered = events.slice().reverse();
  const initial = options.collapsible ? Math.max(1, Number(options.initial) || 12) : ordered.length;
  const visible = ordered.slice(0, initial);
  const hidden = ordered.slice(initial);
  const renderItems = (list) => `<div class="message-feed workflow-event-history">${list.map((event) => {
    const metadata = event.metadata && Object.keys(event.metadata).length > 0
      ? escapeHtml(JSON.stringify(event.metadata))
      : "";
    return `
      <div class="message-item workflow-event-item">
        <strong>${escapeHtml(event.stage || "stage")}</strong>
        <div class="muted">${escapeHtml(event.kind || "event")} · ${escapeHtml(event.agent_id || "orchestrator")} · ${formatTimestamp(event.timestamp)}</div>
        <div>${escapeHtml(event.content || "")}</div>
        ${metadata ? `<div class="muted workflow-detail-meta">${metadata}</div>` : ""}
      </div>
    `;
  }).join("")}</div>`;
  return `
    ${options.collapsible ? `<div class="workflow-detail-meta">Showing latest ${escapeHtml(String(visible.length))} of ${escapeHtml(String(ordered.length))} events.</div>` : ""}
    ${renderItems(visible)}
    ${hidden.length ? `
      <details class="workflow-collapsible">
        <summary>Show ${escapeHtml(String(hidden.length))} older events</summary>
        ${renderItems(hidden)}
      </details>
    ` : ""}
  `;
}

function renderWorkflowRunList(runs, rootId = "workflow-run-list") {
  const root = document.getElementById(rootId);
  if (!root) {
    return;
  }
  root.innerHTML = runs.length === 0
    ? `<div class="message-item">No workflow runs yet. Start one from Workflow Chains.</div>`
    : runs.map((run) => `
      <button class="workflow-run-item ${portalState.selectedWorkflowRunId === run.id ? "active" : ""}" data-workflow-run="${run.id}">
        <span>
          <strong>${escapeHtml(run.label)}</strong>
          <span class="workflow-run-subtitle">${escapeHtml(run.mode || "advisory")} · ${escapeHtml(run.graph_backend || "unknown")}</span>
        </span>
        <span>
          ${statusPill(run.status || "pending")}
          <span class="workflow-run-subtitle">${formatTimestamp(run.started_at)}</span>
        </span>
      </button>
    `).join("");

  root.querySelectorAll("[data-workflow-run]").forEach((button) => {
    button.addEventListener("click", async () => {
      const runId = button.dataset.workflowRun;
      if (!runId || runId === portalState.selectedWorkflowRunId) {
        return;
      }
      try {
        portalState.selectedWorkflowRunId = runId;
        if (!portalState.selectedAgentId && portalState.selectedPageId === "platform") {
          window.history.pushState({}, "", workflowRouteFor(runId));
        }
        await loadPortal(runId);
      } catch (error) {
        setBanner(error.message, "warning");
      }
    });
  });
}

function renderSavedWorkflows(savedWorkflows, rootId = "saved-workflow-list") {
  const root = document.getElementById(rootId);
  if (!root) {
    return;
  }
  root.innerHTML = !savedWorkflows || savedWorkflows.length === 0
    ? `<div class="message-item">No saved workflows yet. Save one from the workflow detail panel.</div>`
    : savedWorkflows.map((item) => `
      <button class="workflow-run-item saved-workflow-item" data-saved-workflow-run="${escapeHtml(item.run_id)}">
        <span>
          <strong>${escapeHtml(item.name || item.label || item.run_id)}</strong>
          <span class="workflow-run-subtitle">${escapeHtml(item.label || item.workflow_id || "workflow")} · run ${escapeHtml(shortId(item.run_id))}</span>
          <span class="workflow-run-subtitle">${escapeHtml(item.purpose || item.run_goal || "No purpose recorded.")}</span>
        </span>
        <span>
          ${statusPill(item.run_status || "missing")}
          <span class="workflow-run-subtitle">${formatTimestamp(item.updated_at || item.created_at)}</span>
        </span>
      </button>
    `).join("");

  root.querySelectorAll("[data-saved-workflow-run]").forEach((button) => {
    button.addEventListener("click", async () => {
      const runId = button.dataset.savedWorkflowRun;
      if (!runId) {
        return;
      }
      try {
        portalState.selectedWorkflowRunId = runId;
        if (!portalState.selectedAgentId && portalState.selectedPageId === "platform") {
          window.history.pushState({}, "", workflowRouteFor(runId));
        }
        await loadPortal(runId);
        setBanner(`Loaded saved workflow ${shortId(runId)}.`, "success");
      } catch (error) {
        setBanner(error.message, "warning");
      }
    });
  });
}



function renderWorkflowDetail(run, rootId = "workflow-detail-panel") {

  const root = document.getElementById(rootId);
  if (!root) {
    return;
  }
  if (!run) {
    root.innerHTML = `<div class="message-item">Select a workflow run to inspect step outputs and event history.</div>`;
    return;
  }

  const graphSteps = synthesizeGraphSteps(run);
  const launchedActions = Array.isArray(run.run_results) ? run.run_results : [];
  const selectedActions = Array.isArray(run.selected_actions) ? run.selected_actions : [];
  const recommendations = Array.isArray(run.recommendations) ? run.recommendations : [];
  const recommendationGroups = Array.isArray(run.recommendation_groups) ? run.recommendation_groups : [];
  const verificationNotes = Array.isArray(run.verification_notes) ? run.verification_notes : [];
  const verificationNoteGroups = Array.isArray(run.verification_note_groups) ? run.verification_note_groups : [];
  const errors = Array.isArray(run.errors) ? run.errors : [];
  const errorGroups = Array.isArray(run.error_groups) ? run.error_groups : [];
  const latestEvents = Array.isArray(run.events) ? run.events : [];
  const runtimeScope = run.runtime_scope || null;
  const approvalUi = workflowApprovalUi(run);
  const modeBadge = workflowModeBadge(run);
  const saveState = portalState.workflowSaveState[run.id] || false;
  const cancelPending = Boolean(portalState.platformActionState[`cancel:${run.id}`]);
  const drainPending = Boolean(portalState.platformActionState[`drain:${run.id}`]);
  const defaultSavedName = `${run.label || "Workflow"} ${shortId(run.id)}`;
  const existingSaved = (portalState.savedWorkflows || []).find((item) => item.run_id === run.id) || null;

  root.innerHTML = `
    <div class="workflow-detail-shell">
      <div class="workflow-detail-header">
        <div>
          <p class="card-eyebrow">${escapeHtml(run.workflow_id || "workflow")}</p>
          <h3>${escapeHtml(run.label || "Workflow")}</h3>
          <p class="muted">${escapeHtml(run.goal || "No goal recorded.")}</p>
          <div class="workflow-mode-badges">
            <span class="workflow-mode-badge ${modeBadge.variant}">${escapeHtml(modeBadge.label)}</span>
            <span class="workflow-mode-badge neutral">${escapeHtml(run.mode || "advisory")}</span>
          </div>
        </div>
        <div class="workflow-detail-status">
          ${statusPill(run.status || "pending")}
          <div class="workflow-detail-meta">Run ${escapeHtml(shortId(run.id))}</div>
        </div>
      </div>

      <div class="chip-row workflow-detail-summary">
        <div class="chip"><strong>Backend</strong><br>${escapeHtml(run.graph_backend || "unknown")}</div>
        <div class="chip"><strong>Mode</strong><br>${escapeHtml(run.mode || "advisory")}</div>
        <div class="chip"><strong>Window</strong><br>${escapeHtml(String(run.effective_duration_s || run.duration_s || 45))}s</div>
        <div class="chip"><strong>Requested</strong><br>${escapeHtml(String(run.requested_duration_s || run.duration_s || 45))}s</div>
        <div class="chip"><strong>Started</strong><br>${formatTimestamp(run.started_at)}</div>
        <div class="chip"><strong>Updated</strong><br>${formatTimestamp(run.updated_at || run.completed_at || run.started_at)}</div>
        <div class="chip"><strong>Actions</strong><br>${launchedActions.length}</div>
        <div class="chip"><strong>Steps</strong><br>${run.completed_step_count || 0}/${(run.steps || []).length}</div>
        <div class="chip"><strong>Queue</strong><br>${escapeHtml(String(run.queue_position || 0))}</div>
      </div>

      <div class="split workflow-detail-top">
        <div class="message-item workflow-detail-block">
          <strong>Summary</strong>
          <p>${escapeHtml(run.summary || "No workflow summary recorded yet.")}</p>
        </div>
        <div class="message-item workflow-detail-block">
          <strong>Approval</strong>
          <p>${escapeHtml(run.approval_reason || "No approval stage output recorded.")}</p>
          <div class="workflow-detail-meta">Required: ${run.approval_required ? "yes" : "no"} · Approved: ${run.approval_required ? (run.approved === true ? "yes" : "no") : "n/a"}</div>
          ${approvalUi.visible ? `
            <div class="workflow-detail-actions">
              <button class="workflow-approve-button ${approvalUi.variant}" data-approve-workflow="${escapeHtml(run.id)}" ${approvalUi.disabled ? "disabled" : ""}>${escapeHtml(approvalUi.label)}</button>
              <div class="workflow-detail-meta">${escapeHtml(approvalUi.note)}</div>
            </div>
          ` : ""}
        </div>
      </div>

      ${renderRuntimeScopePanel(runtimeScope, "workflow")}

      <div class="split workflow-detail-top">
        <div class="message-item workflow-detail-block">
          <strong>Scheduler</strong>
          <p>${escapeHtml(run.blocked_reason || "No scheduler conflict is recorded for this workflow.")}</p>
          <div class="workflow-detail-meta">State: ${escapeHtml(run.status || "pending")} · Queue: ${escapeHtml(String(run.queue_position || "n/a"))}</div>
          <div class="workflow-detail-meta">Resources: ${escapeHtml(resourceListText(run.required_resources || []))}</div>
          <div class="workflow-detail-meta">Wait started: ${escapeHtml(formatTimestamp(run.wait_started_at))} · Lease acquired: ${escapeHtml(formatTimestamp(run.lease_acquired_at))}</div>
        </div>
        <div class="message-item workflow-detail-block">
          <strong>Operator Controls</strong>
          <p>Use targeted workflow controls before falling back to the emergency runtime reset.</p>
          <div class="workflow-detail-actions">
            <button class="workflow-button warning" data-cancel-workflow="${escapeHtml(run.id)}" ${cancelPending || ["completed", "completed_with_issues", "cancelled", "expired"].includes(run.status) ? "disabled" : ""}>${cancelPending ? "Cancelling..." : "Cancel Workflow"}</button>
            <button class="workflow-button warning" data-drain-workflow="${escapeHtml(run.id)}" ${drainPending || ["completed", "completed_with_issues", "cancelled", "expired"].includes(run.status) ? "disabled" : ""}>${drainPending ? "Draining..." : "Drain Workflow"}</button>
            <div class="workflow-detail-meta">Cancel removes the workflow from queue or stops it. Drain releases its leases and stops active actions without wiping the rest of the runtime.</div>
          </div>
        </div>
      </div>

      <div class="split workflow-detail-top">
        <div class="message-item workflow-detail-block">
          <strong>Save Run</strong>
          <label>
            Name
            <input id="save-workflow-name" type="text" value="${escapeHtml((existingSaved && existingSaved.name) || defaultSavedName)}">
          </label>
          <label>
            Purpose
            <textarea id="save-workflow-purpose" rows="4">${escapeHtml((existingSaved && existingSaved.purpose) || run.goal || "")}</textarea>
          </label>
          <div class="workflow-detail-actions">
            <button class="workflow-approve-button ready" data-save-workflow="${escapeHtml(run.id)}" ${saveState ? "disabled" : ""}>${saveState ? "Saving..." : (existingSaved ? "Update Saved Workflow" : "Save Workflow")}</button>
            <div class="workflow-detail-meta">${existingSaved ? `Saved as ${escapeHtml(existingSaved.name)}.` : "Store this workflow with a human-friendly label so you can reopen it later."}</div>
          </div>
        </div>
        <div class="message-item workflow-detail-block">
          <strong>Run Address</strong>
          <p class="platform-code">${escapeHtml(window.location.origin + workflowRouteFor(run.id))}</p>
          <div class="workflow-detail-meta">Run id ${escapeHtml(run.id)} · workflow ${escapeHtml(run.workflow_id || "workflow")}</div>
        </div>
      </div>

      <div class="split workflow-detail-top">
        <div class="message-item workflow-detail-block">
          <strong>Recommendations</strong>
          ${renderGroupedTextList(recommendations, recommendationGroups, "No recommendations recorded.", {initial: 3, label: "recommendations"})}
        </div>
        <div class="message-item workflow-detail-block">
          <strong>Verification Notes</strong>
          ${renderGroupedTextList(verificationNotes, verificationNoteGroups, "No verification notes recorded.", {initial: 4, label: "notes"})}
        </div>
      </div>

      <div class="message-item workflow-detail-block">
        <strong>Launched Actions</strong>
        ${renderActionRunList(launchedActions, {
          emptyMessage: "No action runs were launched in this workflow.",
          initial: 6,
          detailsLabel: "action runs",
        })}
        ${selectedActions.length > 0 ? `<div class="workflow-detail-meta">Selected actions: ${escapeHtml(selectedActions.map((item) => `${item.agent_id}:${item.action_id}`).join(", "))}</div>` : ""}
      </div>

      <div>
        <div class="section-head workflow-detail-section-head">
          <h3>Graph Steps</h3>
          <p>Per-stage outputs from observe, diagnose, approve, act, verify, and summarize.</p>
        </div>
        <div class="workflow-stage-grid">
          ${graphSteps.map((step) => `
            <article class="workflow-stage-card">
              <div class="workflow-stage-head">
                <div>
                  <p class="card-eyebrow">${escapeHtml(step.agent_id || "orchestrator")}</p>
                  <h3>${escapeHtml(step.label || step.id || "Step")}</h3>
                </div>
                ${statusPill(step.status || "pending")}
              </div>
              <p class="muted">${escapeHtml(step.summary || "No summary recorded.")}</p>
              ${renderWorkflowOutputs(step.outputs || [])}
              <div class="workflow-stage-events-block">
                <strong>Stage events</strong>
                ${renderEventHistory(step.events || [], "No stage events recorded.", {collapsible: true, initial: 6})}
              </div>
            </article>
          `).join("")}
        </div>
      </div>

      <div class="message-item workflow-detail-block ${errors.length > 0 ? "workflow-errors" : ""}">
        <strong>Errors</strong>
        ${renderGroupedTextList(errors, errorGroups, "No workflow errors recorded.", {initial: 4, label: "errors"})}
      </div>

      <div>
        <div class="section-head workflow-detail-section-head">
          <h3>Full Event History</h3>
          <p>Complete event stream for the selected workflow run.</p>
        </div>
        ${renderEventHistory(latestEvents, "No event history recorded yet.", {collapsible: true, initial: 12})}
      </div>
    </div>
  `;

  const approveButton = root.querySelector("[data-approve-workflow]");
  if (approveButton) {
    approveButton.addEventListener("click", async () => {
      portalState.workflowApprovalState[run.id] = true;
      renderWorkflowDetail(run, rootId);
      setBanner(`Approving workflow ${shortId(run.id)} and launching its selected actions...`);
      try {
        await fetchJson(`/api/workflows/${run.id}/approve`, {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({reason: `Manually approved from the portal UI at ${new Date().toLocaleString()}. Execute the selected actions now.`}),
        });
        delete portalState.workflowApprovalState[run.id];
        await loadPortal(run.id);
        setBanner(`Workflow ${shortId(run.id)} approved. Selected actions were launched from the backend.`, "success");
      } catch (error) {
        delete portalState.workflowApprovalState[run.id];
        renderWorkflowDetail(run, rootId);
        setBanner(error.message, "warning");
      }
    });
  }

  const cancelButton = root.querySelector("[data-cancel-workflow]");
  if (cancelButton) {
    cancelButton.addEventListener("click", async () => {
      await runWorkflowControl(run.id, "cancel");
    });
  }

  const drainButton = root.querySelector("[data-drain-workflow]");
  if (drainButton) {
    drainButton.addEventListener("click", async () => {
      await runWorkflowControl(run.id, "drain");
    });
  }

  const saveButton = root.querySelector("[data-save-workflow]");
  if (saveButton) {
    saveButton.addEventListener("click", async () => {
      const nameInput = document.getElementById("save-workflow-name");
      const purposeInput = document.getElementById("save-workflow-purpose");
      const payload = {
        name: (nameInput ? nameInput.value : "").trim() || defaultSavedName,
        purpose: (purposeInput ? purposeInput.value : "").trim(),
      };
      portalState.workflowSaveState[run.id] = true;
      renderWorkflowDetail(run, rootId);
      setBanner(`Saving workflow ${shortId(run.id)}...`);
      try {
        await fetchJson(`/api/workflows/${run.id}/save`, {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload),
        });
        delete portalState.workflowSaveState[run.id];
        await loadPortal(run.id);
        setBanner(`Saved workflow ${shortId(run.id)} as ${payload.name}.`, "success");
      } catch (error) {
        delete portalState.workflowSaveState[run.id];
        renderWorkflowDetail(run, rootId);
        setBanner(error.message, "warning");
      }
    });
  }
}

function renderPlatformOrchestrator(platform, data) {
  const root = document.getElementById("platform-orchestrator-panel");
  if (!root) {
    return;
  }
  const agents = (data && data.agents) || [];
  const orchestrator = agents.find((agent) => agent.id === "orchestrator");
  const latestWorkflow = data && data.multi_agent ? data.multi_agent.latest_workflow : null;
  const a2a = (platform && platform.a2a) || {};
  if (!orchestrator) {
    root.innerHTML = `<div class="message-item">The orchestrator agent is unavailable.</div>`;
    return;
  }

  root.innerHTML = `
    <div class="message-item">
      <strong>${escapeHtml(orchestrator.name)}</strong>
      <div class="muted">${escapeHtml(orchestrator.role || "Workflow coordinator")}</div>
      ${statusPill(orchestrator.status || "ready")}
      <p>${escapeHtml(orchestrator.description || "No orchestrator description recorded.")}</p>
      <div class="chip-row">
        <div class="chip"><strong>Skills</strong><br>${orchestrator.skills.length}</div>
        <div class="chip"><strong>Peers</strong><br>${orchestrator.peers.length}</div>
        <div class="chip"><strong>A2A methods</strong><br>${(a2a.methods || []).length}</div>
        <div class="chip"><strong>Entry</strong><br>workflow.run</div>
      </div>
      <div class="workflow-detail-meta">${escapeHtml(orchestrator.activity || "No activity recorded.")}</div>
      <div class="platform-code">${escapeHtml(orchestrator.a2a_card_path || "/.well-known/agent-card.json")}</div>
      <div class="workflow-detail-actions">
        <button class="workflow-approve-button ready" data-open-agent="orchestrator">Open orchestrator workspace</button>
      </div>
    </div>
    <div class="message-item">
      <strong>Latest orchestration state</strong>
      ${latestWorkflow ? `
        <div>${escapeHtml(latestWorkflow.label || "workflow")}</div>
        <div class="muted">${escapeHtml(latestWorkflow.goal || "No goal recorded.")}</div>
        <div class="chip-row">
          <div class="chip"><strong>Status</strong><br>${escapeHtml(latestWorkflow.status || "unknown")}</div>
          <div class="chip"><strong>Backend</strong><br>${escapeHtml(latestWorkflow.graph_backend || data.multi_agent.graph_backend || "unknown")}</div>
          <div class="chip"><strong>Completed</strong><br>${latestWorkflow.completed_step_count || 0}/${(latestWorkflow.steps || []).length}</div>
        </div>
      ` : `<div class="muted">No workflow has been started yet.</div>`}
    </div>
  `;

  root.querySelectorAll("[data-open-agent]").forEach((button) => {
    button.addEventListener("click", () => {
      selectView(button.dataset.openAgent, "agent", true);
    });
  });
}

function renderPlatformTopology(workflows) {
  const root = document.getElementById("platform-workflows-panel");
  if (!root) {
    return;
  }
  const workflowRuns = portalState.workflowRuns || [];
  root.innerHTML = Object.entries(workflows || {}).map(([id, workflow]) => {
    const latestRun = workflowRuns.find((run) => run.workflow_id === id) || null;
    return `
      <div class="message-item">
        <strong>${escapeHtml(workflow.label || id)}</strong>
        <div class="muted">${escapeHtml(workflow.description || "No workflow description provided.")}</div>
        <div class="chip-row">${chipRow(workflow.steps || [])}</div>
        ${latestRun ? `<div class="workflow-detail-meta">Latest run ${escapeHtml(shortId(latestRun.id))} · ${escapeHtml(latestRun.status || "unknown")} · ${escapeHtml(latestRun.mode || "advisory")}</div>` : `<div class="workflow-detail-meta">No run recorded yet for this template.</div>`}
      </div>
    `;
  }).join("") || `<div class="message-item">No workflow templates are available.</div>`;
}

function renderSchedulerView(data) {
  const summaryRoot = document.getElementById("scheduler-summary-grid");
  const endpointRoot = document.getElementById("scheduler-endpoint-feed");
  if (!summaryRoot || !endpointRoot) {
    return;
  }
  const scheduler = data.scheduler || ((data.platform || {}).scheduler) || {leases: [], queues: []};
  const history = data.scheduler_history || ((data.platform || {}).scheduler_history) || {};
  const runtimeSafety = data.runtime_safety || ((data.platform || {}).runtime_safety) || null;
  const safetyState = runtimeSafetyState(runtimeSafety);
  const resetPending = Boolean(portalState.platformActionState.reset);
  const reconcilePending = Boolean(portalState.platformActionState.reconcile);

  summaryRoot.innerHTML = `
    <article class="stack-card platform-card">
      <p class="card-eyebrow">Scheduler</p>
      <h3>Resource Control</h3>
      ${statusPill((scheduler.queued_workflow_count || scheduler.active_lease_count) ? "queued" : "ready")}
      <p class="muted">${escapeHtml((scheduler.blocked_reasons || [])[0] || "No workflow is blocked right now.")}</p>
      <div class="chip-row">
        <div class="chip"><strong>Active leases</strong><br>${escapeHtml(String(scheduler.active_lease_count || 0))}</div>
        <div class="chip"><strong>Queued</strong><br>${escapeHtml(String(scheduler.queued_workflow_count || 0))}</div>
        <div class="chip"><strong>Safe for enforced</strong><br>${scheduler.safe_for_enforced ? "yes" : "no"}</div>
      </div>
    </article>
    <article class="stack-card platform-card">
      <p class="card-eyebrow">Runtime Safety</p>
      <h3>${escapeHtml(safetyState.title)}</h3>
      ${statusPill(safetyState.status)}
      <p class="muted">${escapeHtml(safetyState.body)}</p>
      <div class="chip-row">
        <div class="chip"><strong>Actions</strong><br>${escapeHtml(String((runtimeSafety && runtimeSafety.active_action_count) || 0))}</div>
        <div class="chip"><strong>Flows</strong><br>${escapeHtml(String((runtimeSafety && runtimeSafety.active_workflow_count) || 0))}</div>
        <div class="chip"><strong>Core</strong><br>${escapeHtml(String((runtimeSafety && runtimeSafety.essential_ready_count) || 0))}/${escapeHtml(String((runtimeSafety && runtimeSafety.essential_service_count) || 0))}</div>
      </div>
    </article>
    <article class="stack-card platform-card">
      <p class="card-eyebrow">Targeted Controls</p>
      <h3>Queue And Lease Ops</h3>
      ${statusPill("ready")}
      <p class="muted">Use reconcile, cancel, and drain before falling back to the emergency reset.</p>
      <div class="workflow-detail-actions">
        <button class="workflow-approve-button ready" data-runtime-reconcile="leases" ${reconcilePending ? "disabled" : ""}>${reconcilePending ? "Reconciling..." : "Reconcile Leases"}</button>
        <button class="workflow-button warning" data-runtime-reset="soft" ${resetPending ? "disabled" : ""}>${resetPending ? "Resetting..." : "Emergency Reset"}</button>
      </div>
      <div class="workflow-detail-meta">Reconcile releases stale scheduler state. Emergency reset clears portal-managed runtime state but does not restart FlexRIC services.</div>
    </article>
    <article class="stack-card platform-card">
      <p class="card-eyebrow">Audit Trail</p>
      <h3>Persistence</h3>
      ${statusPill("ready")}
      <p class="muted">Recent operator actions and implementation changes are loaded from SQLite-backed audit tables.</p>
      <div class="chip-row">
        <div class="chip"><strong>Actions</strong><br>${escapeHtml(String((history.operator_actions || []).length || 0))}</div>
        <div class="chip"><strong>Changes</strong><br>${escapeHtml(String((history.implementation_changes || []).length || 0))}</div>
      </div>
    </article>
  `;

  renderLeaseFeed((scheduler && scheduler.leases) || [], "scheduler-lease-feed");
  renderQueueFeed((scheduler && scheduler.queues) || [], "scheduler-queue-feed");
  renderWorkflowRunList(portalState.workflowRuns || [], "scheduler-workflow-run-list");
  renderWorkflowDetail(portalState.workflowDetail, "scheduler-workflow-detail-panel");
  renderAuditFeed(history.operator_actions || [], "scheduler-operator-feed", "No operator actions have been recorded yet.", "operator");
  renderAuditFeed(history.implementation_changes || [], "scheduler-change-feed", "No implementation changes are recorded yet.", "change");

  const endpoints = (history && history.endpoints) || {};
  endpointRoot.innerHTML = Object.keys(endpoints).length === 0
    ? `<div class="message-item">Scheduler endpoint metadata is unavailable.</div>`
    : Object.entries(endpoints).map(([key, value]) => `
      <div class="message-item">
        <strong>${escapeHtml(key)}</strong>
        <div class="platform-code">${escapeHtml(value)}</div>
      </div>
    `).join("");

  summaryRoot.querySelectorAll("[data-runtime-reset]").forEach((button) => {
    button.addEventListener("click", async () => {
      await resetRuntime(false);
    });
  });
  summaryRoot.querySelectorAll("[data-runtime-reconcile]").forEach((button) => {
    button.addEventListener("click", async () => {
      portalState.platformActionState.reconcile = true;
      renderSchedulerView(data);
      setBanner("Reconciling scheduler leases and queue state...");
      try {
        await fetchJson("/api/runtime/leases/reconcile", {method: "POST"});
        portalState.platformActionState.reconcile = false;
        await loadPortal(portalState.selectedWorkflowRunId);
        setBanner("Scheduler reconcile complete.", "success");
      } catch (error) {
        portalState.platformActionState.reconcile = false;
        renderSchedulerView(data);
        setBanner(error.message, "warning");
      }
    });
  });
}

function renderPlatform(platform, data) {
  const header = document.getElementById("platform-header");
  const overviewRoot = document.getElementById("platform-overview-grid");
  const toolsRoot = document.getElementById("platform-langchain-tools");
  const a2aRoot = document.getElementById("platform-a2a-panel");
  const routesRoot = document.getElementById("platform-routes-panel");
  const leaseRoot = document.getElementById("platform-lease-feed");
  const queueRoot = document.getElementById("platform-queue-feed");
  if (!header || !overviewRoot || !toolsRoot || !a2aRoot || !routesRoot || !leaseRoot || !queueRoot) {
    return;
  }
  if (!platform) {
    header.innerHTML = `
      <p class="eyebrow">LangGraph</p>
      <h2>Platform data unavailable</h2>
      <p class="lede">The portal could not load LangGraph, MCP, A2A, LangChain, or LangSmith status.</p>
    `;
    overviewRoot.innerHTML = `<div class="message-item">Platform status is unavailable.</div>`;
    toolsRoot.innerHTML = `<div class="message-item">No LangChain tool data available.</div>`;
    a2aRoot.innerHTML = `<div class="message-item">No A2A data available.</div>`;
    routesRoot.innerHTML = `<div class="message-item">No route data available.</div>`;
    return;
  }

  const langgraph = platform.langgraph || {};
  const langchain = platform.langchain || {};
  const a2a = platform.a2a || {};
  const langsmith = platform.langsmith || {};
  const routes = platform.routes || {};
  const mcpControl = platform.mcp_control || {};
  const mcpService = mcpControl.service || {};
  const runtimeSafety = data.runtime_safety || platform.runtime_safety || null;
  const scheduler = data.scheduler || platform.scheduler || (runtimeSafety && runtimeSafety.scheduler) || {leases: [], queues: []};
  const safetyState = runtimeSafetyState(runtimeSafety);
  const mcpPending = Boolean(portalState.platformActionState.mcp);
  const resetPending = Boolean(portalState.platformActionState.reset);

  header.innerHTML = `
    <p class="eyebrow">${escapeHtml(platform.label || "LangGraph")}</p>
    <h2>Orchestration And Runtime Architecture</h2>
    <p class="lede">${escapeHtml(platform.description || "Portal-integrated LangGraph orchestration and MCP runtime status.")}</p>
  `;

  overviewRoot.innerHTML = `
    <article class="stack-card platform-card">
      <p class="card-eyebrow">LangGraph</p>
      <h3>${escapeHtml(langgraph.backend || "unknown")}</h3>
      ${statusPill(langgraph.installed ? "ready" : "warning")}
      <p class="muted">${escapeHtml(langgraph.detail || "No LangGraph detail available.")}</p>
      <div class="chip-row">
        <div class="chip"><strong>Nodes</strong><br>${(langgraph.node_names || []).length}</div>
        <div class="chip"><strong>Templates</strong><br>${(langgraph.workflow_templates || []).length}</div>
      </div>
    </article>
    <article class="stack-card platform-card">
      <p class="card-eyebrow">LangChain</p>
      <h3>Portal Toolbox</h3>
      ${statusPill(langchain.installed ? "ready" : "warning")}
      <p class="muted">${escapeHtml(langchain.detail || "No LangChain detail available.")}</p>
      <div class="chip-row">
        <div class="chip"><strong>Tools</strong><br>${langchain.tool_count || 0}</div>
      </div>
    </article>
    <article class="stack-card platform-card">
      <p class="card-eyebrow">A2A</p>
      <h3>${escapeHtml(a2a.protocol || "A2A-aligned JSON-RPC")}</h3>
      ${statusPill(a2a.installed ? "ready" : "warning")}
      <p class="muted">${escapeHtml(a2a.detail || "No A2A detail available.")}</p>
      <div class="chip-row">
        <div class="chip"><strong>Methods</strong><br>${(a2a.methods || []).length}</div>
        <div class="chip"><strong>Cards</strong><br>${(a2a.cards || []).length}</div>
      </div>
    </article>
    <article class="stack-card platform-card">
      <p class="card-eyebrow">LangSmith</p>
      <h3>${escapeHtml(langsmith.project || "flexric-agent-portal")}</h3>
      ${statusPill(langsmith.enabled && langsmith.api_key_present ? "ready" : "warning")}
      <p class="muted">${escapeHtml(langsmith.detail || "No LangSmith detail available.")}</p>
      <div class="chip-row">
        <div class="chip"><strong>Installed</strong><br>${langsmith.installed ? "yes" : "no"}</div>
        <div class="chip"><strong>Tracing</strong><br>${langsmith.enabled ? "enabled" : "disabled"}</div>
      </div>
    </article>
    <article class="stack-card platform-card">
      <p class="card-eyebrow">Runtime Safety</p>
      <h3>${escapeHtml(safetyState.title)}</h3>
      ${statusPill(safetyState.status)}
      <p class="muted">${escapeHtml(safetyState.body)}</p>
      <div class="chip-row">
        <div class="chip"><strong>Core</strong><br>${escapeHtml(String((runtimeSafety && runtimeSafety.essential_ready_count) || 0))}/${escapeHtml(String((runtimeSafety && runtimeSafety.essential_service_count) || 0))}</div>
        <div class="chip"><strong>Actions</strong><br>${escapeHtml(String((runtimeSafety && runtimeSafety.active_action_count) || 0))}</div>
        <div class="chip"><strong>Flows</strong><br>${escapeHtml(String((runtimeSafety && runtimeSafety.active_workflow_count) || 0))}</div>
      </div>
      <div class="workflow-detail-actions">
        <button class="workflow-button warning" data-runtime-reset="soft" ${resetPending ? "disabled" : ""}>${resetPending ? "Resetting..." : "Emergency Reset"}</button>
        <div class="workflow-detail-meta">Emergency-only: stops active local actions and clears live portal-managed state. This is not the same as restarting the FlexRIC services.</div>
      </div>
    </article>

    <article class="stack-card platform-card">
      <p class="card-eyebrow">MCP Control</p>
      <h3>${escapeHtml(mcpService.label || "MCP Metrics")}</h3>
      ${statusPill(mcpService.status || "warning")}
      <p class="muted">${escapeHtml(mcpControl.langgraph_mode || "LangGraph can run without MCP when needed.")}</p>
      <div class="chip-row">
        <div class="chip"><strong>LangGraph</strong><br>${escapeHtml(mcpControl.langgraph_mode || "Graph runtime with optional MCP")}</div>
        <div class="chip"><strong>Overview</strong><br>${escapeHtml(mcpControl.mcp_mode || "Portal uses MCP automatically")}</div>
      </div>
      <div class="workflow-detail-actions">
        <button class="workflow-approve-button ready" data-mcp-control="start" ${mcpPending || mcpService.ok ? "disabled" : ""}>${mcpPending ? "Working..." : "Start MCP"}</button>
        <button class="workflow-button warning" data-mcp-control="stop" ${mcpPending || !mcpService.ok ? "disabled" : ""}>${mcpPending ? "Working..." : "Stop MCP"}</button>
        <div class="workflow-detail-meta">${escapeHtml(mcpService.public_url || mcpService.url || "")}</div>
      </div>
    </article>
  `;

  renderLeaseFeed((scheduler && scheduler.leases) || [], "platform-lease-feed");
  renderQueueFeed((scheduler && scheduler.queues) || [], "platform-queue-feed");
  renderPlatformOrchestrator(platform, data || {});
  renderPlatformTopology((data && data.workflow_templates) || {});
  renderProviders((data && data.providers) || [], "platform-provider-grid");
  renderWorkflowRunList(portalState.workflowRuns || [], "platform-workflow-run-list");
  renderWorkflowDetail(portalState.workflowDetail, "platform-workflow-detail-panel");
  renderSavedWorkflows(portalState.savedWorkflows || [], "platform-saved-workflow-list");
  renderMessages((data && data.messages) || [], "platform-message-feed");
  renderTasks((data && data.tasks) || [], "platform-task-feed");
  renderAgents((data && data.agents) || [], "platform-agent-grid");
  renderRuns((data && data.runs) || [], "platform-run-feed");

  toolsRoot.innerHTML = (langchain.tools || []).length === 0
    ? `<div class="message-item">No LangChain tools are registered in the portal toolbox yet.</div>`
    : (langchain.tools || []).map((tool) => `
      <div class="message-item">
        <strong>${escapeHtml(tool.name || "tool")}</strong>
        <div>${escapeHtml(tool.description || "No description provided.")}</div>
      </div>
    `).join("");

  a2aRoot.innerHTML = `
    <div class="message-item">
      <strong>RPC Endpoint</strong>
      <div class="platform-code">${escapeHtml(a2a.rpc_path || routes.rpc || "/api/a2a/rpc")}</div>
    </div>
    <div class="message-item">
      <strong>Orchestrator card</strong>
      <div class="platform-code">${escapeHtml(a2a.agent_card_path || routes.orchestrator_card || "/.well-known/agent-card.json")}</div>
    </div>
    <div class="message-item">
      <strong>Methods</strong>
      <ul class="platform-list">${(a2a.methods || []).map((method) => `<li>${escapeHtml(method)}</li>`).join("")}</ul>
    </div>
    <div class="message-item">
      <strong>Agent Cards</strong>
      <ul class="platform-list">${(a2a.cards || []).map((card) => `<li><span class="platform-code">${escapeHtml(card.path)}</span> · ${escapeHtml(card.name || card.agent_id || "agent")}</li>`).join("")}</ul>
    </div>
  `;

  routesRoot.innerHTML = `
    <div class="message-item">
      <strong>LangGraph Page</strong>
      <div class="platform-code">${escapeHtml(routes.page || "/platform")}</div>
    </div>
    <div class="message-item">
      <strong>Platform API</strong>
      <div class="platform-code">${escapeHtml(routes.overview || "/api/platform")}</div>
    </div>
    <div class="message-item">
      <strong>Workflow API</strong>
      <div class="platform-code">${escapeHtml(routes.workflow_list || "/api/workflows")}</div>
    </div>
    <div class="message-item">
      <strong>LangSmith</strong>
      <div class="platform-code">${escapeHtml(langsmith.endpoint || "https://api.smith.langchain.com")}</div>
      <div class="muted">Project: ${escapeHtml(langsmith.project || "flexric-agent-portal")}</div>
    </div>
  `;

  overviewRoot.querySelectorAll("[data-runtime-reset]").forEach((button) => {
    button.addEventListener("click", async () => {
      await resetRuntime(false);
    });
  });

  overviewRoot.querySelectorAll("[data-mcp-control]").forEach((button) => {
    button.addEventListener("click", async () => {
      const action = button.dataset.mcpControl;
      if (!action) {
        return;
      }
      portalState.platformActionState.mcp = action;
      renderPlatform(platform, data);
      setBanner(`${action === "stop" ? "Stopping" : "Starting"} MCP from the LangGraph page...`);
      try {
        await fetchJson(`/api/runtime/mcp/${action}`, {method: "POST"});
        portalState.platformActionState.mcp = null;
        await loadPortal(portalState.selectedWorkflowRunId);
        setBanner(`MCP ${action === "stop" ? "stopped" : "started"} from the LangGraph page.`, "success");
      } catch (error) {
        portalState.platformActionState.mcp = null;
        renderPlatform(platform, data);
        setBanner(error.message, "warning");
      }
    });
  });
}

function averageOf(values) {
  if (!values || values.length === 0) {
    return null;
  }
  return values.reduce((sum, value) => sum + Number(value || 0), 0) / values.length;
}

function summarizeFigurePayload(payload) {
  const figures = Array.isArray(payload && payload.figures) ? payload.figures : [];
  const metrics = {};
  figures.forEach((figure) => {
    (figure.series || []).forEach((series) => {
      const points = series.points || [];
      const latestPoint = points.length > 0 ? points[points.length - 1] : null;
      metrics[series.measurement || series.id] = {
        measurement: series.measurement || series.id,
        latest: latestPoint ? Number(latestPoint.y) : null,
        average: averageOf(points.map((point) => Number(point.y))),
        sample_count: points.length,
        color: series.color,
      };
    });
  });
  return metrics;
}

function formatMetricDelta(current, previous) {
  if (current === null || current === undefined || previous === null || previous === undefined) {
    return "n/a";
  }
  const delta = Number(current) - Number(previous);
  const prefix = delta > 0 ? "+" : "";
  return `${prefix}${formatMetricValue(delta)}`;
}

function snapshotWorkflowContext() {
  const preferred = (portalState.workflowRuns || []).find((run) => run.id === portalState.selectedWorkflowRunId);
  const latest = preferred || (portalState.workflowRuns || [])[0] || null;
  if (!latest) {
    return null;
  }
  return {
    id: latest.id,
    label: latest.label,
    workflow_id: latest.workflow_id,
    status: latest.status,
    mode: latest.mode,
    action_run_count: latest.action_run_count,
    started_at: latest.started_at,
    updated_at: latest.updated_at || latest.completed_at || latest.started_at,
  };
}

async function loadComparisonLiveFigures(force = false) {
  if (!force && portalState.comparisonLiveFigures) {
    return portalState.comparisonLiveFigures;
  }
  portalState.comparisonBusy.live = true;
  try {
    const payload = await fetchJson('/api/agents/kpm/figures');
    portalState.comparisonLiveFigures = payload;
    return payload;
  } finally {
    portalState.comparisonBusy.live = false;
  }
}

async function captureComparisonSnapshot(kind) {
  portalState.comparisonBusy[kind] = true;
  renderComparison(portalState.overview || {});
  try {
    const payload = await fetchJson('/api/agents/kpm/figures');
    portalState.comparisonLiveFigures = payload;
    portalState.comparisonSnapshots[kind] = {
      kind,
      captured_at: new Date().toISOString(),
      source: payload.source || {},
      detail: payload.detail || '',
      metrics: summarizeFigurePayload(payload),
      workflow: snapshotWorkflowContext(),
    };
    saveComparisonSnapshots();
    renderComparison(portalState.overview || {});
    setBanner(`${kind === 'baseline' ? 'Without-optimization' : 'With-optimization'} snapshot captured.`, 'success');
  } catch (error) {
    setBanner(error.message, 'warning');
  } finally {
    portalState.comparisonBusy[kind] = false;
    renderComparison(portalState.overview || {});
  }
}

function comparisonRunCard(title, run, emptyMessage) {
  if (!run) {
    return `<div class="figure-card"><h3>${escapeHtml(title)}</h3><div class="figure-empty">${escapeHtml(emptyMessage)}</div></div>`;
  }
  const duration = Math.max(0, Math.round(((run.updated_at || run.completed_at || run.started_at) - run.started_at)));
  return `
    <div class="figure-card">
      <div class="figure-card-head">
        <div>
          <h3>${escapeHtml(title)}</h3>
          <p class="figure-meta">${escapeHtml(run.label || run.workflow_id || 'workflow')}</p>
        </div>
        ${statusPill(run.status || 'pending')}
      </div>
      <div class="figure-summary-grid">
        <div class="figure-summary-chip"><span class="figure-meta">Run</span><strong>${escapeHtml(shortId(run.id))}</strong><span class="figure-series-meta">${escapeHtml(run.mode || 'advisory')}</span></div>
        <div class="figure-summary-chip"><span class="figure-meta">Duration</span><strong>${escapeHtml(String(duration))}s</strong><span class="figure-series-meta">window ${escapeHtml(String(run.duration_s || 45))}s</span></div>
        <div class="figure-summary-chip"><span class="figure-meta">Actions</span><strong>${escapeHtml(String(run.action_run_count || 0))}</strong><span class="figure-series-meta">completed ${escapeHtml(String(run.completed_step_count || 0))}/${escapeHtml(String((run.steps || []).length || 0))}</span></div>
        <div class="figure-summary-chip"><span class="figure-meta">Errors</span><strong>${escapeHtml(String((run.errors || []).length || 0))}</strong><span class="figure-series-meta">updated ${escapeHtml(formatTimestamp(run.updated_at || run.completed_at || run.started_at))}</span></div>
      </div>
    </div>
  `;
}

function comparisonSnapshotCard(title, snapshot, busy, emptyMessage) {
  if (!snapshot) {
    return `<div class="figure-card"><h3>${escapeHtml(title)}</h3><div class="figure-empty">${escapeHtml(busy ? 'Capturing snapshot...' : emptyMessage)}</div></div>`;
  }
  const metrics = Object.values(snapshot.metrics || {});
  return `
    <div class="figure-card">
      <div class="figure-card-head">
        <div>
          <h3>${escapeHtml(title)}</h3>
          <p class="figure-meta">${escapeHtml(snapshot.detail || 'KPM telemetry snapshot')}</p>
        </div>
        <div class="figure-source-meta">${escapeHtml(formatIsoTimestamp(snapshot.captured_at))}</div>
      </div>
      <div class="figure-summary-grid">
        <div class="figure-summary-chip"><span class="figure-meta">Metrics</span><strong>${escapeHtml(String(metrics.length))}</strong><span class="figure-series-meta">captured from KPM bus</span></div>
        <div class="figure-summary-chip"><span class="figure-meta">Workflow</span><strong>${escapeHtml(snapshot.workflow ? shortId(snapshot.workflow.id) : 'n/a')}</strong><span class="figure-series-meta">${escapeHtml(snapshot.workflow ? snapshot.workflow.label : 'No workflow linked')}</span></div>
        <div class="figure-summary-chip"><span class="figure-meta">Source</span><strong>${escapeHtml(snapshot.source.service || 'kpm_bus')}</strong><span class="figure-series-meta">${escapeHtml(String(snapshot.source.record_count || 0))} parsed records</span></div>
      </div>
      <div class="figure-recent-list">
        ${metrics.slice(0, 6).map((metric) => `
          <div class="message-item">
            <strong>${escapeHtml(metric.measurement)}</strong><br>
            latest=${escapeHtml(formatMetricValue(metric.latest))} · avg=${escapeHtml(formatMetricValue(metric.average))}<br>
            <span class="muted">samples ${escapeHtml(String(metric.sample_count || 0))}</span>
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

function renderComparison(data) {
  const workflowRoot = document.getElementById('comparison-workflow-panel');
  const liveRoot = document.getElementById('comparison-live-panel');
  const baselineRoot = document.getElementById('comparison-baseline-panel');
  const optimizedRoot = document.getElementById('comparison-optimized-panel');
  const metricRoot = document.getElementById('comparison-metric-panel');
  if (!workflowRoot || !liveRoot || !baselineRoot || !optimizedRoot || !metricRoot) {
    return;
  }

  if (!portalState.comparisonLiveFigures && !portalState.comparisonBusy.live) {
    loadComparisonLiveFigures(false).then(() => {
      if (portalState.selectedPageId === 'comparison') {
        renderComparison(portalState.overview || {});
      }
    }).catch((error) => {
      console.error(error);
    });
  }

  const runs = portalState.workflowRuns || [];
  const baselineRun = runs.find((run) => (run.action_run_count || 0) === 0 && (run.status || '') !== 'running');
  const optimizedRun = runs.find((run) => (run.action_run_count || 0) > 0);
  workflowRoot.innerHTML = `
    ${comparisonRunCard('Without Optimization Workflow', baselineRun, 'Run an advisory workflow without approving actions to establish a baseline.')}
    ${comparisonRunCard('With Optimization Workflow', optimizedRun, 'Approve a workflow so control actions launch, then compare its runtime behavior here.')}
  `;

  const live = portalState.comparisonLiveFigures;
  if (!live) {
    liveRoot.innerHTML = `<div class="figure-card"><div class="figure-empty">${portalState.comparisonBusy.live ? 'Loading live KPM telemetry...' : 'No live KPM telemetry loaded yet.'}</div></div>`;
  } else {
    liveRoot.innerHTML = `
      <div class="figure-card accent-card">
        <div class="figure-card-head">
          <div>
            <h3>Shared KPM Source</h3>
            <p class="figure-meta">${escapeHtml(live.detail || 'Current KPM bus status')}</p>
          </div>
          ${statusPill(live.status || 'warning')}
        </div>
        <div class="figure-summary-grid">
          <div class="figure-summary-chip"><span class="figure-meta">Indications</span><strong>${escapeHtml(String((live.source || {}).indication_count || 0))}</strong><span class="figure-series-meta">subscription events seen</span></div>
          <div class="figure-summary-chip"><span class="figure-meta">Parsed Records</span><strong>${escapeHtml(String((live.source || {}).record_count || 0))}</strong><span class="figure-series-meta">figure-ready samples</span></div>
          <div class="figure-summary-chip"><span class="figure-meta">Updated</span><strong>${escapeHtml(formatIsoTimestamp((live.source || {}).last_ts))}</strong><span class="figure-series-meta">latest bus refresh</span></div>
        </div>
      </div>
    `;
  }

  const baselineSnapshot = (portalState.comparisonSnapshots || {}).baseline || null;
  const optimizedSnapshot = (portalState.comparisonSnapshots || {}).optimized || null;
  baselineRoot.innerHTML = comparisonSnapshotCard('Without Optimization Snapshot', baselineSnapshot, Boolean(portalState.comparisonBusy.baseline), 'Capture a baseline before applying optimization actions.');
  optimizedRoot.innerHTML = comparisonSnapshotCard('With Optimization Snapshot', optimizedSnapshot, Boolean(portalState.comparisonBusy.optimized), 'Capture a second snapshot after the optimization run finishes.');

  const baselineMetrics = baselineSnapshot ? baselineSnapshot.metrics || {} : {};
  const optimizedMetrics = optimizedSnapshot ? optimizedSnapshot.metrics || {} : {};
  const metricNames = Array.from(new Set([...Object.keys(baselineMetrics), ...Object.keys(optimizedMetrics)])).sort();
  metricRoot.innerHTML = metricNames.length === 0
    ? `<div class="figure-card"><div class="figure-empty">Capture both snapshots to see metric deltas.</div></div>`
    : metricNames.map((name) => {
        const before = baselineMetrics[name] || {};
        const after = optimizedMetrics[name] || {};
        return `
          <div class="figure-card">
            <div class="figure-card-head">
              <div>
                <h3>${escapeHtml(name)}</h3>
                <p class="figure-meta">Compare latest and average values before and after tuning.</p>
              </div>
            </div>
            <div class="figure-summary-grid">
              <div class="figure-summary-chip"><span class="figure-meta">Before latest</span><strong>${escapeHtml(formatMetricValue(before.latest))}</strong><span class="figure-series-meta">avg ${escapeHtml(formatMetricValue(before.average))}</span></div>
              <div class="figure-summary-chip"><span class="figure-meta">After latest</span><strong>${escapeHtml(formatMetricValue(after.latest))}</strong><span class="figure-series-meta">avg ${escapeHtml(formatMetricValue(after.average))}</span></div>
              <div class="figure-summary-chip"><span class="figure-meta">Latest delta</span><strong>${escapeHtml(formatMetricDelta(after.latest, before.latest))}</strong><span class="figure-series-meta">after - before</span></div>
              <div class="figure-summary-chip"><span class="figure-meta">Average delta</span><strong>${escapeHtml(formatMetricDelta(after.average, before.average))}</strong><span class="figure-series-meta">after - before</span></div>
            </div>
          </div>
        `;
      }).join('');

  const refreshButton = document.getElementById('comparison-refresh');
  const baselineButton = document.getElementById('capture-baseline');
  const optimizedButton = document.getElementById('capture-optimized');
  const clearButton = document.getElementById('clear-comparison');
  if (refreshButton) {
    refreshButton.onclick = async () => {
      setBanner('Refreshing live comparison telemetry...');
      try {
        await loadComparisonLiveFigures(true);
        renderComparison(portalState.overview || {});
        setBanner('Comparison telemetry refreshed.', 'success');
      } catch (error) {
        setBanner(error.message, 'warning');
      }
    };
  }
  if (baselineButton) {
    baselineButton.disabled = Boolean(portalState.comparisonBusy.baseline);
    baselineButton.textContent = portalState.comparisonBusy.baseline ? 'Capturing...' : 'Capture Without Optimization';
    baselineButton.onclick = () => captureComparisonSnapshot('baseline');
  }
  if (optimizedButton) {
    optimizedButton.disabled = Boolean(portalState.comparisonBusy.optimized);
    optimizedButton.textContent = portalState.comparisonBusy.optimized ? 'Capturing...' : 'Capture With Optimization';
    optimizedButton.onclick = () => captureComparisonSnapshot('optimized');
  }
  if (clearButton) {
    clearButton.onclick = () => {
      portalState.comparisonSnapshots = {};
      saveComparisonSnapshots();
      renderComparison(portalState.overview || {});
      setBanner('Comparison snapshots cleared.', 'success');
    };
  }
}


function renderAgentWorkspace(agent, providers, agents) {
  if (!agent) {
    return;
  }

  document.title = `${agent.name} | FlexRIC Agent Portal`;

  document.getElementById("agent-header").innerHTML = `
    <p class="eyebrow">${agent.service_model}</p>
    <h2>${agent.name}</h2>
    ${statusPill(agent.status)}
    <p class="agent-meta">${agent.role}</p>
    <p class="lede">${agent.description}</p>
  `;

  document.getElementById("agent-card").innerHTML = `
    <div class="chip-row">
      <div class="chip"><strong>Skills</strong><br>${chipRow(agent.skills)}</div>
      <div class="chip"><strong>Measurements</strong><br>${chipRow(agent.measurements)}</div>
      <div class="chip"><strong>Use cases</strong><br>${chipRow(agent.use_cases)}</div>
      <div class="chip"><strong>Peers</strong><br>${chipRow(agent.peers)}</div>
    </div>
    <div class="message-item">
      <strong>A2A card</strong><br>
      <code>${agent.a2a_card_path}</code>
    </div>
    <div class="message-item">
      <strong>Current state</strong><br>
      ${agent.activity}
    </div>
    ${renderRuntimeScopePanel(agent.runtime_scope || null, "agent")}
  `;

  const actionRoot = document.getElementById("action-list");
  actionRoot.innerHTML = agent.actions.length === 0
    ? `<div class="action-item">No local launch action is wired yet for this agent.</div>`
    : agent.actions.map((action) => `
      <div class="action-item">
        <strong>${action.label}</strong>
        <p class="muted">${action.description}</p>
        <button class="action-button" data-action="${action.id}">Run action</button>
      </div>
    `).join("");

  actionRoot.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", async () => {
      setBanner(`Launching ${button.dataset.action} for ${agent.name}...`);
      try {
        await fetchJson(`/api/agents/${agent.id}/actions/${button.dataset.action}/run`, {method: "POST"});
        await loadPortal(portalState.selectedWorkflowRunId);
        setBanner(`Launched ${button.dataset.action} for ${agent.name}.`, "success");
      } catch (error) {
        setBanner(error.message, "warning");
      }
    });
  });

  const targetSelect = document.getElementById("target-agent");
  targetSelect.innerHTML = agents
    .filter((item) => item.id !== agent.id)
    .map((item) => `<option value="${item.id}">${item.name}</option>`)
    .join("");

  const providerSelect = document.getElementById("task-provider");
  providerSelect.innerHTML = [
    `<option value="auto">Auto select provider</option>`,
    ...providers.map((provider) => `
      <option value="${provider.id}" ${provider.enabled ? "" : "disabled"}>
        ${provider.label}${provider.enabled ? "" : " (not configured)"}
      </option>
    `),
  ].join("");

  document.getElementById("timeline-list").innerHTML = agent.timeline.length === 0
    ? `<div class="timeline-item">No agent events yet.</div>`
    : agent.timeline.map((entry) => `<div class="timeline-item">${entry}</div>`).join("");

  if (agent.latest_run) {
    document.getElementById("run-panel").innerHTML = `
      <div class="message-item">
        <strong>${agent.latest_run.label}</strong><br>
        ${statusPill(agent.latest_run.status)}
        <div class="muted">${agent.latest_run.cmd.join(" ")}</div>
      </div>
      <div class="run-tail">${escapeHtml((agent.latest_run.tail || []).join("\n") || "No log lines yet.")}</div>
    `;
  } else {
    document.getElementById("run-panel").innerHTML = `<div class="message-item">No run launched for this agent yet.</div>`;
  }

  if (agent.latest_task) {
    document.getElementById("task-panel").innerHTML = `
      <div class="message-item">
        <strong>${agent.latest_task.provider_id}</strong><br>
        ${statusPill(agent.latest_task.status)}
      </div>
      <div class="run-tail">${escapeHtml(agent.latest_task.response || agent.latest_task.error || "No response text yet.")}</div>
    `;
  } else {
    document.getElementById("task-panel").innerHTML = `<div class="message-item">No provider-backed task for this agent yet.</div>`;
  }

  loadAgentFigures(agent).catch((error) => {
    console.error(error);
  });
}

function wireAgentForms(agentId) {
  const handoffForm = document.getElementById("handoff-form");
  handoffForm.onsubmit = async (event) => {
    event.preventDefault();
    const payload = {
      target_id: document.getElementById("target-agent").value,
      content: document.getElementById("handoff-message").value,
      kind: "handoff",
    };
    try {
      const result = await fetchJson(`/api/agents/${agentId}/message`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload),
      });
      document.getElementById("handoff-result").innerHTML = `
        <div class="message-item"><strong>Sent</strong><br>${result.message.content}</div>
      `;
      await loadPortal(portalState.selectedWorkflowRunId);
      setBanner(`Handoff sent from ${agentId} to ${payload.target_id}.`, "success");
    } catch (error) {
      setBanner(error.message, "warning");
    }
  };

  const taskForm = document.getElementById("task-form");
  taskForm.onsubmit = async (event) => {
    event.preventDefault();
    const payload = {
      provider: document.getElementById("task-provider").value,
      prompt: document.getElementById("task-prompt").value,
    };
    document.getElementById("task-result").innerHTML = `<div class="message-item">Running provider task...</div>`;
    try {
      const result = await fetchJson(`/api/agents/${agentId}/tasks/run`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload),
      });
      const task = result.task;
      document.getElementById("task-result").innerHTML = `
        <div class="message-item">
          <strong>${task.provider_id}</strong><br>
          ${escapeHtml(task.response || task.error)}
        </div>
      `;
      await loadPortal(portalState.selectedWorkflowRunId);
      setBanner(`Provider task finished for ${agentId}.`, task.status === "completed" ? "success" : "warning");
    } catch (error) {
      setBanner(error.message, "warning");
    }
  };
}

function renderPortal(data) {
  portalState.overview = data;
  if (portalState.selectedAgentId && !data.agents.find((agent) => agent.id === portalState.selectedAgentId)) {
    portalState.selectedAgentId = null;
    portalState.selectedPageId = "overview";
  }
  renderTopMenu(data.agents);
  portalState.runtimeSafety = data.runtime_safety || null;
  renderStackHealth(data.multi_agent, portalState.runtimeSafety, data.scheduler || (data.multi_agent || {}).scheduler || null);
  renderWorkflows(data.workflow_templates);
  renderWorkflowEvents(data.multi_agent);
  renderRuns(data.runs || [], "run-feed");
  renderPlatform(data.platform || null, data);

  if (portalState.selectedAgentId) {
    const currentAgent = data.agents.find((agent) => agent.id === portalState.selectedAgentId);
    renderAgentWorkspace(currentAgent, data.providers, data.agents);
    wireAgentForms(portalState.selectedAgentId);
  } else if (portalState.selectedPageId === "platform") {
    document.title = "LangGraph | FlexRIC Agent Portal";
  } else if (portalState.selectedPageId === "scheduler") {
    document.title = "Scheduler | FlexRIC Agent Portal";
    renderSchedulerView(data);
  } else if (portalState.selectedPageId === "comparison") {
    document.title = "Comparison | FlexRIC Agent Portal";
    renderComparison(data);
  } else {
    document.title = "FlexRIC Agent Portal";
  }
}

async function loadWorkflowDetail(runId) {
  if (!runId) {
    portalState.workflowDetail = null;
    return;
  }
  const [detail, eventPayload] = await Promise.all([
    fetchJson(`/api/workflows/${runId}`),
    fetchJson(`/api/workflows/${runId}/events`),
  ]);
  detail.events = Array.isArray(eventPayload.events) ? eventPayload.events : (detail.events || []);
  portalState.workflowDetail = detail;
}

async function loadPortal(preferredWorkflowRunId = null) {
  const [data, workflowPayload] = await Promise.all([
    fetchJson("/api/overview"),
    fetchJson("/api/workflows"),
  ]);

  portalState.workflowRuns = Array.isArray(workflowPayload.runs) ? workflowPayload.runs : [];
  portalState.savedWorkflows = Array.isArray(data.saved_workflows) ? data.saved_workflows : [];

  let nextWorkflowRunId = preferredWorkflowRunId || portalState.selectedWorkflowRunId;
  if (nextWorkflowRunId && !portalState.workflowRuns.find((run) => run.id === nextWorkflowRunId)) {
    nextWorkflowRunId = null;
  }
  if (!nextWorkflowRunId && portalState.workflowRuns.length > 0) {
    nextWorkflowRunId = portalState.workflowRuns[0].id;
  }
  portalState.selectedWorkflowRunId = nextWorkflowRunId;

  if (nextWorkflowRunId) {
    await loadWorkflowDetail(nextWorkflowRunId);
  } else {
    portalState.workflowDetail = null;
  }

  renderPortal(data);
}

function startAutoRefresh() {
  if (portalState.refreshTimer) {
    clearInterval(portalState.refreshTimer);
  }
  portalState.refreshTimer = window.setInterval(() => {
    loadPortal(portalState.selectedWorkflowRunId).catch((error) => {
      console.error(error);
      setBanner(`Auto-refresh failed: ${error.message}`, "warning");
    });
  }, 3000);
}

function wireTopLevelActions() {
  document.getElementById("refresh-button").addEventListener("click", async () => {
    try {
      await loadPortal(portalState.selectedWorkflowRunId);
      setBanner("Portal refreshed.", "success");
    } catch (error) {
      setBanner(error.message, "warning");
    }
  });

  document.getElementById("reset-runtime-button").addEventListener("click", async () => {
    await resetRuntime(false);
  });

  document.getElementById("test-all-button").addEventListener("click", async () => {
    setBanner("Running test-all across the agent chain...");
    try {
      await fetchJson("/api/test-all", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({include_actions: true, include_messages: true}),
      });
      await loadPortal(portalState.selectedWorkflowRunId);
      setBanner("Test-all completed. Check runs, messages, and agent timelines.", "success");
    } catch (error) {
      setBanner(error.message, "warning");
    }
  });

  window.addEventListener("popstate", async () => {
    const route = currentRouteState();
    portalState.selectedAgentId = route.agentId;
    portalState.selectedPageId = route.pageId || (route.agentId ? "agent" : "overview");
    portalState.selectedWorkflowRunId = route.workflowRunId;
    selectView(route.agentId, portalState.selectedPageId, false);
    try {
      await loadPortal(route.workflowRunId);
    } catch (error) {
      setBanner(error.message, "warning");
    }
  });
}

async function boot() {
  const route = currentRouteState();
  portalState.selectedAgentId = route.agentId;
  portalState.selectedPageId = route.pageId || (route.agentId ? "agent" : "overview");
  portalState.selectedWorkflowRunId = route.workflowRunId;
  wireTopLevelActions();
  selectView(portalState.selectedAgentId, portalState.selectedPageId, false);
  await loadPortal(route.workflowRunId);
  startAutoRefresh();
}

boot().catch((error) => {
  console.error(error);
  document.body.insertAdjacentHTML("beforeend", `<div class="message-item">Failed to load portal: ${error.message}</div>`);
});
