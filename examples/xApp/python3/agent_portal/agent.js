async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

function statusPill(status) {
  return `<span class="status-pill ${status}">${status}</span>`;
}

function chips(items) {
  return items.map((item) => `<div class="chip">${item}</div>`).join("");
}

function queryAgentId() {
  const parts = window.location.pathname.split("/");
  return parts[parts.length - 1];
}

async function loadAgentPage() {
  const agentId = queryAgentId();
  const [agent, allAgents] = await Promise.all([
    fetchJson(`/api/agents/${agentId}`),
    fetchJson("/api/agents"),
  ]);

  document.title = `${agent.name} | FlexRIC Agent Portal`;

  document.getElementById("agent-header").innerHTML = `
    <p class="eyebrow">${agent.service_model}</p>
    <h1>${agent.name}</h1>
    ${statusPill(agent.status)}
    <p class="agent-meta">${agent.role}</p>
    <p class="lede">${agent.description}</p>
  `;

  document.getElementById("agent-card").innerHTML = `
    <div class="chip-row">
      <div class="chip"><strong>Skills</strong><br>${chips(agent.skills)}</div>
      <div class="chip"><strong>Measurements</strong><br>${chips(agent.measurements)}</div>
      <div class="chip"><strong>Use cases</strong><br>${chips(agent.use_cases)}</div>
      <div class="chip"><strong>Peers</strong><br>${chips(agent.peers)}</div>
    </div>
    <div class="message-item">
      <strong>A2A card</strong><br>
      <code>${agent.a2a_card_path}</code>
    </div>
    <div class="message-item">
      <strong>Current activity</strong><br>
      ${agent.activity}
    </div>
  `;

  document.getElementById("action-list").innerHTML = agent.actions.length === 0
    ? `<div class="action-item">No local launch action is wired yet for this agent.</div>`
    : agent.actions.map((action) => `
      <div class="action-item">
        <strong>${action.label}</strong>
        <p class="muted">${action.description}</p>
        <button class="action-button" data-action="${action.id}">Run action</button>
      </div>
    `).join("");

  document.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", async () => {
      await fetchJson(`/api/agents/${agentId}/actions/${button.dataset.action}/run`, {method: "POST"});
      await refreshAgent(agentId);
    });
  });

  const targetSelect = document.getElementById("target-agent");
  targetSelect.innerHTML = allAgents
    .filter((item) => item.id !== agentId)
    .map((item) => `<option value="${item.id}">${item.name}</option>`)
    .join("");

  document.getElementById("handoff-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = {
      target_id: targetSelect.value,
      content: document.getElementById("handoff-message").value,
      kind: "handoff",
    };
    const result = await fetchJson(`/api/agents/${agentId}/message`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload),
    });
    document.getElementById("handoff-result").innerHTML = `
      <div class="message-item"><strong>Sent</strong><br>${result.message.content}</div>
    `;
    await refreshAgent(agentId);
  });

  await refreshAgent(agentId);
}

async function refreshAgent(agentId) {
  const agent = await fetchJson(`/api/agents/${agentId}`);
  document.getElementById("timeline-list").innerHTML = agent.timeline.length === 0
    ? `<div class="timeline-item">No agent events yet.</div>`
    : agent.timeline.map((entry) => `<div class="timeline-item">${entry}</div>`).join("");

  if (agent.latest_run) {
    document.getElementById("run-panel").innerHTML = `
      <div class="message-item">
        <strong>${agent.latest_run.label}</strong><br>
        ${statusPill(agent.latest_run.status)}
      </div>
      <div class="run-tail">${(agent.latest_run.tail || []).join("\n") || "No log lines yet."}</div>
    `;
  } else {
    document.getElementById("run-panel").innerHTML = `<div class="message-item">No run launched for this agent yet.</div>`;
  }
}

loadAgentPage().catch((error) => {
  console.error(error);
  document.body.insertAdjacentHTML("beforeend", `<div class="message-item">Failed to load agent page: ${error.message}</div>`);
});
