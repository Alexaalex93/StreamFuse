(function () {
  const root = document.getElementById('streamfuse-widget-root');
  if (!root) return;

  const summaryEl = document.getElementById('streamfuse-widget-summary');
  const listEl = document.getElementById('streamfuse-widget-list');
  const refreshBtn = document.getElementById('streamfuse-widget-refresh');
  const openLink = document.getElementById('streamfuse-widget-open');

  let refreshMs = 10000;
  let timer = null;

  function esc(text) {
    return String(text || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  async function loadConfig() {
    const r = await fetch('/plugins/streamfuse-widget/api/config.php', { credentials: 'same-origin' });
    if (!r.ok) throw new Error('Cannot load widget config');
    return r.json();
  }

  function renderSummary(summary) {
    const active = Number(summary?.active_sessions || 0);
    const tautulli = Number(summary?.tautulli_sessions || 0);
    const sftpgo = Number(summary?.sftpgo_sessions || 0);
    const samba = Number(summary?.samba_sessions || 0);
    const bw = summary?.total_bandwidth_human || '0 Mbps';

    summaryEl.innerHTML =
      '<div class="sf-kpis">' +
        '<div class="sf-kpi"><span>Active</span><strong>' + active + '</strong></div>' +
        '<div class="sf-kpi"><span>Tautulli</span><strong>' + tautulli + '</strong></div>' +
        '<div class="sf-kpi"><span>SFTPGo</span><strong>' + sftpgo + '</strong></div>' +
        '<div class="sf-kpi"><span>Samba</span><strong>' + samba + '</strong></div>' +
      '</div>' +
      '<div style="margin-top:8px;color:#9ab0d8;font-size:12px;">Bandwidth: ' + esc(bw) + '</div>';
  }

  function sourceClass(source) {
    const s = String(source || '').toLowerCase();
    if (s === 'sftpgo') return 'sftpgo';
    if (s === 'samba') return 'samba';
    return 'tautulli';
  }

  function renderList(data, appUrl) {
    const sessions = Array.isArray(data?.sessions) ? data.sessions : [];
    if (!sessions.length) {
      listEl.innerHTML = '<div class="sf-state"><p>No active sessions</p></div>';
      return;
    }

    const rows = sessions.map((s) => {
      const src = String(s.source || 'unknown').toUpperCase();
      const cls = sourceClass(s.source);
      const poster = s.poster_url || '/plugins/streamfuse-widget/widget/assets/poster-placeholder.svg';
      return '' +
        '<a class="sf-row" href="' + esc(appUrl) + '" target="_blank" rel="noopener noreferrer">' +
          '<img class="sf-poster" src="' + esc(poster) + '" loading="lazy" />' +
          '<div>' +
            '<p class="sf-title">' + esc(s.title || 'n/a') + '</p>' +
            '<div class="sf-meta">' +
              '<span>' + esc(s.user_name || 'n/a') + '</span>' +
              '<span class="sf-source ' + cls + '">' + esc(src) + '</span>' +
              '<span>' + esc(s.bandwidth_human || 'n/a') + '</span>' +
            '</div>' +
          '</div>' +
        '</a>';
    }).join('');

    const hidden = Number(data?.hidden_count || 0);
    listEl.innerHTML = '<ul>' + rows + '</ul>' + (hidden > 0 ? '<p class="sf-more">+' + hidden + ' more</p>' : '');
  }

  async function refresh(config) {
    const response = await fetch('/plugins/streamfuse-widget/api/widget_data.php', { credentials: 'same-origin' });
    if (!response.ok) throw new Error('Cannot reach StreamFuse');
    const data = await response.json();
    renderSummary(data.summary || {});
    renderList(data, config.app_url || 'http://127.0.0.1:5173');
  }

  async function boot() {
    try {
      const config = await loadConfig();
      openLink.href = config.app_url || 'http://127.0.0.1:5173';
      refreshMs = Math.max(3000, Number(config.refresh_seconds || 10) * 1000);

      const doRefresh = () => {
        refresh(config).catch((err) => {
          listEl.innerHTML = '<div class="sf-state"><p>' + esc(err.message || 'Error') + '</p></div>';
        });
      };

      doRefresh();
      refreshBtn?.addEventListener('click', doRefresh);
      timer = setInterval(doRefresh, refreshMs);
    } catch (err) {
      listEl.innerHTML = '<div class="sf-state"><p>Widget initialization failed</p></div>';
    }
  }

  boot();
  window.addEventListener('beforeunload', () => timer && clearInterval(timer));
})();
