
// Minimal upload logic for SNP Candidate file
let snpFile = null;

function handleFileSelect(file, type) {
  if (type === 'snp') snpFile = file;
  updateStatus();
}

function updateStatus() {
  const btn = document.getElementById('upload-submit-btn');
  btn.disabled = !snpFile;
  
  if (snpFile) {
    document.getElementById('snp-file-status').innerHTML = `<span style="color:var(--success)">Loaded: ${snpFile.name}</span>`;
    document.getElementById('snp-file-status').classList.remove('hidden');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  // SNP Drag/Drop
  const snpZone = document.getElementById('zone-snp');
  const snpInput = document.getElementById('snp-file-input');
  
  snpZone.addEventListener('click', () => snpInput.click());
  snpInput.addEventListener('change', (e) => {
    if (e.target.files.length) handleFileSelect(e.target.files[0], 'snp');
  });

  ['dragover', 'dragleave', 'drop'].forEach(evt => {
    snpZone.addEventListener(evt, (e) => {
      e.preventDefault();
      if (evt === 'dragover') snpZone.classList.add('upload-zone--active');
      if (evt === 'dragleave') snpZone.classList.remove('upload-zone--active');
      if (evt === 'drop') {
        snpZone.classList.remove('upload-zone--active');
        if (e.dataTransfer.files.length) handleFileSelect(e.dataTransfer.files[0], 'snp');
      }
    });
  });

  // Submit
  const submitBtn = document.getElementById('upload-submit-btn');
  submitBtn.addEventListener('click', async () => {
    if (!snpFile) return;

    submitBtn.disabled = true;
    const mask = document.getElementById('processing-mask');
    const statusText = document.getElementById('processing-status');
    const progressBar = document.getElementById('processing-bar');
    
    if (mask) mask.style.display = 'flex';

    const location = document.getElementById('location-select').value;
    lsSet('selected_location', location);

    const formData = new FormData();
    formData.append('snp_file', snpFile);

    try {
      // Step 1: Upload File
      if (statusText) statusText.innerText = 'Uploading SNP Data...';
      if (progressBar) progressBar.style.width = '30%';
      
      const res = await apiFetch(`${API_BASE}/api/upload`, {
        method: 'POST',
        body: formData,
        headers: {} // Don't set content-type for FormData
      });

      if (!res.filename) throw new Error("Upload failed");
      
      lsSet('last_candidate_file', res.filename);
      
      // Step 2: Trigger Recommendation Pipeline
      if (statusText) statusText.innerText = 'Evaluating Millions of Combinations...';
      if (progressBar) progressBar.style.width = '60%';
      
      const body = { 
        top_n: 20,
        location_filter: location,
        candidate_file: res.filename
      };

      const recRes = await apiFetch(`${API_BASE}/api/recommend/snp`, {
        method:  'POST',
        body:    JSON.stringify(body),
      });
      
      if (!recRes.top_recommendations) throw new Error("Recommendation failed");
      
      // Normalize recommendations
      const recs = recRes.top_recommendations.map((r, idx) => ({
        rank:                  r.rank       || idx + 1,
        hybrid_name:           r.hybrid_name || `${r.parent_a} × ${r.parent_b}`,
        parent_1:              r.parent_a    || r.parent_1 || 'Line_?',
        parent_2:              r.parent_b    || r.parent_2 || 'Line_?',
        predicted_yield:       r.predicted_yield       || 0,
        predicted_drought:     r.predicted_drought     || 'Medium',
        predicted_disease:     r.predicted_disease     || 'Moderate',
        predicted_quality:     r.predicted_quality     || 'Standard',
        predicted_maturity:    r.predicted_maturity    || 'Medium',
        genomic_compatibility: r.genomic_compatibility || 0.65,
        recommendation_score:  r.recommendation_score  || 0.80,
        confidence:            r.confidence            || 0.85,
      }));

      // Step 3: Save to History DB and Session
      if (statusText) statusText.innerText = 'Saving Results...';
      if (progressBar) progressBar.style.width = '90%';

      lsSet('lastRecommendation', recs);
      lsSet('last_total_pairs', recRes.total_pairs_evaluated);
      lsSet('last_unique_parents', recRes.unique_parents);
      lsSet('last_env', recRes.location_filter);

      try {
        await apiFetch(`${API_BASE}/api/history`, {
          method: 'POST',
          body: JSON.stringify({
            top_hybrid:   recs[0]?.hybrid_name,
            top_score:    recs[0]?.recommendation_score,
            total_pairs:  recRes.total_pairs_evaluated || 499500,
            results:      recs,
          })
        });
      } catch (err) {
        console.error("Failed to save history to DB:", err);
      }

      if (progressBar) progressBar.style.width = '100%';
      
      // Step 4: Redirect
      window.location.href = 'recommend.html';
      
    } catch (err) {
      console.error(err);
      if (mask) mask.style.display = 'none';
      if (typeof showToast === 'function') showToast(err.message || "An error occurred", "error");
      submitBtn.disabled = false;
    }
  });
});
