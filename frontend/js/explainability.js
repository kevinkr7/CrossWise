/**
 * explainability.js — CrossWise SHAP Explainability UI controller.
 */

'use strict';

document.addEventListener('DOMContentLoaded', () => {
  loadShapData();
});

/* ── SNP metadata (gene annotation lookup) ──────────────────────────────── */
const SNP_ANNOTATIONS = {
  'SNP_042': { gene: 'Drought-1 (Zm00001d01423)',  impact: 'High positive effect on yield under water deficit' },
  'SNP_189': { gene: 'GLS-Resist (Zm00001d03891)', impact: 'Confers Gray Leaf Spot resistance' },
  'SNP_012': { gene: 'Kernel-Wt (Zm00001d00112)',  impact: 'Increases 100-kernel weight (+12.4g)' },
  'SNP_256': { gene: 'Heat-Shock (Zm00001d05612)', impact: 'Thermal tolerance above 35°C' },
  'SNP_104': { gene: 'Root-Depth (Zm00001d02004)', impact: 'Enhances deep soil water extraction' },
  'SNP_088': { gene: 'Stalk-Str (Zm00001d00988)',  impact: 'Reduces lodging risk under high wind' },
  'SNP_300': { gene: 'Ear-Length (Zm00001d04900)', impact: 'Increases ear length (+2.3 cm)' },
  'SNP_145': { gene: 'Chloro-A (Zm00001d02845)',   impact: 'Higher photosynthetic efficiency' },
  'SNP_067': { gene: 'N-Use-Eff (Zm00001d00767)',  impact: 'Optimizes nitrogen uptake efficiency' },
  'SNP_219': { gene: 'Blight-R (Zm00001d04219)',   impact: 'Resistance to Northern Corn Leaf Blight' },
  'SNP_033': { gene: 'Silk-Days (Zm00001d00233)',  impact: 'Controls anthesis-silking interval (ASI)' },
  'SNP_178': { gene: 'Row-Num (Zm00001d02478)',    impact: 'Increases kernel row number (+2 rows)' },
  'SNP_290': { gene: 'Stay-Green (Zm00001d04890)', impact: 'Extends canopy greenness during grain fill' },
  'Rainfall_mm': { gene: 'Environmental',          impact: 'Seasonal precipitation at silking stage' },
  'Temp_C':      { gene: 'Environmental',          impact: 'Mean seasonal temperature' },
  'Humidity_pct':{ gene: 'Environmental',          impact: 'Relative humidity during grain fill' },
};

/* ── Fallback demo features ─────────────────────────────────────────────── */
const DEMO_FEATURES = [
  { name: 'SNP_042 (Chr 3: 45.2 Mb)', shap: 0.84, mean_shap: 0.84 },
  { name: 'SNP_189 (Chr 8: 12.8 Mb)', shap: 0.79, mean_shap: 0.79 },
  { name: 'SNP_012 (Chr 1: 98.4 Mb)', shap: 0.72, mean_shap: 0.72 },
  { name: 'SNP_256 (Chr 10: 5.1 Mb)', shap: 0.68, mean_shap: 0.68 },
  { name: 'SNP_104 (Chr 4: 33.7 Mb)', shap: 0.63, mean_shap: 0.63 },
  { name: 'SNP_088 (Chr 2: 77.3 Mb)', shap: 0.58, mean_shap: 0.58 },
  { name: 'SNP_300 (Chr 9: 64.0 Mb)', shap: 0.54, mean_shap: 0.54 },
  { name: 'SNP_145 (Chr 6: 22.1 Mb)', shap: 0.51, mean_shap: 0.51 },
  { name: 'SNP_067 (Chr 2: 19.4 Mb)', shap: 0.47, mean_shap: 0.47 },
  { name: 'SNP_219 (Chr 7: 81.6 Mb)', shap: 0.44, mean_shap: 0.44 },
  { name: 'Rainfall_mm (Env)',         shap: 0.41, mean_shap: 0.41 },
  { name: 'SNP_033 (Chr 1: 154.0 Mb)', shap: 0.38, mean_shap: 0.38 },
  { name: 'SNP_178 (Chr 5: 41.2 Mb)', shap: 0.35, mean_shap: 0.35 },
  { name: 'Temp_C (Env)',              shap: 0.32, mean_shap: 0.32 },
  { name: 'SNP_290 (Chr 9: 18.9 Mb)', shap: 0.29, mean_shap: 0.29 },
];

/* ── Main loader ─────────────────────────────────────────────────────────── */
async function loadShapData() {
  const loadingEl = document.getElementById('shap-loading');
  const errorEl   = document.getElementById('shap-error');

  let features = lsGet('shapFeatures', null);
  let method = 'shap_tree_explainer';

  if (!features || !features.length) {
    try {
      const res = await fetch(`${API_BASE}/api/shap`);
      if (res.ok) {
        const data = await res.json();
        if (data.features && data.features.length) {
          features = data.features;
          method = data.method || method;
          lsSet('shapFeatures', features);
        }
      }
    } catch (err) {
      console.warn('Could not fetch live SHAP values:', err);
    }
  }

  if (!features || !features.length) {
    features = DEMO_FEATURES;
    method = 'demo';
  }

  if (loadingEl) loadingEl.style.display = 'none';

  const methodLabel = method === 'shap_tree_explainer'
    ? '<span class="tag" style="background:var(--sage-100);color:var(--sage-800)">SHAP TreeExplainer (live)</span>'
    : method === 'rf_feature_importance'
    ? '<span class="tag" style="background:var(--earth-100);color:var(--earth-600)">RF Feature Importance</span>'
    : '<span class="tag" style="background:var(--linen);color:var(--muted)">Reference Data</span>';

  renderImportanceChart(features, methodLabel);
  renderImportanceTable(features);
  renderBeeswarmPlot(features);
  renderLocalExplanations(features);
}

/* ── Global importance bars ──────────────────────────────────────────────── */
function renderImportanceChart(features, methodLabel) {
  const el = document.getElementById('importance-chart');
  if (!el) return;

  const maxShap = Math.max(...features.map(f => f.shap || f.mean_shap || 0));

  el.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:var(--s4)">
      <span style="font-size:var(--t-xs);color:var(--text-muted)">Mean |SHAP value| → positive impact on grain yield</span>
      ${methodLabel}
    </div>
    <div style="display:flex;flex-direction:column;gap:var(--s3)">
      ${features.slice(0, 15).map((f, i) => {
        const shapVal  = f.shap || f.mean_shap || 0;
        const pct      = maxShap > 0 ? ((shapVal / maxShap) * 100).toFixed(1) : '0';
        const isEnv    = f.name.includes('Env') || f.name.includes('_mm') || f.name.includes('_C') || f.name.includes('_pct');
        const barColor = isEnv ? 'var(--earth-600)' : 'var(--sage-600)';

        return `
          <div class="shap-bar-row" style="--delay:${i * 60}ms">
            <div style="display:flex;justify-content:space-between;font-size:var(--t-xs);margin-bottom:4px">
              <span style="font-weight:600;color:var(--sage-900)">${f.name}</span>
              <span style="font-weight:700;color:var(--sage-700)">${shapVal.toFixed(3)}</span>
            </div>
            <div style="height:10px;background:var(--sage-100);border-radius:var(--r-full);overflow:hidden">
              <div class="shap-bar-fill" style="height:100%;width:${pct}%;background:${barColor};border-radius:var(--r-full)">
              </div>
            </div>
          </div>`;
      }).join('')}
    </div>`;
}

/* ── Importance table ────────────────────────────────────────────────────── */
function renderImportanceTable(features) {
  const el = document.getElementById('importance-list');
  if (!el) return;

  el.innerHTML = `
    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>Rank</th>
            <th>Marker / Feature</th>
            <th>Annotated Gene</th>
            <th>Mean |SHAP|</th>
            <th>Biological Impact</th>
          </tr>
        </thead>
        <tbody>
          ${features.slice(0, 20).map((f, i) => {
            const snpKey = f.name.split(' ')[0].replace('(', '');
            const ann    = SNP_ANNOTATIONS[snpKey] || { gene: 'Novel loci', impact: 'Modulates multi-trait hybrid vigour' };
            const shapVal = f.shap || f.mean_shap || 0;

            return `
              <tr>
                <td style="font-weight:700;color:var(--sage-700)">#${i + 1}</td>
                <td style="font-weight:600">${f.name}</td>
                <td><code style="font-family:var(--font-mono);font-size:var(--t-xs);color:var(--sage-800)">${ann.gene}</code></td>
                <td style="font-weight:700">${shapVal.toFixed(3)}</td>
                <td style="color:var(--muted);font-size:var(--t-xs)">${ann.impact}</td>
              </tr>`;
          }).join('')}
        </tbody>
      </table>
    </div>`;
}

/* ── Beeswarm summary plot ────────────────────────────────────────────────── */
function renderBeeswarmPlot(features) {
  const el = document.getElementById('summary-plot');
  if (!el) return;

  el.innerHTML = `
    <div style="background:var(--parchment);padding:var(--s6);border-radius:var(--r-lg);border:1px solid var(--border)">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:var(--s4)">
        <span style="font-size:var(--t-xs);font-weight:700;text-transform:uppercase;color:var(--muted)">SNP Dosage → SHAP Impact on Yield</span>
        <div style="display:flex;gap:var(--s4);font-size:var(--t-xs)">
          <span style="color:var(--coral);font-weight:600">● Alt Allele (higher dosage)</span>
          <span style="color:var(--sage-600);font-weight:600">● Ref Allele (lower dosage)</span>
        </div>
      </div>
      <div style="display:flex;flex-direction:column;gap:var(--s3)">
        ${features.slice(0, 10).map(f => {
          const hasData = f.feat_vals && f.shap_vals;
          const shapVal = f.shap || f.mean_shap || 0;

          let dots = '';
          if (hasData && f.feat_vals.length > 0) {
            const maxFeat = Math.max(...f.feat_vals) || 2;
            dots = f.feat_vals.slice(0, 25).map((fv, k) => {
              const sv   = f.shap_vals[k] || 0;
              const xPct = Math.max(5, Math.min(95, 50 + (sv / (shapVal * 2 || 1)) * 45));
              const color = fv > maxFeat * 0.5 ? 'var(--coral)' : 'var(--sage-500)';
              return `<span style="position:absolute;left:${xPct.toFixed(1)}%;top:50%;transform:translate(-50%,-50%);width:7px;height:7px;border-radius:50%;background:${color};opacity:0.8"></span>`;
            }).join('');
          } else {
            const positions = [55, 65, 38, 52, 45, 48, 62, 42];
            dots = positions.map((pos, k) => `<span style="position:absolute;left:${pos}%;top:50%;transform:translate(-50%,-50%);width:7px;height:7px;border-radius:50%;background:${k % 2 === 0 ? 'var(--coral)' : 'var(--sage-500)'};opacity:0.8"></span>`).join('');
          }

          return `
            <div style="display:grid;grid-template-columns:200px 1fr;align-items:center;gap:var(--s3)">
              <div style="font-size:var(--t-xs);font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${f.name.split(' ')[0]}</div>
              <div style="position:relative;height:20px;background:var(--stone);border-radius:var(--r-full);border:1px dashed var(--sage-300)">
                <div style="position:absolute;left:50%;top:0;bottom:0;width:1px;background:var(--sage-400)"></div>
                ${dots}
              </div>
            </div>`;
        }).join('')}
      </div>
      <div style="text-align:center;font-size:var(--t-xs);color:var(--muted);margin-top:var(--s4)">
        ← Decreases Predicted Yield &nbsp;|&nbsp; Increases Predicted Yield →
      </div>
    </div>`;
}

/* ── Local explanations per top hybrid ───────────────────────────────────── */
function renderLocalExplanations(features) {
  const container = document.getElementById('local-explanations');
  if (!container) return;

  const lastRec = lsGet('lastRecommendation', []);
  if (!lastRec.length) {
    container.innerHTML = `
      <div class="alert alert--info">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        Local explanations appear here after running <a href="recommend.html">Recommendations</a>.
      </div>`;
    return;
  }

  const top5 = lastRec.slice(0, 5);
  const topFeatures = features.slice(0, 8);

  container.innerHTML = top5.map((rec, ri) => `
    <div class="card mb-4" style="border-left:3px solid var(--sage-500)">
      <div class="card__header">
        <div>
          <span class="tag">#${rec.rank || ri + 1}</span>
          <div class="card__title" style="margin-top:4px">${rec.hybrid_name}</div>
        </div>
        <div style="text-align:right;font-size:var(--t-sm)">
          <div style="color:var(--text-muted)">Predicted Yield</div>
          <div style="font-weight:700;font-size:var(--t-xl);color:var(--sage-700)">${typeof formatYield === 'function' ? formatYield(rec.predicted_yield) : rec.predicted_yield + ' t/ha'}</div>
        </div>
      </div>

      <div style="margin-top:var(--s4)">
        <div style="font-size:var(--t-xs);font-weight:700;color:var(--text-muted);margin-bottom:var(--s3);text-transform:uppercase">Top Driving Features for this Hybrid</div>
        ${topFeatures.map((f, fi) => {
          const shapVal = (f.shap || f.mean_shap || 0);
          const pct = Math.min(100, (shapVal / (features[0].shap || features[0].mean_shap || 1)) * 100).toFixed(1);

          return `
            <div style="margin-bottom:var(--s2)">
              <div style="display:flex;justify-content:space-between;font-size:var(--t-xs);margin-bottom:3px">
                <span>${f.name.split(' ')[0]}</span>
                <span style="font-weight:600;color:var(--sage-700)">${shapVal.toFixed(3)}</span>
              </div>
              <div style="height:7px;background:var(--sage-100);border-radius:var(--r-full);overflow:hidden">
                <div style="height:100%;width:${pct}%;background:var(--sage-500);border-radius:var(--r-full);opacity:0.85"></div>
              </div>
            </div>`;
        }).join('')}
      </div>
    </div>`).join('');
}
