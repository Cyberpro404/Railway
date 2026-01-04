// Frontend JavaScript for Training functionality
// Handles ML model training, prediction, and monitoring

// Global state
let trainingPage = 1;
const TRAINING_PAGE_SIZE = 25;
let trainingStats = null;
let modelInfo = null;
let isModelLoading = false;
let modelLoadPromise = null;
let predictionInterval = null;

// Training capture modal
function showCaptureModal() {
  if (!latest) {
    showToast('No sensor reading available to capture', 'error');
    return;
  }

  const modal = document.createElement('div');
  modal.className = 'modal';
  modal.innerHTML = `
    <div class="modal__content">
      <div class="modal__head">
        <h3>Capture Training Sample</h3>
        <button class="btn btn--text" onclick="closeCaptureModal()">×</button>
      </div>
      <div class="modal__body">
        <div class="capturePreview">
          <h4>Current Reading</h4>
          <div class="captureGrid">
            <div class="captureItem">
              <label>Z RMS:</label>
              <span>${fmt(latest.z_rms_mm_s, 3)} mm/s</span>
            </div>
            <div class="captureItem">
              <label>X RMS:</label>
              <span>${fmt(latest.x_rms_mm_s, 3)} mm/s</span>
            </div>
            <div class="captureItem">
              <label>Temperature:</label>
              <span>${fmt(latest.temp_c, 1)} °C</span>
            </div>
            <div class="captureItem">
              <label>Selected Band:</label>
              <span>${selectedBand ? `${axisLabel(selectedAxis)} · Band ${selectedBand} (${bandMultiple(selectedAxis ? latest.bands_x.find(b => b.band_number === selectedBand) : latest.bands_z.find(b => b.band_number === selectedBand))?.multiple || selectedBand}×)` : 'None'}</span>
            </div>
          </div>
        </div>
        
        <div class="formGroup">
          <label>Axis to capture</label>
          <select id="captureAxis">
            <option value="both">Both Z and X</option>
            <option value="z">Z axis only</option>
            <option value="x">X axis only</option>
          </select>
        </div>
        
        <div class="formGroup">
          <label>Label (optional)</label>
          <select id="captureLabel">
            <option value="">No label</option>
            <option value="normal">Normal</option>
            <option value="wheel_flat">Wheel Flat</option>
            <option value="loose_fastener">Loose Fastener</option>
            <option value="other">Other</option>
          </select>
        </div>
        
        <div class="formGroup" id="customLabelGroup" style="display: none;">
          <label>Custom label</label>
          <input type="text" id="customLabel" placeholder="Enter custom label">
        </div>
      </div>
      <div class="modal__foot">
        <button class="btn btn--secondary" onclick="closeCaptureModal()">Cancel</button>
        <button class="btn btn--primary" onclick="captureSample()">Capture Sample</button>
      </div>
    </div>
  `;
  
  document.body.appendChild(modal);
  
  // Handle label selection
  const labelSelect = qs('captureLabel');
  const customGroup = qs('customLabelGroup');
  labelSelect.addEventListener('change', () => {
    customGroup.style.display = labelSelect.value === 'other' ? 'block' : 'none';
  });
}

function closeCaptureModal() {
  const modal = document.querySelector('.modal');
  if (modal) {
    modal.remove();
  }
}

async function captureSample() {
  try {
    const axis = qs('captureAxis').value;
    const labelSelect = qs('captureLabel');
    let label = labelSelect.value;
    
    if (label === 'other') {
      label = qs('customLabel').value || null;
    }
    
    const payload = {
      axis: axis,
      label: label || null,
      selected_band_axis: selectedBand ? selectedAxis : null,
      selected_band_number: selectedBand || null
    };
    
    const result = await apiPostWithErrorHandling('/api/training/capture', payload);
    
    showToast(`Training sample saved (ID: ${result.inserted_id})`, 'success');
    closeCaptureModal();
    
    // Refresh training data if on training tab
    if (activeTab === 'training') {
      await refreshTrainingData();
    }
    
  } catch (error) {
    showToast(`Failed to capture sample: ${error.message}`, 'error');
  }
}

// Training data table
async function refreshTrainingData() {
  try {
    const [samples, stats] = await Promise.all([
      apiGetWithErrorHandling(`/api/training/samples?limit=${TRAINING_PAGE_SIZE}&offset=${(trainingPage - 1) * TRAINING_PAGE_SIZE}`),
      apiGetWithErrorHandling('/api/training/stats')
    ]);
    
    trainingStats = stats;
    renderTrainingSamplesTable(samples);
    renderTrainingStats(stats);
    updateTrainingPagination(samples.total);
    
  } catch (error) {
    console.error('Failed to refresh training data:', error);
    showToast('Failed to load training data', 'error');
  }
}

function renderTrainingSamplesTable(data) {
  const tbody = qs('trainingSamplesTable').querySelector('tbody');
  tbody.innerHTML = '';
  
  if (!data.items || data.items.length === 0) {
    tbody.innerHTML = '<tr><td colspan="10" class="muted" style="text-align:center; padding:24px;">No training samples captured yet. Use the Capture button to add samples.</td></tr>';
    return;
  }
  
  data.items.forEach(sample => {
    const row = document.createElement('tr');
    const bandInfo = sample.selected_band_number && sample.selected_band_axis 
      ? `${axisLabel(sample.selected_band_axis)}·${sample.selected_band_number}` 
      : '—';
    const labelClass = sample.label ? '' : 'muted';
    
    row.innerHTML = `
      <td><input type="checkbox" class="training__checkbox training__sampleCheck" data-id="${sample.id}"></td>
      <td><span class="training__id">#${sample.id}</span></td>
      <td><span class="training__timestamp">${new Date(sample.timestamp).toLocaleString()}</span></td>
      <td><span class="pill pill--axis">${sample.axis.toUpperCase()}</span></td>
      <td><span class="${labelClass}">${sample.label || '—'}</span></td>
      <td>${fmt(sample.z_rms_mm_s, 3)}</td>
      <td>${fmt(sample.x_rms_mm_s, 3)}</td>
      <td>${fmt(sample.temp_c, 1)}°</td>
      <td>${bandInfo}</td>
      <td>
        <div class="training__rowActions">
          <button class="training__rowBtn" onclick="editSampleLabel(${sample.id})" title="Edit label"><i data-lucide="pencil"></i></button>
          <button class="training__rowBtn" onclick="deleteSample(${sample.id})" title="Delete"><i data-lucide="trash-2"></i></button>
        </div>
      </td>
    `;
    tbody.appendChild(row);
  });
  
  // Re-init lucide icons for new buttons
  if (window.lucide) lucide.createIcons();
}

function renderTrainingStats(stats) {
  // Update stat cards
  const totalEl = document.getElementById('totalSamplesCount');
  const labeledEl = document.getElementById('labeledCount');
  const uniqueEl = document.getElementById('uniqueLabelsCount');
  const modelBadgeEl = document.getElementById('modelStatusBadge');
  const statsEl = qs('trainingStats');
  
  if (totalEl) totalEl.textContent = stats.total_samples || 0;
  
  // Count labeled samples
  const labeledCount = Object.values(stats.label_counts || {}).reduce((a, b) => a + b, 0);
  if (labeledEl) labeledEl.textContent = labeledCount;
  
  // Count unique labels
  const uniqueLabels = Object.keys(stats.label_counts || {}).length;
  if (uniqueEl) uniqueEl.textContent = uniqueLabels;
  
  // Update filter dropdown with labels
  const filterLabelEl = document.getElementById('filterLabel');
  if (filterLabelEl && stats.label_counts) {
    const currentVal = filterLabelEl.value;
    filterLabelEl.innerHTML = '<option value="">All Labels</option>';
    Object.keys(stats.label_counts).forEach(label => {
      filterLabelEl.innerHTML += `<option value="${label}">${label} (${stats.label_counts[label]})</option>`;
    });
    filterLabelEl.value = currentVal;
  }
  
  // Page info
  if (statsEl) {
    statsEl.textContent = `${stats.total_samples || 0} samples`;
  }
}

function updateTrainingPagination(total) {
  const totalPages = Math.ceil(total / TRAINING_PAGE_SIZE);
  const prevBtn = qs('trainingPrevBtn');
  const nextBtn = qs('trainingNextBtn');
  const pageInfo = qs('trainingPageInfo');
  
  if (prevBtn) prevBtn.disabled = trainingPage <= 1;
  if (nextBtn) nextBtn.disabled = trainingPage >= totalPages;
  if (pageInfo) pageInfo.textContent = `${trainingPage} / ${totalPages || 1}`;
}

// Model loading and management
async function ensureModelLoaded() {
  if (modelInfo?.is_loaded) return true;
  
  // If model is already being loaded, return the existing promise
  if (isModelLoading && modelLoadPromise) {
    return modelLoadPromise;
  }
  
  isModelLoading = true;
  try {
    // Try to load the model
    modelLoadPromise = (async () => {
      try {
        // First check if model exists
        modelInfo = await apiGet('api/training/model/info');
        
        // If model exists but not loaded, load it
        if (modelInfo.model_exists && !modelInfo.is_loaded) {
          await apiPost('api/training/model/load', {});
          modelInfo = await apiGet('api/training/model/info');
        }
        
        return modelInfo?.is_loaded || false;
      } catch (error) {
        console.error('Error loading model:', error);
        showToast('Failed to load ML model: ' + (error.message || 'Unknown error'), 'error');
        return false;
      } finally {
        isModelLoading = false;
      }
    })();
    
    return await modelLoadPromise;
  } catch (error) {
    isModelLoading = false;
    console.error('Error in ensureModelLoaded:', error);
    return false;
  }
}

// Model training and info
async function refreshModelInfo() {
  try {
    // Get current model info
    modelInfo = await apiGet('api/training/model/info');
    
    // If model exists but not loaded, try to load it
    if (modelInfo?.model_exists && !modelInfo.is_loaded) {
      const loaded = await ensureModelLoaded();
      if (loaded) {
        // Refresh the model info after loading
        modelInfo = await apiGet('api/training/model/info');
      }
    }
    
    // Update the UI with the latest model info
    renderModelStatus(modelInfo);
    
    // Update prediction buttons state
    const predictBtn = document.getElementById('predictBtn');
    const batchPredictBtn = document.getElementById('batchPredictBtn');
    
    if (predictBtn) predictBtn.disabled = !(modelInfo?.is_loaded);
    if (batchPredictBtn) batchPredictBtn.disabled = !(modelInfo?.is_loaded);
    
    return modelInfo;
  } catch (error) {
    console.error('Error fetching model info:', error);
    showToast('Failed to load model info: ' + (error.message || 'Unknown error'), 'error');
    return null;
  }
}

function renderModelStatus(info) {
  const statusEl = document.getElementById('modelStatus');
  const modelCard = document.getElementById('modelCard');
  const modelInfoEl = document.getElementById('modelInfo');
  const modelMetricsEl = document.getElementById('modelMetrics');
  const modelActionsEl = document.getElementById('modelActions');
  const predictBtn = document.getElementById('predictBtn');
  const batchPredictBtn = document.getElementById('batchPredictBtn');
  
  if (!modelCard) return;
  
  if (!info || !info.model_exists) {
    // No model exists
    modelCard.className = 'model-status-card border-warning';
    modelCard.innerHTML = `
      <div class="model-status-header bg-warning text-white">
        <div class="d-flex align-items-center">
          <i class="fas fa-exclamation-triangle me-2"></i>
          <span>No Model Trained</span>
        </div>
      </div>
      <div class="model-status-body">
        <p class="mb-4">Train a model to start making predictions on your data.</p>
        <div class="d-flex justify-content-between align-items-center">
          <small class="text-muted">At least 20 samples with 2+ labels required</small>
          <button class="btn btn-sm btn-primary" id="trainModelBtn">
            <i class="fas fa-cogs me-1"></i> Train Model
          </button>
        </div>
      </div>
    `;
    
    // Add event listener to the train button
    modelCard.querySelector('#trainModelBtn')?.addEventListener('click', trainModel);
    
  } else if (info.is_loaded) {
    // Model is loaded and ready
    const accuracy = info.metrics?.accuracy || 0;
    const precision = info.metrics?.precision || 0;
    const recall = info.metrics?.recall || 0;
    const f1 = info.metrics?.f1 || 0;
    const trainingDate = info.trained_at ? new Date(info.trained_at).toLocaleString() : 'Unknown';
    
    modelCard.className = 'model-status-card border-success';
    modelCard.innerHTML = `
      <div class="model-status-header bg-success text-white">
        <div class="d-flex align-items-center">
          <i class="fas fa-check-circle me-2"></i>
          <span>Model Ready</span>
        </div>
        <span class="badge bg-light text-dark">${info.algorithm || 'Unknown'}</span>
      </div>
      <div class="model-status-body">
        <div class="model-metrics mb-4">
          <div class="metric-card">
            <div class="metric-value text-success">${(accuracy * 100).toFixed(1)}%</div>
            <div class="metric-label">Accuracy</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">${(precision * 100).toFixed(1)}%</div>
            <div class="metric-label">Precision</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">${(recall * 100).toFixed(1)}%</div>
            <div class="metric-label">Recall</div>
          </div>
          <div class="metric-card">
            <div class="metric-value">${f1.toFixed(3)}</div>
            <div class="metric-label">F1 Score</div>
          </div>
        </div>
        
        <div class="d-flex justify-content-between align-items-center mb-3">
          <div>
            <small class="text-muted">Trained on</small>
            <div class="fw-bold">${trainingDate}</div>
          </div>
          <div class="text-end">
            <small class="text-muted">Samples used</small>
            <div class="fw-bold">${info.n_samples || 0}</div>
          </div>
        </div>
        
        <div class="d-grid gap-2">
          <button class="btn btn-primary" id="predictBtn">
            <i class="fas fa-bolt me-1"></i> Make Prediction
          </button>
          <button class="btn btn-outline-secondary" id="batchPredictBtn">
            <i class="fas fa-bolt me-1"></i> Batch Predict
          </button>
        </div>
      </div>
    `;
    
    // Add event listeners
    modelCard.querySelector('#predictBtn')?.addEventListener('click', makePrediction);
    modelCard.querySelector('#batchPredictBtn')?.addEventListener('click', batchPredict);
    
  } else if (info.model_exists && !info.is_loaded) {
    // Model exists but not loaded
    modelCard.className = 'model-status-card border-warning';
    modelCard.innerHTML = `
      <div class="model-status-header bg-warning text-dark">
        <div class="d-flex align-items-center">
          <i class="fas fa-exclamation-circle me-2"></i>
          <span>Model Not Loaded</span>
        </div>
      </div>
      <div class="model-status-body">
        <p class="mb-3">A trained model exists but is not currently loaded.</p>
        <div class="d-grid gap-2">
          <button class="btn btn-primary" id="loadModelBtn">
            <i class="fas fa-box-open me-1"></i> Load Model
          </button>
          <button class="btn btn-outline-secondary" id="retrainModelBtn">
            <i class="fas fa-sync-alt me-1"></i> Train New Model
          </button>
        </div>
      </div>
    `;
    
    // Add event listeners
    modelCard.querySelector('#loadModelBtn')?.addEventListener('click', async () => {
      const loaded = await ensureModelLoaded();
      if (loaded) {
        await refreshModelInfo();
      }
    });
    
    modelCard.querySelector('#retrainModelBtn')?.addEventListener('click', trainModel);
  }
  
  // Update prediction buttons state
  const isModelReady = info?.model_exists && info?.is_loaded;
  if (predictBtn) predictBtn.disabled = !isModelReady;
  if (batchPredictBtn) batchPredictBtn.disabled = !isModelReady;
}

async function trainModel() {
  if (!trainingStats || trainingStats.total_samples < 20) {
    showToast('Need at least 20 training samples to train model', 'error');
    return;
  }
  
  if (!trainingStats.label_counts || Object.keys(trainingStats.label_counts).length < 2) {
    showToast('Need at least 2 different labels to train classification model', 'error');
    return;
  }
  
  const progressEl = qs('trainingProgress');
  const resultsEl = qs('trainingResults');
  const progressFill = qs('trainingProgressFill');
  const progressText = qs('trainingProgressText');
  const progressPercent = document.getElementById('trainingPercent');
  const modelBadgeEl = document.getElementById('modelBadge');
  
  // Update badge to training state
  if (modelBadgeEl) {
    modelBadgeEl.className = 'training__modelBadge is-training';
    modelBadgeEl.innerHTML = '<span class="dot"></span><span>Training...</span>';
  }
  
  // Show progress
  if (progressEl) progressEl.style.display = 'block';
  if (resultsEl) resultsEl.style.display = 'none';
  if (progressText) progressText.textContent = 'Preparing data...';
  if (progressFill) progressFill.style.width = '0%';
  if (progressPercent) progressPercent.textContent = '0%';
  
  try {
    const payload = {
      target_label_field: qs('targetLabelField').value,
      algorithm: qs('trainingAlgorithm').value,
      test_split: parseFloat(document.getElementById('testSplit')?.value || 20) / 100,
      min_samples: parseInt(document.getElementById('minSamples')?.value || 50)
    };
    
    // Simulate progress with stages
    let progress = 0;
    const stages = ['Preparing data...', 'Extracting features...', 'Training model...', 'Evaluating...'];
    let stageIdx = 0;
    const progressInterval = setInterval(() => {
      progress += 8;
      if (progressFill) progressFill.style.width = `${Math.min(progress, 90)}%`;
      if (progressPercent) progressPercent.textContent = `${Math.min(progress, 90)}%`;
      if (progress % 25 === 0 && stageIdx < stages.length - 1) {
        stageIdx++;
        if (progressText) progressText.textContent = stages[stageIdx];
      }
      if (progress >= 90) clearInterval(progressInterval);
    }, 180);
    
    const result = await apiPostWithErrorHandling('/api/training/train', payload);
    
    clearInterval(progressInterval);
    if (progressFill) progressFill.style.width = '100%';
    if (progressPercent) progressPercent.textContent = '100%';
    if (progressText) progressText.textContent = 'Training complete!';
    
    // Show results
    setTimeout(() => {
      if (progressEl) progressEl.style.display = 'none';
      if (resultsEl) {
        resultsEl.style.display = 'block';
        const metricsEl = qs('trainingMetrics');
        if (metricsEl) {
          const accuracy = result.metrics?.accuracy || result.metrics?.test_accuracy;
          const precision = result.metrics?.precision || result.metrics?.weighted_precision;
          const recall = result.metrics?.recall || result.metrics?.weighted_recall;
          const f1 = result.metrics?.f1_score || result.metrics?.weighted_f1;
          
          metricsEl.innerHTML = `
            <div class="training__metric">
              <div class="training__metricValue ${accuracy >= 0.8 ? 'is-ok' : accuracy >= 0.6 ? 'is-warn' : ''}">${accuracy ? (accuracy * 100).toFixed(1) + '%' : '—'}</div>
              <div class="training__metricLabel">Accuracy</div>
            </div>
            <div class="training__metric">
              <div class="training__metricValue">${precision ? (precision * 100).toFixed(1) + '%' : '—'}</div>
              <div class="training__metricLabel">Precision</div>
            </div>
            <div class="training__metric">
              <div class="training__metricValue">${recall ? (recall * 100).toFixed(1) + '%' : '—'}</div>
              <div class="training__metricLabel">Recall</div>
            </div>
            <div class="training__metric">
              <div class="training__metricValue">${f1 ? (f1 * 100).toFixed(1) + '%' : '—'}</div>
              <div class="training__metricLabel">F1 Score</div>
            </div>
          `;
        }
      }
      
      showToast('Model trained successfully!', 'success');
      refreshModelInfo();
    }, 1000);
    
  } catch (error) {
    if (progressEl) progressEl.style.display = 'none';
    showToast(`Training failed: ${error.message}`, 'error');
  }
}

// Event listeners
function setupTrainingEventListeners() {
  // Capture button
  const captureBtn = qs('captureTrainingBtn');
  if (captureBtn) {
    captureBtn.addEventListener('click', showCaptureModal);
  }
  
  // Training pagination
  const prevBtn = qs('trainingPrevBtn');
  const nextBtn = qs('trainingNextBtn');
  if (prevBtn) prevBtn.addEventListener('click', () => {
    if (trainingPage > 1) {
      trainingPage--;
      refreshTrainingData();
    }
  });
  if (nextBtn) nextBtn.addEventListener('click', () => {
    trainingPage++;
    refreshTrainingData();
  });
  
  // Train model button
  const trainBtn = qs('trainModelBtn');
  if (trainBtn) {
    trainBtn.addEventListener('click', trainModel);
  }
  
  // Refresh button
  const refreshBtn = document.getElementById('refreshTrainingBtn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      refreshTrainingData();
      refreshModelInfo();
    });
  }
  
  // Export button
  const exportBtn = document.getElementById('exportTrainingBtn');
  if (exportBtn) {
    exportBtn.addEventListener('click', exportTrainingData);
  }
  
  // Select all checkbox
  const selectAll = document.getElementById('selectAllSamples');
  if (selectAll) {
    selectAll.addEventListener('change', (e) => {
      document.querySelectorAll('.training__sampleCheck').forEach(cb => {
        cb.checked = e.target.checked;
      });
    });
  }
}

// Export training data
async function exportTrainingData() {
  try {
    const data = await apiGetWithErrorHandling('/api/training/samples?limit=10000');
    if (!data.items || data.items.length === 0) {
      showToast('No training data to export', 'error');
      return;
    }
    
    const headers = ['id', 'timestamp', 'axis', 'label', 'z_rms_mm_s', 'x_rms_mm_s', 'temp_c', 'selected_band_number'];
    const csv = [
      headers.join(','),
      ...data.items.map(row => headers.map(h => JSON.stringify(row[h] ?? '')).join(','))
    ].join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `training_data_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('Training data exported', 'success');
  } catch (error) {
    showToast(`Export failed: ${error.message}`, 'error');
  }
}

// Edit sample label
async function editSampleLabel(sampleId) {
  const newLabel = prompt('Enter new label (or leave empty to clear):');
  if (newLabel === null) return;
  
  try {
    await apiPostWithErrorHandling(`/api/training/samples/${sampleId}/label`, { label: newLabel || null });
    showToast('Label updated', 'success');
    refreshTrainingData();
  } catch (error) {
    showToast(`Failed to update label: ${error.message}`, 'error');
  }
}

// Delete sample
async function deleteSample(sampleId) {
  if (!confirm('Delete this training sample?')) return;
  
  try {
    await fetch(`/api/training/samples/${sampleId}`, { method: 'DELETE' });
    showToast('Sample deleted', 'success');
    refreshTrainingData();
  } catch (error) {
    showToast(`Failed to delete: ${error.message}`, 'error');
  }
}

// Make a prediction with the current sensor reading
async function makePrediction() {
  if (!latest) {
    showToast('No sensor reading available for prediction', 'warning');
    return;
  }

  try {
    const predictBtn = document.getElementById('predictBtn');
    const originalText = predictBtn.innerHTML;
    predictBtn.disabled = true;
    predictBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Predicting...';

    // Prepare the sample data for prediction
    const sample = {
      z_rms_mm_s: latest.z_rms_mm_s,
      x_rms_mm_s: latest.x_rms_mm_s,
      temp_c: latest.temp_c,
      // Add frequency bands if available
      ...(latest.bands_z && { bands_z: latest.bands_z }),
      ...(latest.bands_x && { bands_x: latest.bands_x })
    };

    // Make the prediction request
    const result = await apiPost('api/training/model/predict', { sample });
    
    // Show the prediction result
    showPredictionResult(result);
    
  } catch (error) {
    console.error('Prediction error:', error);
    showToast(`Prediction failed: ${error.message || 'Unknown error'}`, 'error');
  } finally {
    const predictBtn = document.getElementById('predictBtn');
    if (predictBtn) {
      predictBtn.disabled = false;
      predictBtn.innerHTML = '<i class="fas fa-bolt me-1"></i> Make Prediction';
    }
  }
}

// Make batch predictions on multiple samples
async function batchPredict() {
  try {
    const batchPredictBtn = document.getElementById('batchPredictBtn');
    batchPredictBtn.disabled = true;
    const originalText = batchPredictBtn.innerHTML;
    batchPredictBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Processing...';

    // Get recent samples for batch prediction
    const samples = await apiGet('api/training/samples/recent?limit=10');
    if (!samples || samples.length === 0) {
      showToast('No samples available for batch prediction', 'warning');
      return;
    }
    
    // Make batch prediction request
    const result = await apiPost('api/training/model/batch-predict', { samples });
    
    // Show batch prediction results
    showBatchPredictionResults(result);
    
  } catch (error) {
    console.error('Batch prediction error:', error);
    showToast(`Batch prediction failed: ${error.message || 'Unknown error'}`, 'error');
  } finally {
    const batchPredictBtn = document.getElementById('batchPredictBtn');
    if (batchPredictBtn) {
      batchPredictBtn.disabled = false;
      batchPredictBtn.innerHTML = '<i class="fas fa-bolt me-1"></i> Batch Predict';
    }
  }
}

// Show prediction result in a modal
function showPredictionResult(result) {
  const modal = document.createElement('div');
  modal.className = 'modal';
  
  const predictedClass = result.predicted_class || 'Unknown';
  const confidence = result.confidence ? (result.confidence * 100).toFixed(1) : 0;
  const probabilities = result.probabilities || {};
  
  // Sort probabilities
  const sortedProbs = Object.entries(probabilities)
    .map(([label, prob]) => ({ label, prob }))
    .sort((a, b) => b.prob - a.prob);
  
  modal.innerHTML = `
    <div class="modal__content" style="max-width: 500px;">
      <div class="modal__head">
        <h3>Prediction Result</h3>
        <button class="btn btn--text" onclick="this.closest('.modal').remove()">×</button>
      </div>
      <div class="modal__body">
        <div class="prediction-result text-center mb-4">
          <div class="prediction-badge mb-3">
            <div class="prediction-class">${predictedClass}</div>
            <div class="prediction-confidence">${confidence}% confidence</div>
          </div>
          
          <div class="progress mb-4" style="height: 24px;">
            <div class="progress-bar bg-success" 
                 role="progressbar" 
                 style="width: ${confidence}%"
                 aria-valuenow="${confidence}" 
                 aria-valuemin="0" 
                 aria-valuemax="100">
              ${confidence}%
            </div>
          </div>
          
          <h5 class="mb-3">Class Probabilities</h5>
          <div class="probability-chart">
            ${sortedProbs.map(item => `
              <div class="probability-row mb-2">
                <div class="d-flex justify-content-between mb-1">
                  <span class="class-name">${item.label}</span>
                  <span class="class-prob">${(item.prob * 100).toFixed(1)}%</span>
                </div>
                <div class="progress" style="height: 10px;">
                  <div class="progress-bar" 
                       role="progressbar" 
                       style="width: ${item.prob * 100}%"
                       aria-valuenow="${item.prob * 100}" 
                       aria-valuemin="0" 
                       aria-valuemax="100">
                  </div>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      </div>
      <div class="modal__foot">
        <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">Close</button>
      </div>
    </div>
  `;
  
  document.body.appendChild(modal);
  
  // Close modal when clicking outside
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.remove();
    }
  });
}

// Show batch prediction results
function showBatchPredictionResults(results) {
  const modal = document.createElement('div');
  modal.className = 'modal';
  
  modal.innerHTML = `
    <div class="modal__content" style="max-width: 800px;">
      <div class="modal__head">
        <h3>Batch Prediction Results</h3>
        <button class="btn btn--text" onclick="this.closest('.modal').remove()">×</button>
      </div>
      <div class="modal__body">
        <div class="table-responsive">
          <table class="table table-hover">
            <thead>
              <tr>
                <th>Sample ID</th>
                <th>Prediction</th>
                <th>Confidence</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody id="batchResultsBody">
              ${results.predictions?.map((pred, idx) => {
                const confidence = pred.confidence ? (pred.confidence * 100).toFixed(1) + '%' : 'N/A';
                return `
                  <tr>
                    <td>#${results.sample_ids?.[idx] || idx + 1}</td>
                    <td>${pred.predicted_class || 'Unknown'}</td>
                    <td>
                      <div class="progress" style="height: 20px;">
                        <div class="progress-bar" 
                             role="progressbar" 
                             style="width: ${pred.confidence * 100}%"
                             aria-valuenow="${pred.confidence * 100}" 
                             aria-valuemin="0" 
                             aria-valuemax="100">
                          ${confidence}
                        </div>
                      </div>
                    </td>
                    <td>
                      <button class="btn btn-sm btn-outline-primary" 
                              onclick="showPredictionDetails(${JSON.stringify(pred).replace(/"/g, '&quot;')})">
                        <i class="fas fa-search"></i> View
                      </button>
                    </td>
                  </tr>
                `;
              }).join('') || '<tr><td colspan="4" class="text-center py-4">No predictions available</td></tr>'}
            </tbody>
          </table>
        </div>
      </div>
      <div class="modal__foot">
        <div class="text-muted small">
          Showing ${results.predictions?.length || 0} predictions
        </div>
        <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">Close</button>
      </div>
    </div>
  `;
  
  document.body.appendChild(modal);
  
  // Close modal when clicking outside
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.remove();
    }
  });
}

// Show detailed prediction view
function showPredictionDetails(prediction) {
  const modal = document.createElement('div');
  modal.className = 'modal';
  
  modal.innerHTML = `
    <div class="modal__content" style="max-width: 600px;">
      <div class="modal__head">
        <h3>Prediction Details</h3>
        <button class="btn btn--text" onclick="this.closest('.modal').remove()">×</button>
      </div>
      <div class="modal__body">
        <div class="card mb-4">
          <div class="card-body">
            <h5 class="card-title">Prediction</h5>
            <div class="d-flex align-items-center mb-3">
              <div class="me-4">
                <div class="prediction-badge">
                  <div class="prediction-class">${prediction.predicted_class || 'Unknown'}</div>
                  <div class="prediction-confidence">${(prediction.confidence * 100).toFixed(1)}% confidence</div>
                </div>
              </div>
              <div class="flex-grow-1">
                <div class="progress" style="height: 24px;">
                  <div class="progress-bar bg-success" 
                       role="progressbar" 
                       style="width: ${prediction.confidence * 100}%"
                       aria-valuenow="${prediction.confidence * 100}" 
                       aria-valuemin="0" 
                       aria-valuemax="100">
                    ${(prediction.confidence * 100).toFixed(1)}%
                  </div>
                </div>
              </div>
            </div>
            
            ${prediction.explanation ? `
              <div class="alert alert-info">
                <h6>Explanation:</h6>
                <p>${prediction.explanation}</p>
              </div>
            ` : ''}
          </div>
        </div>
        
        ${prediction.feature_importances ? `
          <div class="card">
            <div class="card-body">
              <h5 class="card-title">Feature Importance</h5>
              <div class="feature-importance-chart">
                ${Object.entries(prediction.feature_importances)
                  .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
                  .slice(0, 10)
                  .map(([feature, importance]) => {
                    const isPositive = importance >= 0;
                    const width = Math.min(100, Math.abs(importance) * 100);
                    return `
                      <div class="feature-row mb-2">
                        <div class="d-flex justify-content-between mb-1">
                          <span class="feature-name">${feature}</span>
                          <span class="feature-value ${isPositive ? 'text-success' : 'text-danger'}">
                            ${isPositive ? '+' : ''}${importance.toFixed(4)}
                          </span>
                        </div>
                        <div class="progress" style="height: 8px;">
                          <div class="progress-bar ${isPositive ? 'bg-success' : 'bg-danger'}" 
                               role="progressbar" 
                               style="width: ${width}%"
                               aria-valuenow="${width}" 
                               aria-valuemin="0" 
                               aria-valuemax="100">
                          </div>
                        </div>
                      </div>
                    `;
                  }).join('')}
              </div>
            </div>
          </div>
        ` : ''}
      </div>
      <div class="modal__foot">
        <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">Close</button>
      </div>
    </div>
  `;
  
  document.body.appendChild(modal);
  
  // Close modal when clicking outside
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.remove();
    }
  });
}

// Initialize training functionality
function initTraining() {
  // Add ML styles to the head
  const styleLink = document.createElement('link');
  styleLink.rel = 'stylesheet';
  styleLink.href = 'ml-styles.css';
  document.head.appendChild(styleLink);
  
  // Set up event listeners
  setupTrainingEventListeners();
  
  // Initial data load
  refreshTrainingData();
  
  // Initialize model and refresh status
  ensureModelLoaded().then(() => {
    refreshModelInfo();
    
    // Set up periodic refresh of model info (every 30 seconds)
    setInterval(refreshModelInfo, 30000);
  });
  
  // Show tooltips
  const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
  tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });
}

// Helper functions
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast toast--${type}`;
  toast.textContent = message;
  toast.style.cssText = `
    position: fixed;
    bottom: 20px;
    right: 20px;
    padding: 12px 20px;
    border-radius: 4px;
    color: white;
    font-weight: 500;
    z-index: 10000;
    background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
  `;
  
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}
