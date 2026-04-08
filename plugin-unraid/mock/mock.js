const API_BASE = "http://localhost:8000/api";

const statusEl = document.getElementById("status");
const rowsEl = document.getElementById("rows");
const totalEl = document.getElementById("kpi-total");
const tautulliEl = document.getElementById("kpi-tautulli");
const sftpgoEl = document.getElementById("kpi-sftpgo");
const refreshBtn = document.getElementById("btn-refresh");

function sourceBadge(source) {
  const txt = String(source || "unknown").toUpperCase();
  return `<span class="badge">${txt}</span>`;
}

function safe(text) {
  return String(text ?? "").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

async function getJson(path) {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

function renderSessions(sessions) {
  if (!Array.isArray(sessions) || sessions.length === 0) {
    rowsEl.innerHTML = `<tr><td colspan="4">No active sessions</td></tr>`;
    return;
  }

  rowsEl.innerHTML = sessions
    .slice(0, 12)
    .map(
      (item) => `
      <tr>
        <td>${safe(item.user_name || "-")}</td>
        <td>${safe(item.title || item.file_name || "-")}</td>
        <td>${sourceBadge(item.source)}</td>
        <td>${safe(item.bandwidth_human || "n/a")}</td>
      </tr>
    `,
    )
    .join("");
}

function renderTotals(overview) {
  const active = Number(overview?.active_sessions || 0);
  totalEl.textContent = String(active);

  const bySource = Array.isArray(overview?.active_by_source) ? overview.active_by_source : [];
  const tautulli = bySource.find((x) => x.source === "tautulli")?.sessions ?? 0;
  const sftpgo = bySource.find((x) => x.source === "sftpgo")?.sessions ?? 0;

  tautulliEl.textContent = String(tautulli);
  sftpgoEl.textContent = String(sftpgo);
}

async function refresh() {
  statusEl.textContent = "Loading...";
  try {
    const [sessions, overview] = await Promise.all([
      getJson("/sessions/active?limit=50"),
      getJson("/stats/overview"),
    ]);

    renderSessions(sessions);
    renderTotals(overview);
    statusEl.textContent = `Updated ${new Date().toLocaleTimeString()}`;
  } catch (error) {
    console.error(error);
    statusEl.textContent = `Error loading data: ${error.message}`;
  }
}

refreshBtn?.addEventListener("click", refresh);
refresh();
setInterval(refresh, 15000);