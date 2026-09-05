/**
 * utils.js — Pure utility functions for the CrossWise
 * No DOM side-effects. All functions are stateless and independently testable.
 */

/** LocalStorage getter with fallback. */
function lsGet(key, fallback = null) {
  try {
    const item = localStorage.getItem(key);
    return item ? JSON.parse(item) : fallback;
  } catch (e) {
    return fallback;
  }
}

/** LocalStorage setter. */
function lsSet(key, val) {
  try {
    localStorage.setItem(key, JSON.stringify(val));
  } catch (e) {
    console.error('lsSet error:', e);
  }
}

/** Formats yield number as t/ha. */
function formatYield(val) {
  if (val === null || val === undefined || isNaN(val)) return '—';
  const num = typeof val === 'number' ? val : parseFloat(val);
  return num ? `${num.toFixed(2)} t/ha` : '—';
}

/** Formats percentage score. */
function formatScore(val) {
  if (val === null || val === undefined || isNaN(val)) return '—';
  const num = typeof val === 'number' ? val : parseFloat(val);
  return num > 1 ? `${num.toFixed(1)}%` : `${(num * 100).toFixed(1)}%`;
}

/** Formats ISO date string to readable format. */
function formatDate(dateStr) {
  if (!dateStr) return '—';
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch (e) {
    return dateStr;
  }
}

/** Downloads JS object as JSON file. */
function downloadJSON(data, filename) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  triggerDownload(blob, filename);
}

/** Renders toast notification. */
function showToast(msg, type = 'info') {
  let toastContainer = document.getElementById('toast-container');
  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.id = 'toast-container';
    toastContainer.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:9999;display:flex;flex-direction:column;gap:8px;';
    document.body.appendChild(toastContainer);
  }
  const toast = document.createElement('div');
  toast.className = `alert alert--${type}`;
  toast.style.cssText = 'box-shadow:var(--sh-md);animation:fadeUp 0.3s var(--ease-out);margin:0;min-width:280px;';
  toast.innerHTML = `<div>${msg}</div>`;
  toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

/** Initializes scroll reveal observer for [data-reveal] elements. */
function initScrollReveal() {
  const els = document.querySelectorAll('[data-reveal]:not(.revealed)');
  if (!els.length) return;
  if ('IntersectionObserver' in window) {
    const obs = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add('revealed');
          obs.unobserve(e.target);
        }
      });
    }, { threshold: 0.1 });
    els.forEach((el) => obs.observe(el));
  } else {
    els.forEach((el) => el.classList.add('revealed'));
  }
}

document.addEventListener('DOMContentLoaded', initScrollReveal);


/** Creates a temporary <a> link and clicks it to trigger a file download. */
function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = Object.assign(document.createElement('a'), { href: url, download: filename });
  a.click();
  URL.revokeObjectURL(url);
}
