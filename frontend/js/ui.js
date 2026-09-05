/**
 * ui.js — All DOM state management for the CrossWise.
 * Depends on utils.js (must be loaded first).
 */

// ─── State ────────────────────────────────────────────────────────────────────

/** @type {'upload'|'manual'|null} */
let activeMethod = null;

/** Snapshot of last prediction result, used by downloadReport. */
let lastResults = null;

// ─── Input Method Selection ────────────────────────────────────────────────────

/**
 * Switches the visible input section to either 'upload' or 'manual'.
 * @param {'upload'|'manual'} method
 */
function selectInputMethod(method) {
  activeMethod = method;

  // Show/hide sections
  setVisible('upload-section', method === 'upload');
  setVisible('manual-section', method === 'manual');

  // Reveal action buttons
  document.getElementById('predict-btn').style.display = 'inline-flex';
  document.getElementById('reset-btn').style.display = 'inline-flex';

  // Highlight active mode button
  document.getElementById('upload-btn').classList.toggle('btn--active', method === 'upload');
  document.getElementById('manual-btn').classList.toggle('btn--active', method === 'manual');

  clearError();
  hideResults();
}

// ─── Modal ────────────────────────────────────────────────────────────────────

/**
 * Builds and displays the confirmation modal with an input summary.
 */
function showConfirmationModal() {
  const summaryEl = document.getElementById('input-summary');

  if (activeMethod === 'upload') {
    const f1 = document.getElementById('parent1').files[0];
    const f2 = document.getElementById('parent2').files[0];
    summaryEl.innerHTML = `
      <div class="summary-row"><span class="summary-label">Method</span><span class="summary-value">FASTA Upload</span></div>
      <div class="summary-row"><span class="summary-label">Parent 1</span><span class="summary-value">${f1 ? f1.name : '<em>not selected</em>'}</span></div>
      <div class="summary-row"><span class="summary-label">Parent 2</span><span class="summary-value">${f2 ? f2.name : '<em>not selected</em>'}</span></div>
    `;
  } else {
    const v = (id) => document.getElementById(id).value;
    summaryEl.innerHTML = `
      <div class="summary-row"><span class="summary-label">Method</span><span class="summary-value">Manual Entry</span></div>
      <div class="summary-parents">
        <div class="summary-parent">
          <strong>Parent 1</strong>
          <span>A: ${v('parent1_a')}</span>
          <span>T: ${v('parent1_t')}</span>
          <span>G: ${v('parent1_g')}</span>
          <span>C: ${v('parent1_c')}</span>
        </div>
        <div class="summary-parent">
          <strong>Parent 2</strong>
          <span>A: ${v('parent2_a')}</span>
          <span>T: ${v('parent2_t')}</span>
          <span>G: ${v('parent2_g')}</span>
          <span>C: ${v('parent2_c')}</span>
        </div>
      </div>
    `;
  }

  openModal('confirmation-modal');
}

function closeConfirmationModal() {
  closeModal('confirmation-modal');
}

function showVersionModal() {
  openModal('version-modal');
}

function closeVersionModal() {
  closeModal('version-modal');
}

function openModal(id) {
  const modal = document.getElementById(id);
  modal.setAttribute('aria-hidden', 'false');
  modal.style.display = 'flex';
}

function closeModal(id) {
  const modal = document.getElementById(id);
  modal.setAttribute('aria-hidden', 'true');
  modal.style.display = 'none';
}

// ─── Progress & Loading ───────────────────────────────────────────────────────

function showLoading(message = 'Processing prediction…') {
  const el = document.getElementById('loading');
  el.querySelector('.loading-text').textContent = message;
  el.style.display = 'flex';
}

function hideLoading() {
  document.getElementById('loading').style.display = 'none';
}

function updateProgress(label, pct) {
  const container = document.getElementById('progress-container');
  const fill = document.getElementById('progress-bar');
  container.style.display = 'block';
  fill.style.width = `${pct}%`;
  fill.setAttribute('aria-valuenow', pct);
  // The label <span> is inside .progress-label <p>
  const labelEl = container.querySelector('.progress-label span');
  if (labelEl) labelEl.textContent = label;
}

function hideProgress() {
  document.getElementById('progress-container').style.display = 'none';
  document.getElementById('progress-bar').style.width = '0%';
}

// ─── Error ────────────────────────────────────────────────────────────────────

function showError(message) {
  const el = document.getElementById('error-message');
  el.textContent = message;
  el.style.display = 'flex';
  el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function clearError() {
  const el = document.getElementById('error-message');
  el.textContent = '';
  el.style.display = 'none';
}

// ─── Results ──────────────────────────────────────────────────────────────────

/**
 * Populates the results section with prediction data and switches the view.
 * @param {object} data — backend response
 */
function displayResults(data) {
  lastResults = data;

  // Populate result fields
  setText('result-crop', data.hybrid_crop ?? '—');
  setText('result-gc', data.gc_content !== undefined ? data.gc_content.toFixed(2) + '%' : '—');
  setText('result-snp', data.snp_count !== undefined ? Math.round(data.snp_count).toString() : '—');
  setText('result-yield', data.yield_potential !== undefined ? data.yield_potential.toFixed(2) + ' kg/ha' : '—');
  setText('result-drought', data.drought_resistance !== undefined ? Math.round(data.drought_resistance) + '%' : '—');
  setText('result-disease', data.disease_resistance !== undefined ? Math.round(data.disease_resistance) + '%' : '—');

  // Set trait badge colours
  setBadgeLevel('badge-drought', data.drought_resistance);
  setBadgeLevel('badge-disease', data.disease_resistance);

  // Transition to results view
  document.getElementById('main-view').style.display = 'none';
  document.getElementById('results-view').style.display = 'block';
  document.getElementById('results-view').scrollIntoView({ behavior: 'smooth' });
}

/**
 * Assigns a semantic class to a badge based on percentage score.
 * @param {string} id
 * @param {number|undefined} pct
 */
function setBadgeLevel(id, pct) {
  const el = document.getElementById(id);
  if (!el || pct === undefined) return;
  el.classList.remove('badge--low', 'badge--medium', 'badge--high');
  if (pct >= 75) {
    el.classList.add('badge--high');
    el.textContent = 'High';
  } else if (pct >= 40) {
    el.classList.add('badge--medium');
    el.textContent = 'Moderate';
  } else {
    el.classList.add('badge--low');
    el.textContent = 'Low';
  }
}

function hideResults() {
  document.getElementById('main-view').style.display = 'block';
  document.getElementById('results-view').style.display = 'none';
}

// ─── Reset ────────────────────────────────────────────────────────────────────

/**
 * Resets the entire form back to its initial empty state.
 */
function resetForm() {
  // Clear file inputs
  document.getElementById('parent1').value = '';
  document.getElementById('parent2').value = '';

  // Reset nucleotide inputs
  document.querySelectorAll('input[type="number"]').forEach((el) => (el.value = '0.250'));

  // Hide sections and buttons
  setVisible('upload-section', false);
  setVisible('manual-section', false);
  document.getElementById('predict-btn').style.display = 'none';
  document.getElementById('reset-btn').style.display = 'none';

  // Remove active state from mode buttons
  document.getElementById('upload-btn').classList.remove('btn--active');
  document.getElementById('manual-btn').classList.remove('btn--active');

  // Reset state
  activeMethod = null;
  lastResults = null;

  clearError();
  hideProgress();
  hideLoading();
  hideResults();
  clearLocalStorage();
}

// ─── Download ─────────────────────────────────────────────────────────────────

/**
 * Triggers the CSV report download for the last prediction result.
 */
function triggerReportDownload() {
  if (!lastResults) return;
  downloadReport(lastResults);
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function setVisible(id, visible) {
  const el = document.getElementById(id);
  if (el) el.style.display = visible ? 'block' : 'none';
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

/** Returns the currently active input method. */
function getActiveMethod() {
  return activeMethod;
}
