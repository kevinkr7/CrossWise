/**
 * dashboard.js — Personalized, Live Breeding Intelligence Dashboard
 * Tailored specifically to the logged-in user with live data from MongoDB.
 */

'use strict';

window._userHistory = [];
window._activeRunIndex = 0;

document.addEventListener('DOMContentLoaded', () => {
  initUserGreeting();
  loadDashboardData();
  setupHistoryActions();
});

/* ── User Greeting & Personalization ─────────────────────────────────────── */
function initUserGreeting() {
  const user = typeof getCurrentUser === 'function' ? getCurrentUser() : null;
  if (!user) return;

  // Personalized greeting
  const greetingEl = document.getElementById('user-greeting-text');
  if (greetingEl) {
    const firstName = user.name ? user.name.split(' ')[0] : 'Researcher';
    greetingEl.textContent = `Welcome back, ${firstName} 👋`;
  }

  // Email
  const emailEl = document.getElementById('user-email-display');
  if (emailEl && user.email) {
    emailEl.textContent = user.email;
  }

  // Role
  const roleEl = document.getElementById('user-role-badge');
  if (roleEl) {
    roleEl.innerHTML = user.is_admin
      ? `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:12px;height:12px"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg> System Administrator`
      : `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:12px;height:12px"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg> Breeding Specialist`;
  }

  // Avatar initials
  const avatarEl = document.getElementById('user-avatar-initials');
  if (avatarEl && user.name) {
    const parts = user.name.trim().split(/\s+/);
    const initials = parts.length > 1
      ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
      : parts[0].substring(0, 2).toUpperCase();
    avatarEl.textContent = initials;
  }
}

/* ── Load Dashboard Data from MongoDB via API ────────────────────────────── */
async function loadDashboardData() {
  try {
    const res = await apiFetch(`${API_BASE}/api/history`);
    const history = res.history || [];
    window._userHistory = history;

    // 1. Calculate & Render User-Specific Breeding KPIs
    renderUserStats(history);

    // 2. Render Active Recommendation Showcase & Table
    if (history.length > 0) {
      window._activeRunIndex = 0;
      renderActiveRun(0);
    } else {
      renderEmptyDashboard();
    }

    // 3. Render User's History List
    renderHistoryList(history);

  } catch (err) {
    console.error("Failed to load user dashboard data:", err);
    renderEmptyDashboard("Unable to connect to your virtual breeding history.");
  }
}

/* ── User-Specific Breeding KPI Aggregates ───────────────────────────────── */
function renderUserStats(history) {
  const runsEl = document.getElementById('stat-user-runs');
  const yieldEl = document.getElementById('stat-user-best-yield');
  const scoreEl = document.getElementById('stat-user-best-score');
  const pairsEl = document.getElementById('stat-user-pairs');

  if (!history.length) {
    if (runsEl) runsEl.textContent = '0';
    if (yieldEl) yieldEl.textContent = '—';
    if (scoreEl) scoreEl.textContent = '—';
    if (pairsEl) pairsEl.textContent = '0';
    return;
  }

  // Total runs
  if (runsEl) runsEl.textContent = history.length.toLocaleString();

  // Find max yield and max composite score across all user runs
  let maxYield = 0;
  let maxScore = 0;
  let totalPairsScreened = 0;

  history.forEach(run => {
    totalPairsScreened += (run.total_pairs || 0);
    if (run.top_score && run.top_score > maxScore) {
      maxScore = run.top_score;
    }
    if (run.results && Array.isArray(run.results)) {
      run.results.forEach(r => {
        const y = parseFloat(r.predicted_yield);
        if (!isNaN(y) && y > maxYield) maxYield = y;
        const s = parseFloat(r.recommendation_score);
        if (!isNaN(s) && s > maxScore) maxScore = s;
      });
    }
  });

  if (yieldEl) yieldEl.textContent = maxYield > 0 ? `${maxYield.toFixed(2)} t/ha` : '—';
  if (scoreEl) scoreEl.textContent = maxScore > 0 ? formatScore(maxScore) : '—';
  if (pairsEl) pairsEl.textContent = totalPairsScreened.toLocaleString();
}

/* ── Render Active Run ───────────────────────────────────────────────────── */
function renderActiveRun(index) {
  const history = window._userHistory || [];
  const run = history[index];
  if (!run) return;

  window._activeRunIndex = index;

  const topRec = run.results?.[0] || {
    hybrid_name: run.top_hybrid || 'Hybrid Cross',
    recommendation_score: run.top_score || 0.8,
    predicted_yield: 9.5,
    predicted_drought: 'High',
    predicted_disease: 'Resistant',
    confidence: 0.85
  };

  // 1. Run Banner (if viewing older run)
  const banner = document.getElementById('run-active-banner');
  const bannerDate = document.getElementById('run-banner-date');
  const bannerPairs = document.getElementById('run-banner-pairs');
  if (banner) {
    if (index === 0) {
      banner.classList.add('hidden');
    } else {
      banner.classList.remove('hidden');
      if (bannerDate) bannerDate.textContent = formatDate(run.timestamp);
      if (bannerPairs) bannerPairs.textContent = (run.total_pairs || 0).toLocaleString();
    }
  }

  // 2. Showcase Hero Card
  const topRecContainer = document.getElementById('top-rec-container');
  if (topRecContainer) {
    topRecContainer.innerHTML = `
      <div class="card card--glow" style="height:100%;display:flex;flex-direction:column;justify-content:center">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:var(--s2)">
          <span class="tag tag--success">Top Recommended Hybrid Pair</span>
          <span style="font-size:var(--t-xs);color:var(--muted)">Run from ${formatDate(run.timestamp)}</span>
        </div>
        <div style="font-family:var(--ff-display);font-size:var(--t-3xl);font-weight:600;color:var(--sage-900);margin-bottom:var(--s1)">
          ${topRec.hybrid_name}
        </div>
        <p style="font-size:var(--t-sm);color:var(--muted);margin-bottom:var(--s3)">
          Ranked #1 candidate with predicted yield of <strong style="color:var(--sage-800)">${formatYield(topRec.predicted_yield)}</strong> and highest composite suitability score.
        </p>
        <div style="display:flex;gap:var(--s2);flex-wrap:wrap;align-items:center">
          <span class="resistance-badge ${topRec.predicted_drought === 'High' ? 'badge--high' : 'badge--medium'}">
            ${topRec.predicted_drought || 'Moderate'} Drought
          </span>
          <span class="resistance-badge ${topRec.predicted_disease === 'Resistant' ? 'badge--high' : 'badge--medium'}">
            ${topRec.predicted_disease || 'Moderate'}
          </span>
          <span style="font-size:var(--t-xs);color:var(--muted);margin-left:auto">
            Compatibility: <strong>${((topRec.genomic_compatibility || 0.7) * 100).toFixed(0)}%</strong>
          </span>
        </div>
      </div>`;
  }

  // 3. Side & Row Metric Cards
  setEl('metric-yield', formatYield(topRec.predicted_yield));
  setEl('metric-score', formatScore(topRec.recommendation_score));
  setEl('dc-yield', formatYield(topRec.predicted_yield));
  setEl('dc-drought', topRec.predicted_drought || '—');
  setEl('dc-disease', topRec.predicted_disease || '—');
  setEl('dc-confidence', formatScore(topRec.confidence));

  // 4. Recommendations Table
  const tableBody = document.getElementById('rec-table-body');
  const results = run.results || [];
  if (tableBody) {
    if (results.length === 0) {
      tableBody.innerHTML = `<tr><td colspan="9" style="text-align:center;color:var(--muted);padding:var(--s6)">No recommendations recorded in this simulation run.</td></tr>`;
    } else {
      tableBody.innerHTML = results.map(r => `
        <tr>
          <td style="font-weight:700;color:var(--sage-700)">#${r.rank}</td>
          <td style="font-weight:600">${r.hybrid_name}</td>
          <td>${formatYield(r.predicted_yield)}</td>
          <td><span class="resistance-badge ${r.predicted_drought === 'High' ? 'badge--high' : r.predicted_drought === 'Low' ? 'badge--low' : 'badge--medium'}">${r.predicted_drought || '—'}</span></td>
          <td><span class="resistance-badge ${r.predicted_disease === 'Resistant' ? 'badge--high' : r.predicted_disease === 'Susceptible' ? 'badge--low' : 'badge--medium'}">${r.predicted_disease || '—'}</span></td>
          <td>${r.predicted_quality || 'Standard'}</td>
          <td>${r.predicted_maturity || 'Medium'}</td>
          <td style="font-weight:700;color:var(--sage-800)">${formatScore(r.recommendation_score)}</td>
          <td>${formatScore(r.confidence)}</td>
        </tr>
      `).join('');
    }
  }

  // 5. Update "View Full Screen" button to save this run into session
  const btnFull = document.getElementById('btn-view-full-rec');
  if (btnFull) {
    btnFull.onclick = () => {
      lsSet('lastRecommendation', run.results);
      lsSet('last_total_pairs', run.total_pairs);
      lsSet('last_unique_parents', 1000);
      lsSet('last_env', 'All Environments');
    };
  }

  // 6. Highlight selected item in history list
  updateHistoryActiveItem(index);
}

/* ── Empty State Dashboard ───────────────────────────────────────────────── */
function renderEmptyDashboard(customMsg) {
  const topRecContainer = document.getElementById('top-rec-container');
  if (topRecContainer) {
    topRecContainer.innerHTML = `
      <div class="card" style="height:100%;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;padding:var(--s8);">
        <div style="width:52px;height:52px;border-radius:50%;background:var(--sage-100);color:var(--sage-700);display:flex;align-items:center;justify-content:center;margin-bottom:var(--s3)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:28px;height:28px"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
        </div>
        <h2 style="font-family:var(--ff-display);font-size:var(--t-xl);color:var(--sage-900);margin-bottom:var(--s2)">
          Start Your First Virtual Breeding Run
        </h2>
        <p style="font-size:var(--t-sm);color:var(--muted);max-width:480px;margin-bottom:var(--s4)">
          ${customMsg || "You haven't run any virtual breeding simulations yet. Upload your candidate parent inbred lines (.csv) to screen thousands of crosses in seconds."}
        </p>
        <a href="upload.html" class="btn btn--primary" style="display:inline-flex;align-items:center;gap:var(--s2)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:16px;height:16px"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          Launch Virtual Breeding →
        </a>
      </div>`;
  }

  setEl('metric-yield', '—');
  setEl('metric-score', '—');
  setEl('dc-yield', '—');
  setEl('dc-drought', '—');
  setEl('dc-disease', '—');
  setEl('dc-confidence', '—');

  const tableBody = document.getElementById('rec-table-body');
  if (tableBody) {
    tableBody.innerHTML = `
      <tr>
        <td colspan="9" style="text-align:center;color:var(--text-muted);padding:var(--s8)">
          No simulations run yet. <a href="upload.html" style="color:var(--brand);font-weight:600">Start breeding simulation →</a>
        </td>
      </tr>`;
  }

  const histContainer = document.getElementById('history-container');
  if (histContainer) {
    histContainer.innerHTML = `
      <div class="alert alert--info">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
        No recommendation history yet. When you run simulations on the Virtual Breeding page, your results will appear here.
      </div>`;
  }
}

/* ── History List & Interactive Run Switcher ─────────────────────────────── */
function renderHistoryList(history) {
  const container = document.getElementById('history-container');
  if (!container) return;

  if (!history.length) {
    container.innerHTML = `
      <div class="alert alert--info">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
        No recommendation history yet. Run a simulation on the Virtual Breeding page to start building your portfolio.
      </div>`;
    return;
  }

  container.innerHTML = `
    <div class="history-list">
      ${history.map((h, i) => `
        <div class="history-item ${i === window._activeRunIndex ? 'history-item--active' : ''}" id="hist-item-${i}" onclick="selectRun(${i})">
          <div class="history-item__rank">#${i + 1}</div>
          <div class="history-item__body">
            <div class="history-item__hybrid" style="display:flex;align-items:center;gap:var(--s2)">
              <span>${h.top_hybrid || 'Hybrid Cross'}</span>
              ${i === 0 ? '<span class="tag tag--success" style="font-size:10px;padding:1px 6px">Latest</span>' : ''}
            </div>
            <div class="history-item__meta">
              ${formatDate(h.timestamp)} &nbsp;•&nbsp;
              ${(h.total_pairs || 0).toLocaleString()} pairs evaluated
            </div>
          </div>
          <div style="text-align:right">
            <div class="history-item__score">${formatScore(h.top_score)}</div>
            <div style="font-size:10px;color:var(--muted)">Top Score</div>
          </div>
        </div>
      `).join('')}
    </div>`;
}

function selectRun(index) {
  renderActiveRun(index);
  const element = document.getElementById('top-rec-container');
  if (element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
}

function updateHistoryActiveItem(activeIndex) {
  const history = window._userHistory || [];
  for (let i = 0; i < history.length; i++) {
    const el = document.getElementById(`hist-item-${i}`);
    if (el) {
      if (i === activeIndex) {
        el.classList.add('history-item--active');
      } else {
        el.classList.remove('history-item--active');
      }
    }
  }
}

/* ── History Actions: Clear & Export ─────────────────────────────────────── */
function setupHistoryActions() {
  // Return to latest run button
  const btnReturn = document.getElementById('btn-return-latest');
  if (btnReturn) {
    btnReturn.addEventListener('click', () => {
      selectRun(0);
    });
  }

  // Clear history
  const clearBtn = document.getElementById('clear-history-btn');
  if (clearBtn) {
    clearBtn.addEventListener('click', async () => {
      if (!window._userHistory?.length) {
        if (typeof showToast === 'function') showToast('No history to clear.', 'warning');
        return;
      }
      if (confirm('Clear all your recommendation history? This will permanently delete your runs from MongoDB.')) {
        try {
          await apiFetch(`${API_BASE}/api/history`, { method: 'DELETE' });
          window._userHistory = [];
          renderUserStats([]);
          renderEmptyDashboard();
          if (typeof showToast === 'function') showToast('History cleared successfully.', 'success');
        } catch (err) {
          console.error("Failed to clear history:", err);
          if (typeof showToast === 'function') showToast('Failed to clear history.', 'error');
        }
      }
    });
  }

  // Export JSON
  const exportBtn = document.getElementById('export-history-btn');
  if (exportBtn) {
    exportBtn.addEventListener('click', () => {
      const history = window._userHistory || [];
      if (!history.length) {
        if (typeof showToast === 'function') showToast('No history to export.', 'warning');
        return;
      }
      const user = typeof getCurrentUser === 'function' ? getCurrentUser() : null;
      const userName = user?.name ? user.name.replace(/\s+/g, '_').toLowerCase() : 'user';
      downloadJSON(history, `breeding_history_${userName}_${new Date().toISOString().slice(0, 10)}.json`);
      if (typeof showToast === 'function') showToast('History exported successfully.', 'success');
    });
  }
}

/* ── DOM Helper ──────────────────────────────────────────────────────────── */
function setEl(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}
