/**
 * analytics.js — Renders analytics metrics and distribution charts.
 */

document.addEventListener('DOMContentLoaded', () => {
  loadAnalytics();
});


async function loadAnalytics() {
  const modelMetrics = document.getElementById('model-metrics');
  const splitChart = document.getElementById('split-chart');
  const datasetStats = document.getElementById('dataset-stats');
  const traitDist = document.getElementById('trait-distributions');
  
  let ds = null;
  let ms = null;
  
  try {
    const dsRes = await fetch(`${API_BASE}/api/dataset/info`);
    if (dsRes.ok) ds = await dsRes.json();
  } catch(e) {}
  
  try {
    const msRes = await fetch(`${API_BASE}/api/model/status`);
    if (msRes.ok) ms = await msRes.json();
  } catch(e) {}

  if (modelMetrics) {
    if (ms && ms.metrics) {
      modelMetrics.innerHTML = `
        <div class="metric-cards">
          <div class="metric-card metric-card--yield">
            <div class="metric-card__label">Yield Regressor R²</div>
            <div class="metric-card__value">${ms.metrics.yield_r2 || '—'}</div>
            <div class="metric-card__sub">RMSE: ${ms.metrics.yield_rmse || '—'} t/ha</div>
          </div>
          <div class="metric-card metric-card--drought">
            <div class="metric-card__label">Drought Classifier</div>
            <div class="metric-card__value">${ms.metrics.drought_tolerance_accuracy ? (ms.metrics.drought_tolerance_accuracy * 100).toFixed(1) + '%' : '—'}</div>
            <div class="metric-card__sub">Macro F1: ${ms.metrics.drought_f1 ? ms.metrics.drought_f1.toFixed(3) : '—'}</div>
          </div>
          <div class="metric-card metric-card--disease">
            <div class="metric-card__label">Disease Classifier</div>
            <div class="metric-card__value">${ms.metrics.disease_resistance_accuracy ? (ms.metrics.disease_resistance_accuracy * 100).toFixed(1) + '%' : '—'}</div>
            <div class="metric-card__sub">Macro F1: ${ms.metrics.disease_f1 ? ms.metrics.disease_f1.toFixed(3) : '—'}</div>
          </div>
          <div class="metric-card metric-card--confidence">
            <div class="metric-card__label">OOB Score</div>
            <div class="metric-card__value">${ms.metrics.yield_oob || '—'}</div>
            <div class="metric-card__sub">Out-of-bag validation</div>
          </div>
        </div>
      `;
    } else {
      modelMetrics.innerHTML = '<div class="alert alert--info">Model metrics unavailable. Train the model first.</div>';
    }
  }

  if (splitChart) {
    const total = ds ? (ds.total_rows || '—') : '—';
    const train = ms?.metrics?.n_train || '—';
    splitChart.innerHTML = `
      <div class="card">
        <div class="card__header">
          <div class="card__title">Dataset Partition Split</div>
          <span class="tag">${total.toLocaleString()} Total Records</span>
        </div>
        <div style="display:flex;height:24px;border-radius:var(--r-full);overflow:hidden;margin-bottom:var(--s3)">
          <div style="width:70%;background:var(--sage-600);display:flex;align-items:center;justify-content:center;color:white;font-size:var(--t-xs);font-weight:600">Train (70% - ${train.toLocaleString()})</div>
          <div style="width:15%;background:var(--earth-600);display:flex;align-items:center;justify-content:center;color:white;font-size:var(--t-xs);font-weight:600">Val (15%)</div>
          <div style="width:15%;background:var(--coral);display:flex;align-items:center;justify-content:center;color:white;font-size:var(--t-xs);font-weight:600">Test (15%)</div>
        </div>
        <div style="font-size:var(--t-xs);color:var(--muted)">
          Grouped by parent line ID to prevent data leakage across environments.
        </div>
      </div>
    `;
  }

  if (datasetStats) {
    if (ds) {
      datasetStats.innerHTML = `
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:var(--s4)">
          <div>
            <div style="font-size:var(--t-xs);color:var(--muted)">Total Cultivars</div>
            <div style="font-size:var(--t-xl);font-weight:700;color:var(--sage-900)">${ds.unique_lines ? ds.unique_lines.toLocaleString() : '—'} lines</div>
          </div>
          <div>
            <div style="font-size:var(--t-xs);color:var(--muted)">Genotype Markers</div>
            <div style="font-size:var(--t-xl);font-weight:700;color:var(--sage-900)">${ds.n_snp_markers || '—'} SNPs</div>
          </div>
          <div>
            <div style="font-size:var(--t-xs);color:var(--muted)">Environments</div>
            <div style="font-size:var(--t-xl);font-weight:700;color:var(--sage-900)">${ds.n_environments || '—'} Sites</div>
          </div>
          <div>
            <div style="font-size:var(--t-xs);color:var(--muted)">Mean Yield</div>
            <div style="font-size:var(--t-xl);font-weight:700;color:var(--sage-700)">${ds.yield_mean || '—'} t/ha</div>
          </div>
        </div>
      `;
    } else {
      datasetStats.innerHTML = '<div class="alert alert--info">Dataset statistics unavailable.</div>';
    }
  }

  if (traitDist) {
    traitDist.innerHTML = `
      <div class="card mt-4">
        <div class="card__title mb-4">Trait Distribution Overview</div>
        <div style="font-size:var(--t-sm);color:var(--muted)">Live trait distribution data is currently fetched directly from the prediction pipeline during active runs.</div>
      </div>
    `;
  }
}
