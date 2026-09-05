/**
 * upload.js — CrossWire triple-zone CSV upload + model training controller.
 *
 * Zones:
 *   Zone 1 (snp)   — SNP Genotype CSV  [required]
 *   Zone 2 (env)   — Environmental CSV [required]
 *   Zone 3 (pheno) — Phenotypic CSV    [optional]
 *
 * Flow:
 *   1. User drops / picks CSVs → client-side header validation.
 *   2. "Upload Datasets" button → POST /api/upload (FormData).
 *   3. Validation report rendered from server response.
 *   4. "Train Model" button → POST /api/train → animated stepper → metrics.
 *   5. On page load: GET /api/model/status → show existing metrics if trained.
 */

'use strict';

/* ── State ──────────────────────────────────────────────────────────────── */
const _files = { snp: null, env: null, pheno: null };
let   _uploadedSuccessfully = false;

/* ── Zone definitions ────────────────────────────────────────────────────── */
const ZONES = [
  {
    key:       'snp',
    zoneId:    'zone-snp',
    inputId:   'snp-file-input',
    statusId:  'snp-file-status',
    required:  true,
    validate:  validateSnpHeaders,
    label:     'SNP Genotype',
  },
  {
    key:       'env',
    zoneId:    'zone-env',
    inputId:   'env-file-input',
    statusId:  'env-file-status',
    required:  true,
    validate:  validateEnvHeaders,
    label:     'Environmental',
  },
  {
    key:       'pheno',
    zoneId:    'zone-pheno',
    inputId:   'pheno-file-input',
    statusId:  'pheno-file-status',
    required:  false,
    validate:  validatePhenoHeaders,
    label:     'Phenotypic',
  },
];

/* ── Init ────────────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  ZONES.forEach(zone => initZone(zone));

  const submitBtn = document.getElementById('upload-submit-btn');
  const trainBtn  = document.getElementById('train-btn');

  if (submitBtn) submitBtn.addEventListener('click', handleUpload);
  if (trainBtn)  trainBtn.addEventListener('click',  handleTrain);

  checkModelStatus();
});

/* ── Zone initialisation ─────────────────────────────────────────────────── */
function initZone(zone) {
  const el      = document.getElementById(zone.zoneId);
  const inputEl = document.getElementById(zone.inputId);
  if (!el || !inputEl) return;

  el.addEventListener('click', () => inputEl.click());

  el.addEventListener('dragover', e => {
    e.preventDefault();
    el.classList.add('upload-zone--dragging');
  });
  el.addEventListener('dragleave', () => el.classList.remove('upload-zone--dragging'));
  el.addEventListener('drop', e => {
    e.preventDefault();
    el.classList.remove('upload-zone--dragging');
    const file = e.dataTransfer.files[0];
    if (file) handleFile(zone, file);
  });

  inputEl.addEventListener('change', () => {
    if (inputEl.files.length) handleFile(zone, inputEl.files[0]);
  });
}

/* ── File handling ───────────────────────────────────────────────────────── */
async function handleFile(zone, file) {
  if (!file.name.toLowerCase().endsWith('.csv')) {
    showZoneError(zone, 'Please upload a .csv file.');
    return;
  }

  showZoneLoading(zone, file.name);
  const headers = await readCsvHeaders(file);
  const { valid, message, stats } = zone.validate(headers, file);

  if (valid) {
    _files[zone.key] = file;
    showZoneSuccess(zone, file, stats);
  } else {
    _files[zone.key] = null;
    showZoneError(zone, message);
  }

  updateSubmitButton();
}

/* ── Client-side CSV header readers ─────────────────────────────────────── */
function readCsvHeaders(file) {
  return new Promise(resolve => {
    const reader = new FileReader();
    reader.onload = e => {
      const firstLine = e.target.result.split('\n')[0] || '';
      resolve(firstLine.split(',').map(h => h.trim().replace(/^"|"$/g, '')));
    };
    reader.readAsText(file.slice(0, 4096));
  });
}

function readCsvRowCount(file) {
  return new Promise(resolve => {
    const reader = new FileReader();
    reader.onload = e => {
      const lines = e.target.result.split('\n').filter(l => l.trim());
      resolve(Math.max(0, lines.length - 1)); // exclude header
    };
    reader.readAsText(file.slice(0, 512 * 1024)); // first 512 KB
  });
}

/* ── Header validators ────────────────────────────────────────────────────── */
function validateSnpHeaders(headers, file) {
  const snpCols = headers.filter(h => /^SNP_/i.test(h));
  const hasId   = headers.some(h => /^(line|parent_?id|id|genotype|name)$/i.test(h));

  if (!hasId) {
    return { valid: false, message: 'Missing ID column (Line / Parent_ID / ID).' };
  }
  if (snpCols.length < 5) {
    // Could still be the bundled all-in-one CSV — allow if it has SNP cols
    return {
      valid:   false,
      message: `Found ${snpCols.length} SNP columns (SNP_*). Need at least 5.`,
    };
  }

  // Check for bundled dataset (has env + trait cols too)
  const hasEnv    = headers.some(h => /rainfall|temp|humidity/i.test(h));
  const hasTraits = headers.some(h => /yield|disease|drought/i.test(h));
  const note      = hasEnv && hasTraits
    ? ' (bundled format detected — includes env + trait columns)'
    : '';

  return {
    valid: true,
    stats: `${snpCols.length} SNP markers${note}`,
    message: 'OK',
  };
}

function validateEnvHeaders(headers) {
  const envKeys = ['temperature', 'temp', 'rainfall', 'humidity', 'soil'];
  const found = headers.filter(h =>
    envKeys.some(k => h.toLowerCase().includes(k))
  );
  if (found.length === 0) {
    // Warn but don't block — env data might be in the SNP CSV
    return {
      valid: true,
      stats: 'No standard env columns detected — will use bundled env data',
      message: 'OK',
    };
  }
  return {
    valid: true,
    stats: `${found.length} environmental features: ${found.slice(0,3).join(', ')}${found.length > 3 ? '…' : ''}`,
    message: 'OK',
  };
}

function validatePhenoHeaders(headers) {
  const traitKeys = ['yield', 'disease', 'drought', 'resistance', 'tolerance'];
  const found = headers.filter(h =>
    traitKeys.some(k => h.toLowerCase().includes(k))
  );
  return {
    valid: true,
    stats: found.length > 0
      ? `Trait columns found: ${found.join(', ')}`
      : 'No standard trait columns detected',
    message: 'OK',
  };
}

/* ── Zone UI states ──────────────────────────────────────────────────────── */
function showZoneLoading(zone, filename) {
  const el = document.getElementById(zone.zoneId);
  if (el) el.classList.add('upload-zone--loading');
  setZoneStatus(zone.statusId, 'loading', `Reading ${filename}…`);
}

function showZoneSuccess(zone, file, stats) {
  const el = document.getElementById(zone.zoneId);
  if (el) {
    el.classList.remove('upload-zone--loading', 'upload-zone--error');
    el.classList.add('upload-zone--success');
  }
  const card = document.getElementById(`zone-${zone.key}-card`);
  if (card) card.classList.add('upload-card--done');

  setZoneStatus(zone.statusId, 'success', `
    <strong>${file.name}</strong> — ${(file.size / 1024).toFixed(1)} KB
    ${stats ? `<br><span style="color:var(--text-muted);font-size:var(--t-xs)">${stats}</span>` : ''}
  `);
}

function showZoneError(zone, message) {
  const el = document.getElementById(zone.zoneId);
  if (el) {
    el.classList.remove('upload-zone--loading', 'upload-zone--success');
    el.classList.add('upload-zone--error');
  }
  setZoneStatus(zone.statusId, 'error', message);
}

function setZoneStatus(statusId, type, html) {
  const el = document.getElementById(statusId);
  if (!el) return;
  el.classList.remove('hidden');

  const iconMap = {
    loading: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin" style="width:14px;height:14px"><path d="M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0"/></svg>`,
    success: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;color:var(--sage-600)"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
    error:   `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;color:var(--coral)"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
  };

  const colorMap = {
    loading: 'var(--text-muted)',
    success: 'var(--sage-600)',
    error:   'var(--coral)',
  };

  el.style.color = colorMap[type] || 'inherit';
  el.innerHTML   = `<span style="display:flex;align-items:flex-start;gap:6px">${iconMap[type] || ''}${html}</span>`;
}

/* ── Submit button state ─────────────────────────────────────────────────── */
function updateSubmitButton() {
  const btn  = document.getElementById('upload-submit-btn');
  const hint = document.getElementById('upload-hint-text');
  if (!btn) return;

  const snpReady = !!_files.snp;
  const envReady = !!_files.env;
  const ready    = snpReady; // env optional if SNP file is bundled format

  btn.disabled = !ready;

  if (ready) {
    btn.innerHTML = `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:16px;height:16px">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
        <polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
      </svg>
      Upload ${[snpReady?'SNP':null, envReady?'Env':null, _files.pheno?'Phenotypic':null].filter(Boolean).join(' + ')} Dataset${_files.pheno ? 's' : ''}
    `;
    if (hint) hint.textContent = _files.env ? 'All required files ready.' : 'SNP CSV uploaded (env data embedded or using defaults).';
  } else {
    if (hint) hint.textContent = 'Upload SNP Genotype CSV (required) to enable.';
  }
}

/* ── Upload to server ────────────────────────────────────────────────────── */
async function handleUpload() {
  const btn = document.getElementById('upload-submit-btn');
  const statusEl = document.getElementById('upload-global-status');

  btn.disabled = true;
  btn.innerHTML = `<div class="spinner" style="width:14px;height:14px;border-width:2px;margin-right:6px"></div> Uploading…`;

  const form = new FormData();
  if (_files.snp)   form.append('snp_file',   _files.snp);
  if (_files.env)   form.append('env_file',   _files.env);
  if (_files.pheno) form.append('pheno_file', _files.pheno);

  try {
    const res  = await fetch(`${API_BASE}/api/upload`, { method: 'POST', body: form });
    const data = await res.json();

    if (!res.ok) throw new Error(data.error || 'Upload failed');

    _uploadedSuccessfully = true;
    renderValidationReport(data);

    // Show train section
    const trainSec = document.getElementById('train-section');
    if (trainSec) trainSec.classList.remove('hidden');

    if (statusEl) {
      statusEl.innerHTML = `
        <div class="alert alert--success mb-3">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:18px;height:18px"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
          <div><strong>Upload successful!</strong> ${data.rows?.toLocaleString() || '–'} rows · ${data.snp_markers || 0} SNP markers · ${data.unique_lines || 0} unique lines</div>
        </div>`;
    }

    if (typeof showToast === 'function') showToast('Dataset uploaded successfully!', 'success');

  } catch (err) {
    if (statusEl) {
      statusEl.innerHTML = `<div class="alert alert--error mb-3"><strong>Upload failed:</strong> ${err.message}</div>`;
    }
    if (typeof showToast === 'function') showToast(err.message, 'error');
  } finally {
    btn.disabled = false;
    updateSubmitButton();
  }
}

/* ── Validation report ────────────────────────────────────────────────────── */
function renderValidationReport(data) {
  const el = document.getElementById('validation-report');
  if (!el) return;
  el.classList.remove('hidden');

  el.innerHTML = `
    <div class="card">
      <div class="card__title mb-3">Dataset Health Report</div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:var(--s4)">
        <div class="stat-counter">
          <div class="stat-counter__value" data-target="${data.rows || 0}">${(data.rows || 0).toLocaleString()}</div>
          <div class="stat-counter__label">Total Rows</div>
        </div>
        <div class="stat-counter">
          <div class="stat-counter__value" data-target="${data.unique_lines || 0}">${(data.unique_lines || 0).toLocaleString()}</div>
          <div class="stat-counter__label">Unique Lines</div>
        </div>
        <div class="stat-counter">
          <div class="stat-counter__value" data-target="${data.snp_markers || 0}">${(data.snp_markers || 0).toLocaleString()}</div>
          <div class="stat-counter__label">SNP Markers</div>
        </div>
        <div class="stat-counter">
          <div class="stat-counter__value">${data.has_traits ? '✓ Yes' : '✗ No'}</div>
          <div class="stat-counter__label">Trait Targets</div>
        </div>
        <div class="stat-counter">
          <div class="stat-counter__value">${(data.env_features || []).length}</div>
          <div class="stat-counter__label">Env Features</div>
        </div>
      </div>
    </div>`;
}

/* ── Model training ──────────────────────────────────────────────────────── */
async function handleTrain() {
  const trainBtn    = document.getElementById('train-btn');
  const trainResult = document.getElementById('train-result');
  const statusTag   = document.getElementById('train-status-tag');
  const stepper     = document.getElementById('pipeline-stepper');
  const steps       = stepper ? stepper.querySelectorAll('.step-item') : [];

  if (trainBtn) {
    trainBtn.disabled = true;
    trainBtn.innerHTML = `<div class="spinner" style="width:14px;height:14px;border-width:2px;margin-right:6px"></div> Training Random Forest…`;
  }
  if (statusTag) statusTag.textContent = 'Training…';

  // Animate pipeline steps
  const STEP_LABELS = [
    'Loading dataset…',
    'Encoding SNP alleles…',
    'Imputing missing genotypes…',
    'Splitting 70/15/15…',
    'Training Random Forest (200 trees)…',
    'Evaluating on test set…',
    'Saving model artefacts…',
  ];

  async function animateSteps() {
    for (let i = 0; i < steps.length; i++) {
      steps.forEach(s => s.classList.remove('active', 'done'));
      for (let j = 0; j < i; j++) steps[j].classList.add('done');
      steps[i].classList.add('active');
      if (statusTag) statusTag.textContent = STEP_LABELS[i] || 'Processing…';
      await delay(700);
    }
  }

  // Start animation in parallel with actual API call
  const [, result] = await Promise.allSettled([
    animateSteps(),
    trainModel(),
  ]);

  // Mark all done
  steps.forEach(s => { s.classList.remove('active'); s.classList.add('done'); });

  if (result.status === 'fulfilled' && result.value?.status === 'success') {
    const m = result.value.metrics || {};
    if (statusTag) {
      statusTag.textContent  = 'Trained ✓';
      statusTag.style.color  = 'var(--sage-600)';
    }
    if (trainResult) {
      trainResult.innerHTML = `
        <div class="alert alert--success">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
          <div>
            <strong>Model Training Complete!</strong><br>
            Yield R² = <strong>${m.yield_r2 ?? '—'}</strong> &nbsp;·&nbsp;
            Drought Accuracy = <strong>${m.drought_accuracy ? (m.drought_accuracy * 100).toFixed(1) + '%' : '—'}</strong> &nbsp;·&nbsp;
            Disease Accuracy = <strong>${m.disease_accuracy ? (m.disease_accuracy * 100).toFixed(1) + '%' : '—'}</strong><br>
            OOB Score = <strong>${m.yield_oob ? (m.yield_oob * 100).toFixed(1) + '%' : '—'}</strong> &nbsp;·&nbsp;
            Training time = <strong>${m.training_time_sec ?? '—'}s</strong> &nbsp;·&nbsp;
            Samples = <strong>${m.n_train?.toLocaleString() ?? '—'}</strong> train
            <br><br>
            <a href="recommend.html" class="btn btn--primary btn--sm" style="display:inline-flex">
              Proceed to Recommendations →
            </a>
          </div>
        </div>`;
    }
    if (typeof showToast === 'function') showToast('Model trained successfully!', 'success');

    // Refresh model status section
    loadModelStatus();

  } else {
    const err = result.reason?.message || result.value?.error || 'Training failed';
    if (statusTag) { statusTag.textContent = 'Error'; statusTag.style.color = 'var(--coral)'; }
    if (trainResult) {
      trainResult.innerHTML = `<div class="alert alert--error"><strong>Training failed:</strong> ${err}</div>`;
    }
    if (typeof showToast === 'function') showToast('Training failed: ' + err, 'error');
  }

  if (trainBtn) {
    trainBtn.disabled = false;
    trainBtn.innerHTML = `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:16px;height:16px">
        <path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/>
        <path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/>
      </svg>
      Retrain Model
    `;
  }
}

async function trainModel() {
  const res  = await fetch(`${API_BASE}/api/train`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model_name: 'random_forest' }),
  });
  return await res.json();
}

/* ── Model status on load ────────────────────────────────────────────────── */
async function checkModelStatus() {
  try {
    const res  = await fetch(`${API_BASE}/api/model/status`);
    if (!res.ok) return;
    const data = await res.json();
    if (data.trained) loadModelStatus(data);
  } catch (_) { /* server not running */ }
}

async function loadModelStatus(statusData) {
  try {
    const data = statusData || await (await fetch(`${API_BASE}/api/model/status`)).json();
    if (!data.trained) return;

    const section = document.getElementById('model-metrics-section');
    if (section) section.classList.remove('hidden');

    const cards = document.getElementById('model-metric-cards');
    if (!cards) return;

    const m = data.metrics || {};
    const trainSec = document.getElementById('train-section');
    if (trainSec) trainSec.classList.remove('hidden');

    cards.innerHTML = `
      <div class="metric-card metric-card--yield">
        <div class="metric-card__label">Yield R²</div>
        <div class="metric-card__value">${m.yield_r2 ?? '—'}</div>
        <div class="metric-card__sub">Regression accuracy</div>
      </div>
      <div class="metric-card metric-card--drought">
        <div class="metric-card__label">Drought Accuracy</div>
        <div class="metric-card__value" style="font-size:var(--t-2xl)">${m.drought_accuracy ? (m.drought_accuracy * 100).toFixed(1) + '%' : '—'}</div>
        <div class="metric-card__sub">Test set</div>
      </div>
      <div class="metric-card metric-card--disease">
        <div class="metric-card__label">Disease Accuracy</div>
        <div class="metric-card__value" style="font-size:var(--t-2xl)">${m.disease_accuracy ? (m.disease_accuracy * 100).toFixed(1) + '%' : '—'}</div>
        <div class="metric-card__sub">Test set</div>
      </div>
      <div class="metric-card metric-card--confidence">
        <div class="metric-card__label">Training Samples</div>
        <div class="metric-card__value" style="font-size:var(--t-2xl)">${(m.n_train || 0).toLocaleString()}</div>
        <div class="metric-card__sub">70% of dataset</div>
      </div>
    `;
  } catch (_) {}
}

/* ── Utility ─────────────────────────────────────────────────────────────── */
const delay = ms => new Promise(r => setTimeout(r, ms));
