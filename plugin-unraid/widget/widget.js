const DEFAULT_CONFIG = {
  streamfuseApiBase: "http://localhost:8000/api",
  streamfuseAppUrl: "http://localhost:5173",
  refreshSeconds: 10,
  maxVisibleSessions: 5,
};

function loadConfig() {
  const params = new URLSearchParams(window.location.search);
  return {
    streamfuseApiBase: params.get("apiBase") || DEFAULT_CONFIG.streamfuseApiBase,
    streamfuseAppUrl: params.get("appUrl") || DEFAULT_CONFIG.streamfuseAppUrl,
    refreshSeconds: Number(params.get("refresh") || DEFAULT_CONFIG.refreshSeconds),
    maxVisibleSessions: Number(params.get("limit") || DEFAULT_CONFIG.maxVisibleSessions),
  };
}

const config = loadConfig();

const stateLoading = document.getElementById("state-loading");
const stateError = document.getElementById("state-error");
const stateEmpty = document.getElementById("state-empty");
const stateList = document.getElementById("state-list");
const sessionsList = document.getElementById("sessions-list");
const summaryText = document.getElementById("sf-summary-text");
const moreCount = document.getElementById("more-count");
const openApp = document.getElementById("sf-open-app");
const retryBtn = document.getElementById("btn-retry");

const kpiActive = document.getElementById("kpi-active");
const kpiTautulli = document.getElementById("kpi-tautulli");
const kpiSftpgo = document.getElementById("kpi-sftpgo");
const kpiBandwidth = document.getElementById("kpi-bandwidth");

openApp.href = config.streamfuseAppUrl;

function showState(name) {
  stateLoading.classList.add("sf-hidden");
  stateError.classList.add("sf-hidden");
  stateEmpty.classList.add("sf-hidden");
  stateList.classList.add("sf-hidden");

  if (name === "loading") stateLoading.classList.remove("sf-hidden");
  if (name === "error") stateError.classList.remove("sf-hidden");
  if (name === "empty") stateEmpty.classList.remove("sf-hidden");
  if (name === "list") stateList.classList.remove("sf-hidden");
}

function toPosterUrl(posterUrl) {
  if (!posterUrl) return "./assets/poster-placeholder.svg";
  if (posterUrl.startsWith("http://") || posterUrl.startsWith("https://")) return posterUrl;

  const api = config.streamfuseApiBase.replace(/\/$/, "");
  const baseHost = api.replace(/\/api(?:\/v1)?$/, "");
  return `${baseHost}${posterUrl}`;
}

function sourceClass(source) {
  return String(source || "").toLowerCase() === "sftpgo" ? "sf-source sftpgo" : "sf-source";
}

function renderKpis(summary) {
  kpiActive.textContent = String(summary.active_sessions ?? 0);
  kpiTautulli.textContent = String(summary.tautulli_sessions ?? 0);
  kpiSftpgo.textContent = String(summary.sftpgo_sessions ?? 0);
  kpiBandwidth.textContent = summary.total_bandwidth_human || "0 Mbps";
}

function renderRows(sessions, hiddenCount) {
  sessionsList.innerHTML = sessions
    .map((session) => {
      const title = session.title || "Untitled";
      const user = session.user_name || "unknown";
      const source = String(session.source || "unknown");
      const speed = session.bandwidth_human || "n/a";
      const poster = toPosterUrl(session.poster_url);

      return `
      <li>
        <a class="sf-row" href="${config.streamfuseAppUrl}" target="_blank" rel="noreferrer">
          <img class="sf-poster" src="${poster}" alt="poster" loading="lazy" />
          <div>
            <p class="sf-title">${escapeHtml(title)}</p>
            <p class="sf-meta">
              <span>${escapeHtml(user)}</span>
              <span>&middot;</span>
              <span class="${sourceClass(source)}">${escapeHtml(source)}</span>
              <span>&middot;</span>
              <span>${escapeHtml(speed)}</span>
            </p>
          </div>
        </a>
      </li>
      `;
    })
    .join("");

  if (hiddenCount > 0) {
    moreCount.textContent = `+${hiddenCount} more`;
    moreCount.classList.remove("sf-hidden");
  } else {
    moreCount.classList.add("sf-hidden");
  }
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function fetchWidgetData() {
  const limit = Math.min(Math.max(config.maxVisibleSessions, 3), 5);
  const url = `${config.streamfuseApiBase.replace(/\/$/, "")}/dashboard/widget?limit=${limit}`;
  const response = await fetch(url);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

async function refresh() {
  showState("loading");
  summaryText.textContent = "Loading sessions...";

  try {
    const data = await fetchWidgetData();
    const summary = data.summary || {};
    const sessions = Array.isArray(data.sessions) ? data.sessions : [];

    renderKpis(summary);

    if (summary.active_sessions === 0 || sessions.length === 0) {
      summaryText.textContent = "No active sessions";
      showState("empty");
      return;
    }

    renderRows(sessions, Number(data.hidden_count || 0));
    summaryText.textContent = `${summary.active_sessions} active now`;
    showState("list");
  } catch (error) {
    console.error(error);
    summaryText.textContent = "StreamFuse unavailable";
    showState("error");
  }
}

retryBtn?.addEventListener("click", () => {
  void refresh();
});

void refresh();
window.setInterval(() => {
  void refresh();
}, Math.max(config.refreshSeconds, 5) * 1000);
