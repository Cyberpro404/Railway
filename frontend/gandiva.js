/**
 * Project Gandiva - Frontend Controller
 * =====================================
 * 
 * This module handles:
 * - 60-second sliding window graph updates
 * - Real-time sensor polling
 * - Training mode control (sampling)
 * - Alert panel updates
 * 
 * Requires Chart.js for graphing
 */

// =============================================================================
// CONFIGURATION
// =============================================================================

const CONFIG = {
    API_BASE_URL: 'http://localhost:8000',
    POLL_INTERVAL_MS: 1000,         // Poll every 1 second
    WINDOW_SECONDS: 60,             // 60-second sliding window
    GRAPH_UPDATE_INTERVAL: 1000,    // Update graph every second
};

// Label info (must match backend)
const LABEL_INFO = {
    idle: {
        display: 'IDLE',
        message: 'Train is idle',
        severity: 'idle',
        color: '#64748b',       // gray
        bgColor: '#f1f5f9',
        action: null
    },
    normal: {
        display: 'NORMAL',
        message: 'No issues detected',
        severity: 'ok',
        color: '#22c55e',       // green
        bgColor: '#dcfce7',
        action: null
    },
    expansion_gap: {
        display: 'EXPANSION GAP',
        message: 'Intentional gap - no action needed',
        severity: 'info',
        color: '#3b82f6',       // blue
        bgColor: '#dbeafe',
        action: null
    },
    crack: {
        display: 'CRACK DETECTED',
        message: 'Potential crack - inspect immediately!',
        severity: 'critical',
        color: '#ef4444',       // red
        bgColor: '#fee2e2',
        action: 'inspect'
    },
    other_fault: {
        display: 'FAULT DETECTED',
        message: 'Unknown fault type - investigate',
        severity: 'warning',
        color: '#f97316',       // orange
        bgColor: '#ffedd5',
        action: 'investigate'
    }
};


// =============================================================================
// STATE
// =============================================================================

const state = {
    // Sample data (sliding window)
    samples: [],
    
    // Latest data
    latestReading: null,
    latestPrediction: null,
    
    // Polling
    pollInterval: null,
    isPolling: false,
    
    // Sampling mode
    isSampling: false,
    samplingLabel: null,
    samplesCollected: 0,
    
    // Model
    modelLoaded: false,
    
    // Chart instance
    chart: null
};


// =============================================================================
// API FUNCTIONS
// =============================================================================

/**
 * Fetch wrapper with error handling
 */
async function apiFetch(endpoint, options = {}) {
    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}${endpoint}`, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error(`API Error (${endpoint}):`, error);
        throw error;
    }
}

/**
 * Get system status
 */
async function getStatus() {
    return apiFetch('/status');
}

/**
 * Get live sample (sensor reading + prediction)
 */
async function getLiveSample() {
    return apiFetch('/api/live_sample');
}

/**
 * Get sample history for graph initialization
 */
async function getHistory(seconds = 60) {
    return apiFetch(`/api/history?seconds=${seconds}`);
}

/**
 * Start training data collection
 */
async function startSampling(label) {
    return apiFetch('/start_sampling', {
        method: 'POST',
        body: JSON.stringify({ label })
    });
}

/**
 * Stop training data collection
 */
async function stopSampling() {
    return apiFetch('/stop_sampling', {
        method: 'POST'
    });
}

/**
 * Train the model
 */
async function trainModel() {
    return apiFetch('/train', {
        method: 'POST'
    });
}

/**
 * Manual prediction
 */
async function predict(features) {
    return apiFetch('/predict', {
        method: 'POST',
        body: JSON.stringify(features)
    });
}

/**
 * Set simulation mode (for testing)
 */
async function setSimulationMode(mode) {
    return apiFetch('/simulation/mode', {
        method: 'POST',
        body: JSON.stringify({ mode })
    });
}


// =============================================================================
// SLIDING WINDOW MANAGEMENT
// =============================================================================

/**
 * Add a new sample to the sliding window
 */
function addSample(sample) {
    state.samples.push(sample);
    
    // Keep only last WINDOW_SECONDS samples
    while (state.samples.length > CONFIG.WINDOW_SECONDS) {
        state.samples.shift();
    }
}

/**
 * Get data arrays for graphing
 */
function getGraphData() {
    const timestamps = [];
    const rmsValues = [];
    const peakValues = [];
    const band1xValues = [];
    const band2xValues = [];
    const band3xValues = [];
    const band5xValues = [];
    const band7xValues = [];
    
    state.samples.forEach((sample, index) => {
        const reading = sample.reading || {};
        
        // Use relative time (seconds ago)
        timestamps.push(index - state.samples.length + 1);
        
        rmsValues.push(reading.rms || 0);
        peakValues.push(reading.peak || 0);
        band1xValues.push(reading.band_1x || 0);
        band2xValues.push(reading.band_2x || 0);
        band3xValues.push(reading.band_3x || 0);
        band5xValues.push(reading.band_5x || 0);
        band7xValues.push(reading.band_7x || 0);
    });
    
    return {
        timestamps,
        rms: rmsValues,
        peak: peakValues,
        band_1x: band1xValues,
        band_2x: band2xValues,
        band_3x: band3xValues,
        band_5x: band5xValues,
        band_7x: band7xValues
    };
}


// =============================================================================
// POLLING
// =============================================================================

/**
 * Poll for new data
 */
async function pollSensor() {
    try {
        const data = await getLiveSample();
        
        // Update state
        state.latestReading = data.reading;
        state.latestPrediction = data.prediction;
        state.isSampling = data.sampling?.active || false;
        state.samplingLabel = data.sampling?.label;
        state.samplesCollected = data.sampling?.count || 0;
        state.modelLoaded = data.model_loaded;
        
        // Add to sliding window
        addSample({
            timestamp: data.timestamp,
            reading: data.reading,
            prediction: data.prediction
        });
        
        // Update UI
        updateUI();
        
    } catch (error) {
        console.error('Polling error:', error);
        updateConnectionStatus(false, error.message);
    }
}

/**
 * Start polling
 */
function startPolling() {
    if (state.isPolling) return;
    
    state.isPolling = true;
    state.pollInterval = setInterval(pollSensor, CONFIG.POLL_INTERVAL_MS);
    
    // Initial poll
    pollSensor();
    
    console.log('Polling started');
}

/**
 * Stop polling
 */
function stopPolling() {
    if (state.pollInterval) {
        clearInterval(state.pollInterval);
        state.pollInterval = null;
    }
    state.isPolling = false;
    console.log('Polling stopped');
}


// =============================================================================
// UI UPDATE FUNCTIONS
// =============================================================================

/**
 * Main UI update function
 */
function updateUI() {
    updateReadingDisplay();
    updatePredictionDisplay();
    updateSamplingDisplay();
    updateChart();
}

/**
 * Update sensor reading display
 */
function updateReadingDisplay() {
    const reading = state.latestReading;
    if (!reading) return;
    
    // Update value displays (if elements exist)
    setElementText('rms-value', reading.rms?.toFixed(2) || '--');
    setElementText('peak-value', reading.peak?.toFixed(3) || '--');
    setElementText('temp-value', reading.temperature?.toFixed(1) || '--');
    setElementText('freq-value', reading.frequency?.toFixed(1) || '--');
    
    // Band values
    setElementText('band-1x-value', reading.band_1x?.toFixed(2) || '--');
    setElementText('band-2x-value', reading.band_2x?.toFixed(2) || '--');
    setElementText('band-3x-value', reading.band_3x?.toFixed(2) || '--');
    setElementText('band-5x-value', reading.band_5x?.toFixed(2) || '--');
    setElementText('band-7x-value', reading.band_7x?.toFixed(2) || '--');
    
    // Sensor status
    const statusEl = document.getElementById('sensor-status');
    if (statusEl) {
        if (reading.status_ok) {
            statusEl.textContent = 'OK';
            statusEl.className = 'status-ok';
        } else {
            statusEl.textContent = reading.error || 'ERROR';
            statusEl.className = 'status-error';
        }
    }
}

/**
 * Update prediction/alert display
 */
function updatePredictionDisplay() {
    const prediction = state.latestPrediction;
    const alertPanel = document.getElementById('alert-panel');
    const alertLabel = document.getElementById('alert-label');
    const alertMessage = document.getElementById('alert-message');
    const alertConfidence = document.getElementById('alert-confidence');
    
    if (!alertPanel) return;
    
    if (!state.modelLoaded) {
        // Model not loaded
        alertPanel.className = 'alert-panel alert-no-model';
        alertPanel.style.backgroundColor = '#f3f4f6';
        if (alertLabel) alertLabel.textContent = 'MODEL NOT LOADED';
        if (alertMessage) alertMessage.textContent = 'Train the model to enable predictions';
        if (alertConfidence) alertConfidence.textContent = '';
        return;
    }
    
    if (!prediction) {
        alertPanel.className = 'alert-panel';
        alertPanel.style.backgroundColor = '#f3f4f6';
        if (alertLabel) alertLabel.textContent = 'WAITING...';
        if (alertMessage) alertMessage.textContent = 'Waiting for prediction';
        if (alertConfidence) alertConfidence.textContent = '';
        return;
    }

    // Custom logic for exclusive display
    let labelToShow = prediction.label;
    if (labelToShow === 'idle') {
        // If idle, all boxes/indicators should show IDLE
        // (handled by using LABEL_INFO.idle everywhere)
    } else if (labelToShow === 'crack') {
        // Only crack detected box appears, others hidden/normal
        // (handled by using LABEL_INFO.crack)
    } else if (labelToShow === 'expansion_gap') {
        // Only expansion signal appears, others hidden/normal
        // (handled by using LABEL_INFO.expansion_gap)
    } else if (labelToShow === 'normal') {
        // Everything should be normal
        // (handled by using LABEL_INFO.normal)
    }
    const info = LABEL_INFO[labelToShow] || LABEL_INFO.other_fault;

    // Update panel
    alertPanel.className = `alert-panel alert-${info.severity}`;
    alertPanel.style.backgroundColor = info.bgColor;
    alertPanel.style.borderColor = info.color;

    if (alertLabel) {
        alertLabel.textContent = info.display;
        alertLabel.style.color = info.color;
    }

    if (alertMessage) {
        alertMessage.textContent = info.message;
    }

    if (alertConfidence) {
        alertConfidence.textContent = prediction.confidence !== undefined ? `Confidence: ${(prediction.confidence * 100).toFixed(1)}%` : '';
    }

    // Update probability bars if they exist
    updateProbabilityBars(prediction.probabilities);
}

/**
 * Update probability bar display
 */
function updateProbabilityBars(probabilities) {
    if (!probabilities) return;
    
    Object.entries(probabilities).forEach(([label, prob]) => {
        const barEl = document.getElementById(`prob-bar-${label}`);
        const valueEl = document.getElementById(`prob-value-${label}`);
        
        if (barEl) {
            barEl.style.width = `${prob * 100}%`;
            const info = LABEL_INFO[label];
            if (info) barEl.style.backgroundColor = info.color;
        }
        
        if (valueEl) {
            valueEl.textContent = `${(prob * 100).toFixed(1)}%`;
        }
    });
}

/**
 * Update sampling mode display
 */
function updateSamplingDisplay() {
    const statusEl = document.getElementById('sampling-status');
    const labelEl = document.getElementById('sampling-label');
    const countEl = document.getElementById('sampling-count');
    const indicator = document.getElementById('sampling-indicator');
    
    if (statusEl) {
        statusEl.textContent = state.isSampling ? 'RECORDING' : 'IDLE';
        statusEl.className = state.isSampling ? 'sampling-active' : 'sampling-idle';
    }
    
    if (labelEl) {
        labelEl.textContent = state.samplingLabel || '--';
    }
    
    if (countEl) {
        countEl.textContent = state.samplesCollected;
    }
    
    if (indicator) {
        indicator.style.display = state.isSampling ? 'inline-block' : 'none';
    }
    
    // Update button states
    const startBtns = document.querySelectorAll('.btn-start-sampling');
    const stopBtn = document.getElementById('btn-stop-sampling');
    
    startBtns.forEach(btn => {
        btn.disabled = state.isSampling;
    });
    
    if (stopBtn) {
        stopBtn.disabled = !state.isSampling;
    }
}

/**
 * Update connection status display
 */
function updateConnectionStatus(connected, errorMessage = null) {
    const statusEl = document.getElementById('connection-status');
    if (statusEl) {
        if (connected) {
            statusEl.textContent = 'Connected';
            statusEl.className = 'status-connected';
        } else {
            statusEl.textContent = errorMessage || 'Disconnected';
            statusEl.className = 'status-disconnected';
        }
    }
}

/**
 * Helper: Set element text content
 */
function setElementText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}


// =============================================================================
// CHART (using Chart.js)
// =============================================================================

/**
 * Initialize the chart
 */
function initChart(canvasId = 'vibration-chart') {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.warn('Chart canvas not found:', canvasId);
        return;
    }
    
    // Check for Chart.js
    if (typeof Chart === 'undefined') {
        console.warn('Chart.js not loaded');
        return;
    }
    
    const ctx = canvas.getContext('2d');
    
    state.chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'RMS Velocity (mm/s)',
                    data: [],
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 0
                },
                {
                    label: 'Peak Acceleration (g)',
                    data: [],
                    borderColor: '#ef4444',
                    backgroundColor: 'transparent',
                    tension: 0.3,
                    pointRadius: 0
                },
                {
                    label: 'Band 1X',
                    data: [],
                    borderColor: '#22c55e',
                    backgroundColor: 'transparent',
                    tension: 0.3,
                    pointRadius: 0,
                    hidden: true
                },
                {
                    label: 'Band 2X',
                    data: [],
                    borderColor: '#f59e0b',
                    backgroundColor: 'transparent',
                    tension: 0.3,
                    pointRadius: 0,
                    hidden: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 0  // Disable animation for real-time updates
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Time (seconds)'
                    },
                    min: -60,
                    max: 0
                },
                y: {
                    title: {
                        display: true,
                        text: 'Value'
                    },
                    beginAtZero: true
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                    onClick: (e, legendItem, legend) => {
                        // Default toggle behavior
                        const index = legendItem.datasetIndex;
                        const ci = legend.chart;
                        if (ci.isDatasetVisible(index)) {
                            ci.hide(index);
                            legendItem.hidden = true;
                        } else {
                            ci.show(index);
                            legendItem.hidden = false;
                        }
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        }
    });
}

/**
 * Update chart with current data
 */
function updateChart() {
    if (!state.chart) return;
    
    const data = getGraphData();
    
    state.chart.data.labels = data.timestamps;
    state.chart.data.datasets[0].data = data.rms;
    state.chart.data.datasets[1].data = data.peak;
    state.chart.data.datasets[2].data = data.band_1x;
    state.chart.data.datasets[3].data = data.band_2x;
    
    state.chart.update('none');  // 'none' skips animation
}


// =============================================================================
// EVENT HANDLERS
// =============================================================================

/**
 * Handle start sampling button click
 */
async function handleStartSampling(label) {
    try {
        showLoading('Starting sampling...');
        const result = await startSampling(label);
        showMessage(`Sampling started for '${label}'`, 'success');
        console.log('Start sampling result:', result);
    } catch (error) {
        showMessage(`Failed to start sampling: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

/**
 * Handle stop sampling button click
 */
async function handleStopSampling() {
    try {
        showLoading('Stopping sampling...');
        const result = await stopSampling();
        showMessage(`Sampling stopped. Collected ${result.samples_collected} samples.`, 'success');
        console.log('Stop sampling result:', result);
    } catch (error) {
        showMessage(`Failed to stop sampling: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

/**
 * Handle train model button click
 */
async function handleTrainModel() {
    try {
        showLoading('Training model... This may take a moment.');
        const result = await trainModel();
        
        if (result.success) {
            showMessage(
                `Model trained successfully! Accuracy: ${(result.accuracy * 100).toFixed(1)}%`,
                'success'
            );
            state.modelLoaded = true;
        } else {
            showMessage(`Training failed: ${result.error}`, 'error');
        }
        
        console.log('Training result:', result);
    } catch (error) {
        showMessage(`Training failed: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

/**
 * Handle simulation mode change
 */
async function handleSetSimulationMode(mode) {
    try {
        await setSimulationMode(mode);
        showMessage(`Simulation mode set to: ${mode}`, 'info');
    } catch (error) {
        showMessage(`Failed to set simulation mode: ${error.message}`, 'error');
    }
}


// =============================================================================
// UI HELPERS
// =============================================================================

function showMessage(message, type = 'info') {
    console.log(`[${type.toUpperCase()}] ${message}`);
    
    // Show toast notification if element exists
    const toast = document.getElementById('toast');
    if (toast) {
        toast.textContent = message;
        toast.className = `toast toast-${type} show`;
        setTimeout(() => {
            toast.className = 'toast';
        }, 3000);
    }
    
    // Or use alert as fallback for important messages
    if (type === 'error') {
        // Could show a modal or more prominent notification
    }
}

function showLoading(message = 'Loading...') {
    const loader = document.getElementById('loading-overlay');
    const loaderText = document.getElementById('loading-text');
    
    if (loader) {
        loader.style.display = 'flex';
    }
    if (loaderText) {
        loaderText.textContent = message;
    }
}

function hideLoading() {
    const loader = document.getElementById('loading-overlay');
    if (loader) {
        loader.style.display = 'none';
    }
}


// =============================================================================
// INITIALIZATION
// =============================================================================

/**
 * Initialize the application
 */
async function initApp() {
    console.log('Initializing Project Gandiva...');
    
    try {
        // Get initial status
        const status = await getStatus();
        console.log('System status:', status);
        
        state.modelLoaded = status.model?.loaded || false;
        
        // Load history to populate graph
        const history = await getHistory(CONFIG.WINDOW_SECONDS);
        if (history.samples) {
            state.samples = history.samples;
        }
        
        // Initialize chart
        initChart();
        
        // Start polling
        startPolling();
        
        // Update UI
        updateConnectionStatus(true);
        updateUI();
        
        console.log('Initialization complete');
        
    } catch (error) {
        console.error('Initialization failed:', error);
        updateConnectionStatus(false, error.message);
    }
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Sampling buttons
    document.querySelectorAll('.btn-start-sampling').forEach(btn => {
        btn.addEventListener('click', () => {
            const label = btn.dataset.label;
            if (label) handleStartSampling(label);
        });
    });
    
    // Stop sampling button
    const stopBtn = document.getElementById('btn-stop-sampling');
    if (stopBtn) {
        stopBtn.addEventListener('click', handleStopSampling);
    }
    
    // Train button
    const trainBtn = document.getElementById('btn-train-model');
    if (trainBtn) {
        trainBtn.addEventListener('click', handleTrainModel);
    }
    
    // Simulation mode buttons (for testing)
    document.querySelectorAll('.btn-sim-mode').forEach(btn => {
        btn.addEventListener('click', () => {
            const mode = btn.dataset.mode;
            if (mode) handleSetSimulationMode(mode);
        });
    });
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        setupEventListeners();
        initApp();
    });
} else {
    setupEventListeners();
    initApp();
}


// =============================================================================
// EXPORTS (for module usage)
// =============================================================================

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        // API functions
        getStatus,
        getLiveSample,
        getHistory,
        startSampling,
        stopSampling,
        trainModel,
        predict,
        setSimulationMode,
        
        // State
        state,
        
        // Control functions
        startPolling,
        stopPolling,
        initApp,
        
        // Config
        CONFIG,
        LABEL_INFO
    };
}
