/**
 * recommend.js — CrossWise Recommendation Engine UI Controller.
 *
 * This page acts as a pure View layer. The heavy lifting (API calls)
 * happens on the Upload page, which stores the results in session
 * storage and redirects here.
 */

'use strict';

let currentRecommendations = [];

document.addEventListener('DOMContentLoaded', () => {
  const exportBtn = document.getElementById('export-rec-btn');
  if (exportBtn) exportBtn.addEventListener('click', exportRecommendationsCSV);
  
  loadRecommendations();
});

function loadRecommendations() {
  const recs = lsGet('lastRecommendation');
  const env = lsGet('last_env', 'All Environments');
  const totalPairs = lsGet('last_total_pairs', 499500);
  const uniqueParents = lsGet('last_unique_parents', 1000);

  if (!recs || recs.length === 0) {
    const errDiv = document.getElementById('rec-error');
    if (errDiv) {
      errDiv.innerHTML = `
        <div class="alert alert--warning">
          <strong>No recommendations found.</strong><br>
          Please upload a Candidate SNP dataset on the <a href="upload.html">Upload page</a> to generate recommendations.
        </div>`;
      errDiv.classList.remove('hidden');
    }
    return;
  }

  currentRecommendations = recs;
  renderRecommendationResults(recs, env, totalPairs, uniqueParents);
}

/* ── Render results ──────────────────────────────────────────────────────── */
function renderRecommendationResults(recs, env, totalPairs, uniqueParents) {
  const resultsDiv    = document.getElementById('rec-results');
  const summaryBanner = document.getElementById('rec-summary-banner');
  const topHighlight  = document.getElementById('top-pair-highlight');
  const tableBody     = document.getElementById('rec-table-body');
  
  if (resultsDiv) resultsDiv.classList.remove('hidden');

  if (summaryBanner) {
    summaryBanner.innerHTML = `
      <div class="alert alert--info">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
        <div>
          <strong>Evaluation Complete</strong> — Screened
          <strong>${(totalPairs || 499500).toLocaleString()}</strong> virtual parent combinations from
          <strong>${(uniqueParents || 1000).toLocaleString()}</strong> inbred lines across
          <strong>300 SNP loci</strong>.
          Target Environment: <strong>${env}</strong>
        </div>
      </div>`;
  }

  // Top pair highlight card
  if (topHighlight && recs.length > 0) {
    const top = recs[0];
    topHighlight.innerHTML = `
      <div class="card card--glow">
        <div class="card__header">
          <div>
            <span class="tag">#1 Recommendation</span>
            <div class="card__title" style="font-size:var(--t-2xl);margin-top:4px">${top.hybrid_name}</div>
          </div>
          <div style="text-align:right">
            <div style="font-size:var(--t-xs);color:var(--muted);text-transform:uppercase">Composite Score</div>
            <div style="font-family:var(--ff-display);font-size:var(--t-3xl);font-weight:600;color:var(--sage-800)">${formatScore(top.recommendation_score)}</div>
          </div>
        </div>
        <div class="metric-cards">
          <div class="metric-card metric-card--yield">
            <div class="metric-card__label">Grain Yield</div>
            <div class="metric-card__value">${formatYield(top.predicted_yield)}</div>
            <div class="metric-card__sub">Predicted t/ha</div>
          </div>
          <div class="metric-card metric-card--drought">
            <div class="metric-card__label">Drought Tolerance</div>
            <div class="metric-card__value" style="font-size:var(--t-2xl)">${top.predicted_drought}</div>
            <div class="metric-card__sub">Water-deficit tolerance</div>
          </div>
          <div class="metric-card metric-card--disease">
            <div class="metric-card__label">Disease Resistance</div>
            <div class="metric-card__value" style="font-size:var(--t-2xl)">${top.predicted_disease}</div>
            <div class="metric-card__sub">Fungal &amp; blight</div>
          </div>
          <div class="metric-card metric-card--confidence">
            <div class="metric-card__label">Model Confidence</div>
            <div class="metric-card__value">${formatScore(top.confidence)}</div>
            <div class="metric-card__sub">Classifier certainty</div>
          </div>
        </div>
        <div style="margin-top:var(--s3)">
          <div class="confidence-meter">
            <div class="confidence-meter__label">Genomic Compatibility</div>
            <div class="confidence-meter__bar">
              <div class="confidence-meter__fill" style="width:${(top.genomic_compatibility * 100).toFixed(0)}%"></div>
            </div>
            <div class="confidence-meter__value">${(top.genomic_compatibility * 100).toFixed(1)}%</div>
          </div>
        </div>
      </div>`;
  }

  // Full results table
  if (tableBody) {
    tableBody.innerHTML = recs.map((r, i) => `
      <tr>
        <td style="font-weight:700;color:var(--sage-700)">#${r.rank}</td>
        <td style="font-weight:600">${r.hybrid_name}</td>
        <td>${formatYield(r.predicted_yield)}</td>
        <td><span class="resistance-badge ${r.predicted_drought === 'High' ? 'badge--high' : r.predicted_drought === 'Low' ? 'badge--low' : 'badge--medium'}">${r.predicted_drought}</span></td>
        <td><span class="resistance-badge ${r.predicted_disease === 'Resistant' ? 'badge--high' : r.predicted_disease === 'Susceptible' ? 'badge--low' : 'badge--medium'}">${r.predicted_disease}</span></td>
        <td>${r.predicted_quality}</td>
        <td>${r.predicted_maturity}</td>
        <td>
          <div class="compat-bar">
            <div class="compat-bar__fill" style="width:${(r.genomic_compatibility * 100).toFixed(0)}%"></div>
            <span class="compat-bar__label">${(r.genomic_compatibility * 100).toFixed(1)}%</span>
          </div>
        </td>
        <td style="font-weight:700;color:var(--sage-800)">${formatScore(r.recommendation_score)}</td>
        <td>${formatScore(r.confidence)}</td>
        <td>
          <button class="btn btn--ghost btn--sm" onclick="showWhyPanel(${i})" id="why-btn-${i}"
            style="font-size:var(--t-xs);padding:4px 8px">Why?</button>
        </td>
      </tr>
      <tr id="why-row-${i}" class="why-row hidden">
        <td colspan="11">
          <div class="xai-accordion" id="why-content-${i}"></div>
        </td>
      </tr>
    `).join('');
  }
}

let shapFetchPromise = null;

/* ── "Why?" SHAP panel per row ───────────────────────────────────────────── */
async function showWhyPanel(idx) {
  const row = document.getElementById(`why-row-${idx}`);
  const content = document.getElementById(`why-content-${idx}`);
  if (!row || !content) return;

  // Toggle
  if (!row.classList.contains('hidden')) {
    row.classList.add('hidden');
    return;
  }
  row.classList.remove('hidden');

  const rec = currentRecommendations[idx];
  let shapData = lsGet('shapFeatures', null);

  if (!shapData || !shapData.length) {
    content.innerHTML = `
      <div style="padding:var(--s4);display:flex;align-items:center;gap:var(--s2);color:var(--text-muted);font-size:var(--t-sm)">
        <span class="spinner" style="width:14px;height:14px;border-width:2px"></span>
        Computing SHAP feature importance…
      </div>`;

    try {
      if (!shapFetchPromise) {
        shapFetchPromise = fetch(`${API_BASE}/api/shap`)
          .then(res => res.json())
          .then(json => {
            if (json.features && json.features.length) {
              lsSet('shapFeatures', json.features);
              return json.features;
            }
            return null;
          })
          .catch(err => {
            console.warn('SHAP fetch failed:', err);
            return null;
          })
          .finally(() => {
            shapFetchPromise = null;
          });
      }
      shapData = await shapFetchPromise;
    } catch (_) {}
  }

  if (shapData && shapData.length) {
    const top5 = shapData.slice(0, 5);
    content.innerHTML = `
      <div style="padding:var(--s4)">
        <div style="font-size:var(--t-sm);font-weight:700;margin-bottom:var(--s3)">Top Drivers for ${rec.hybrid_name}</div>
        <div style="display:flex;flex-direction:column;gap:var(--s2)">
          ${top5.map(f => `
            <div>
              <div style="display:flex;justify-content:space-between;font-size:var(--t-xs);margin-bottom:3px">
                <span style="font-weight:600">${f.name}</span>
                <span style="color:var(--sage-700);font-weight:700">Impact: ${(f.mean_shap || f.shap || 0).toFixed(3)}</span>
              </div>
              <div style="height:6px;background:var(--sage-100);border-radius:var(--r-full);overflow:hidden">
                <div style="height:100%;width:${Math.min(100, ((f.mean_shap || f.shap || 0) / (top5[0].mean_shap || top5[0].shap || 1)) * 100).toFixed(1)}%;background:var(--sage-600);border-radius:var(--r-full)"></div>
              </div>
            </div>`).join('')}
        </div>
        <div style="margin-top:var(--s3);font-size:var(--t-xs);color:var(--text-muted)">
          <a href="explainability.html">View full SHAP analysis →</a>
        </div>
      </div>`;
  } else {
    content.innerHTML = `
      <div style="padding:var(--s4);font-size:var(--t-sm);color:var(--text-muted)">
        Feature importance not ready. <a href="explainability.html">View full Explainability page →</a>
      </div>`;
  }
}

/* ── CSV Export ──────────────────────────────────────────────────────────── */
function exportRecommendationsCSV() {
  if (!currentRecommendations.length) {
    if (typeof showToast === 'function') showToast('Run recommendations first.', 'warning');
    return;
  }
  const rows = [
    ['Rank','Hybrid Combination','Yield (t/ha)','Drought','Disease','Quality','Maturity','Genomic Compat.','Score','Confidence'],
    ...currentRecommendations.map(r => [
      r.rank,
      `"${r.hybrid_name}"`,
      r.predicted_yield,
      r.predicted_drought,
      r.predicted_disease,
      r.predicted_quality,
      r.predicted_maturity,
      (r.genomic_compatibility * 100).toFixed(1) + '%',
      (r.recommendation_score  * 100).toFixed(2) + '%',
      (r.confidence            * 100).toFixed(2) + '%',
    ]),
  ];
  const csv  = rows.map(e => e.join(',')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  if (typeof triggerDownload === 'function') {
    triggerDownload(blob, `crosswire_recommendations_${new Date().toISOString().slice(0,10)}.csv`);
  }
}
