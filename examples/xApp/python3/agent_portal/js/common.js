export function statusPill(status) {
  return `<span class="status-pill ${status}">${status}</span>`;
}

export function chipRow(items) {
  return items.map((item) => `<div class="chip">${item}</div>`).join("");
}

export function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

export function setBanner(message, variant = "info") {
  const banner = document.getElementById("portal-banner");
  if (!banner) {
    return;
  }
  banner.className = `message-item banner ${variant}`;
  banner.textContent = message;
}

export function formatTimestamp(epochSeconds) {
  if (!epochSeconds) {
    return "n/a";
  }
  return new Date(epochSeconds * 1000).toLocaleString();
}

export function shortId(value) {
  if (!value) {
    return "n/a";
  }
  return String(value).slice(0, 8);
}

export function resourceListText(resources) {
  const items = Array.isArray(resources) ? resources : [];
  if (items.length === 0) {
    return "none";
  }
  return items.map((item) => `${item.id}:${item.mode}`).join(", ");
}
