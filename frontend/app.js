console.log('[GANDIVA] app.js loading...');

// Error handling state
let lastError = null;
let lastErrorTime = null;
let consecutiveErrors = 0;
const MAX_CONSECUTIVE_ERRORS = 5;

// Enhanced API functions with error handling
async function apiGetWithErrorHandling(url){
  try {
    const response = await fetch(API(url), { method: 'GET', headers: { 'Accept': 'application/json' } });
    if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    if (response.status === 204) {
      // No content available
      consecutiveErrors = 0;
      return null;
    }
    const data = await response.json();
    consecutiveErrors = 0;
    return data;
  } catch (error) {
    consecutiveErrors++;
    lastError = error.message || 'Unknown error';
    lastErrorTime = new Date().toISOString();
    throw error;
  }
}

async function apiPostWithErrorHandling(url, body){
  try {
    const response = await fetch(API(url), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: JSON.stringify(body)
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    const data = await response.json();
    consecutiveErrors = 0;
    return data;
  } catch (error) {
    consecutiveErrors++;
    lastError = error.message || 'Unknown error';
    lastErrorTime = new Date().toISOString();
    throw error;
  }
}

function showErrorBanner(message, showRetry = false){
  const banner = qs('errorBanner');
  if (!banner) return;
  
  banner.innerHTML = `
    <div class="banner banner--error">
      <div class="banner__content">
        <strong>Sensor Error:</strong> ${message}
        ${showRetry ? '<button class="btn btn--small btn--secondary" onclick="refreshLatest()">Retry</button>' : ''}
        <button class="btn btn--small btn--text" onclick="hideErrorBanner()">×</button>
      </div>
    </div>
  `;
  banner.style.display = 'block';
}

function hideErrorBanner(){
  const banner = qs('errorBanner');
  if (banner) banner.style.display = 'none';
}

function updateConnectionStatus(){
  const statusEl = qs('connectionStatus');
  if (!statusEl) return;
  
  if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
    statusEl.innerHTML = '<span class="status status--error">Disconnected</span>';
  } else if (lastError) {
    statusEl.innerHTML = '<span class="status status--warning">Intermittent errors</span>';
  } else {
    statusEl.innerHTML = '<span class="status status--ok">Connected</span>';
  }
}

const API = (p) => `${location.origin}${p}`;

let thresholds = null;
let connection = null;
let latest = null;
let alerts = [];

let selectedAxis = 'z';
let selectedBand = null;

let selectedHealthParam = 'z_rms_mm_s';
let selectedAxisHealth = 'z';
let selectedHealthBand = null;

let logsPage = 1;
const LOGS_PAGE_SIZE = 25;
let logsRows = [];

// ML status cache
let mlStatus = null;

const ALPHA = 0.4;
function smooth(previous, current){
  if (previous == null) return current;
  return ALPHA * current + (1 - ALPHA) * previous;
}
const _smoothState = {
  z: null,
  x: null,
  t: null,
  band: null,
  health: null,
  healthBandTotal: null,
  healthBandPeak: null,
  healthBandFreq: null,
};

let activeTab = 'connection';
let _lastHealthTs = null;

const history = {
  labels: [],
  z: [],
  x: [],
  t: [],
  band: []
};

function qs(id){return document.getElementById(id)}

const BAND_LABELS = [
  { band_number: 1,  multiple: 1,  name: '1× – Fundamental speed band' },
  { band_number: 2,  multiple: 2,  name: '2× – Second harmonic' },
  { band_number: 3,  multiple: 3,  name: '3× – Third harmonic' },
  { band_number: 4,  multiple: 4,  name: '4× – Fourth harmonic' },
  { band_number: 5,  multiple: 5,  name: '5× – Fifth harmonic' },
  { band_number: 6,  multiple: 6,  name: '6× – Sixth harmonic' },
  { band_number: 7,  multiple: 7,  name: '7× – Seventh harmonic' },
  { band_number: 8,  multiple: 8,  name: '8× – Eighth harmonic' },
  { band_number: 9,  multiple: 9,  name: '9× – Ninth harmonic' },
  { band_number: 10, multiple: 10, name: '10× – Tenth harmonic' },
  { band_number: 11, multiple: 11, name: '11× – Harmonic' },
  { band_number: 12, multiple: 12, name: '12× – Harmonic' },
  { band_number: 13, multiple: 13, name: '13× – Harmonic' },
  { band_number: 14, multiple: 14, name: '14× – Harmonic' },
  { band_number: 15, multiple: 15, name: '15× – Harmonic' },
  { band_number: 16, multiple: 16, name: '16× – Harmonic' },
  { band_number: 17, multiple: 17, name: '17× – Harmonic' },
  { band_number: 18, multiple: 18, name: '18× – Harmonic' },
  { band_number: 19, multiple: 19, name: '19× – Harmonic' },
  { band_number: 20, multiple: 20, name: '20× – Harmonic' },
];

function bandLabelForNumber(n){
  return BAND_LABELS.find(x => x.band_number === Number(n)) || null;
}

function bandMultiple(b){
  const m = Number(b?.multiple);
  if (Number.isFinite(m) && m > 0) return m;
  return Number(b?.band_number) || 0;
}

function axisLabel(axis){
  return axis === 'z' ? 'Z' : 'X';
}

function _bandPrimaryText(b){
  const n = Number(b.band_number);
  const mul = bandMultiple(b);
  return `Band ${n} – ${mul}×`;
}

function _bandSecondaryText(b){
  const n = Number(b.band_number);
  const label = bandLabelForNumber(n);
  if (!label) return `${bandMultiple(b)}× – Harmonic`;
  const parts = String(label.name).split('–');
  return parts.length > 1 ? parts[1].trim() : label.name;
}

function _bandFriendlyName(b){
  const n = Number(b.band_number);
  const label = bandLabelForNumber(n);
  return label ? label.name : `${bandMultiple(b)}× – Harmonic`;
}

function getBandsFromReading(r, axis){
  if (!r) return [];
  if (axis === 'z') return (r.bands_z ?? []);
  return (r.bands_x ?? []);
}

function _firstBandNumber(bands){
  if (!bands || !bands.length) return null;
  const n = Number(bands[0].band_number);
  return Number.isFinite(n) ? n : null;
}

function syncBandSelectionFromLatest(){
  if (!latest) return;

  // Ensure overview axis defaults to Z where possible and pick a sensible selectedBand
  let bandsOverview = getBandsFromReading(latest, selectedAxis);
  if (!bandsOverview.length){
    const zBands = getBandsFromReading(latest, 'z');
    const xBands = getBandsFromReading(latest, 'x');
    if (zBands.length){
      selectedAxis = 'z';
      bandsOverview = zBands;
    }else if (xBands.length){
      selectedAxis = 'x';
      bandsOverview = xBands;
    }else{
      selectedBand = null;
    }
  }

  if (bandsOverview.length){
    const exists = selectedBand != null && bandsOverview.some(b => Number(b.band_number) === Number(selectedBand));
    if (!exists){
      selectedBand = Number(bandsOverview[0].band_number);
    }
  }

  const bandsHealth = getBandsFromReading(latest, selectedAxisHealth);
  if (!bandsHealth.length){
    selectedHealthBand = null;
  }else{
    const exists = selectedHealthBand != null && bandsHealth.some(b => Number(b.band_number) === Number(selectedHealthBand));
    if (!exists){
      selectedHealthBand = Number(bandsHealth[0].band_number);
    }
  }

  // Keep the axis toggle buttons in sync when we auto-select an axis
  qs('axisZ')?.classList.toggle('is-active', selectedAxis === 'z');
  qs('axisX')?.classList.toggle('is-active', selectedAxis === 'x');
}

function setOverviewAxis(axis){
  selectedAxis = axis;
  qs('axisZ')?.classList.toggle('is-active', axis === 'z');
  qs('axisX')?.classList.toggle('is-active', axis === 'x');

  if (latest){
    const bands = getBandsFromReading(latest, selectedAxis);
    selectedBand = bands.length ? Number(bands[0].band_number) : null;
  }else{
    selectedBand = null;
  }

  renderBandList();
  renderBandDetail();
  renderFrequencySnapshot();
}

let chartSpectrum;
let chartBandRms, chartBandFreq, chartAllBandsRms;
function initSpectrumChart(){
  const el = qs('chartSpectrum');
  if (!el) return;

  chartSpectrum = new Chart(el, {
    type: 'scatter',
    data: {
      datasets: [
        {
          label: 'Bands',
          data: [],
          pointRadius: 5,
          pointHoverRadius: 7,
          borderColor: 'rgba(0,0,0,0)',
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 0 },
      parsing: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const p = ctx.raw;
              if (!p) return '';
              return `Band ${p.band_number} · ${p.axis.toUpperCase()} · ${p.multiple}× | ${p.x.toFixed(2)} Hz | ${p.y.toFixed(3)} | ${p.status}`;
            }
          }
        }
      },
      scales: {
        x: {
          type: 'linear',
          title: { display: true, text: 'Peak Frequency (Hz)', color: 'rgba(232,237,247,.65)' },
          ticks: { color: 'rgba(232,237,247,.55)' },
          grid: { color: 'rgba(255,255,255,.06)' }
        },
        y: {
          title: { display: true, text: 'Amplitude', color: 'rgba(232,237,247,.65)' },
          ticks: { color: 'rgba(232,237,247,.55)' },
          grid: { color: 'rgba(255,255,255,.06)' }
        }
      },
      onClick: (_evt, active) => {
        if (!active || !active.length) return;
        const idx = active[0].index;
        const p = chartSpectrum.data.datasets[0].data[idx];
        if (!p) return;
        selectedHealthBand = Number(p.band_number);
        setHealthAxis(p.axis);

        selectedAxis = selectedAxisHealth;
        selectedBand = selectedHealthBand;
        renderBandList();
        renderBandDetail();

        renderHealthBandsTable();
        renderHealthBandSelector();
        renderHealthBandMetrics();
        renderAllBandsSnapshot();
        renderSpectrum();
        refreshHealthHistory();
      }
    }
  });
}

function initBandAnalysisCharts(){
  const base = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 0 },
    plugins: { legend: { labels: { color: 'rgba(232,237,247,.8)' } } },
    scales: {
      x: { ticks: { color: 'rgba(232,237,247,.55)' }, grid: { color: 'rgba(255,255,255,.06)' } },
      y: { ticks: { color: 'rgba(232,237,247,.55)' }, grid: { color: 'rgba(255,255,255,.06)' } }
    }
  };

  const elRms = qs('chartBandRms');
  if (elRms){
    chartBandRms = new Chart(elRms, {
      type: 'line',
      data: {
        labels: [],
        datasets: [
          { label: 'Total RMS', data: [], borderColor: '#21c7b7', tension: .25, pointRadius: 0 },
          { label: 'Peak RMS', data: [], borderColor: '#a78bfa', tension: .25, pointRadius: 0 },
        ]
      },
      options: base
    });
  }

  const elFreq = qs('chartBandFreq');
  if (elFreq){
    chartBandFreq = new Chart(elFreq, {
      type: 'line',
      data: {
        labels: [],
        datasets: [
          { label: 'Peak Frequency (Hz)', data: [], borderColor: '#6ea8fe', tension: .25, pointRadius: 0 },
        ]
      },
      options: base
    });
  }

  const elAll = qs('chartAllBandsRms');
  if (elAll){
    chartAllBandsRms = new Chart(elAll, {
      type: 'bar',
      data: {
        labels: [],
        datasets: [
          { label: 'Total RMS', data: [], backgroundColor: [], borderWidth: 0 }
        ]
      },
      options: {
        ...base,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => {
                const n = ctx.label;
                const v = Number(ctx.raw ?? 0);
                return `Band ${n} · Total RMS ${v.toFixed(3)}`;
              }
            }
          }
        },
        onClick: (_evt, active) => {
          if (!active || !active.length) return;
          const idx = active[0].index;
          const n = Number(chartAllBandsRms.data.labels[idx]);
          if (!Number.isFinite(n)) return;

          selectedHealthBand = n;
          selectedAxis = selectedAxisHealth;
          selectedBand = n;

          renderHealthBandsTable();
          renderHealthBandSelector();
          renderHealthBandMetrics();
          renderAllBandsSnapshot();
          renderSpectrum();
          refreshHealthHistory();

          renderBandList();
          renderBandDetail();
        }
      }
    });
  }
}

function setHealthAxis(axis){
  selectedAxisHealth = axis;
  qs('healthAxisZ')?.classList.toggle('is-active', axis === 'z');
  qs('healthAxisX')?.classList.toggle('is-active', axis === 'x');
  qs('spectrumAxisZ')?.classList.toggle('is-active', axis === 'z');
  qs('spectrumAxisX')?.classList.toggle('is-active', axis === 'x');
  qs('bandAxisZ')?.classList.toggle('is-active', axis === 'z');
  qs('bandAxisX')?.classList.toggle('is-active', axis === 'x');
  if (latest){
    const bands = getBandsFromReading(latest, selectedAxisHealth);
    selectedHealthBand = bands.length ? Number(bands[0].band_number) : null;
  }else{
    selectedHealthBand = null;
  }

  renderHealthBandsTable();
  renderHealthBandSelector();
  renderHealthBandMetrics();
  renderAllBandsSnapshot();
  renderSpectrum();
  refreshHealthHistory();
}

function renderHealthBandSelector(){
  const sel = qs('healthBandNum');
  if (!sel) return;
  if (!latest){
    sel.innerHTML = '';
    sel.disabled = true;
    return;
  }
  const bands = getBandsFromReading(latest, selectedAxisHealth);
  sel.innerHTML = '';

  if (!bands.length){
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = 'No band data for this axis';
    sel.appendChild(opt);
    sel.disabled = true;
    return;
  }

  sel.disabled = false;
  const nums = [...new Set(bands.map(b => Number(b.band_number)).filter(n => Number.isFinite(n)))].sort((a,b)=>a-b);
  for (const n of nums){
    const opt = document.createElement('option');
    opt.value = String(n);
    opt.textContent = `Band ${n}`;
    sel.appendChild(opt);
  }

  if (selectedHealthBand == null || !nums.includes(Number(selectedHealthBand))){
    selectedHealthBand = nums[0];
  }
  sel.value = String(selectedHealthBand ?? '');
}

function renderHealthBandMetrics(){
  const wrap = qs('healthBandMetrics');
  if (!wrap || !latest) return;
  wrap.innerHTML = '';

  const bands = getBandsFromReading(latest, selectedAxisHealth);
  if (!bands.length){
    wrap.innerHTML = '<div class="note">No band data available for this axis. Check sensor configuration.</div>';
    renderHealthBandName();
    return;
  }

  if (selectedHealthBand == null){
    wrap.innerHTML = '<div class="note">Select a band to inspect.</div>';
    renderHealthBandName();
    return;
  }

  const b = bands.find(x => Number(x.band_number) === Number(selectedHealthBand));
  if (!b){
    wrap.innerHTML = '<div class="note">Select a band to inspect.</div>';
    renderHealthBandName();
    return;
  }

  renderHealthBandName();

  const level = levelForBand(selectedAxisHealth, Number(b.band_number), 'total_rms', Number(b.total_rms));
  const items = [
    { label: 'Total RMS', v: fmt(b.total_rms, 3) },
    { label: 'Peak RMS', v: fmt(b.peak_rms, 3) },
    { label: 'Peak Hz', v: fmt(b.peak_freq_hz, 2) },
    { label: 'Peak RPM', v: fmt(b.peak_rpm, 1) },
    { label: 'Bin', v: String(b.bin_index ?? '—') },
  ];

  for (const it of items){
    const el = document.createElement('div');
    el.className = 'bandCard';
    el.innerHTML = `<div class="bandCard__k">${it.label}</div><div class="bandCard__v">${it.v}</div>`;
    wrap.appendChild(el);
  }

  const head = document.createElement('div');
  head.className = 'note';
  head.style.marginTop = '10px';
  head.textContent = `Band ${b.band_number} · ${selectedAxisHealth.toUpperCase()} · ${(b.multiple || b.band_number)}× · ${level.toUpperCase()}`;
  wrap.appendChild(head);
}

function renderAllBandsSnapshot(){
  if (!chartAllBandsRms || !latest) return;
  const bands = getBandsFromReading(latest, selectedAxisHealth);
  if (!bands.length){
    chartAllBandsRms.data.labels = [];
    chartAllBandsRms.data.datasets[0].data = [];
    chartAllBandsRms.data.datasets[0].backgroundColor = [];
    chartAllBandsRms.update('none');
    return;
  }

  const nums = bands.map(b => Number(b.band_number)).filter(n => Number.isFinite(n)).sort((a,b)=>a-b);
  const data = [];
  const colors = [];
  for (const n of nums){
    const b = bands.find(x => Number(x.band_number) === n);
    const v = b ? Number(b.total_rms ?? 0) : 0;
    const status = levelForBand(selectedAxisHealth, n, 'total_rms', Number(b?.total_rms));
    data.push(v);
    colors.push(_colorForLevel(status));
  }

  chartAllBandsRms.data.labels = nums.map(String);
  chartAllBandsRms.data.datasets[0].data = data;
  chartAllBandsRms.data.datasets[0].backgroundColor = colors;
  chartAllBandsRms.update('none');
}
function fmt(n, d=3){
  if (n === null || n === undefined || Number.isNaN(Number(n))) return '—';
  return Number(n).toFixed(d);
}

function clockTick(){
  const now = new Date();
  qs('clock').textContent = now.toLocaleString();
}
setInterval(clockTick, 500);
clockTick();

function setActiveTab(name){
  activeTab = name;
  document.querySelectorAll('.nav__item').forEach(b => b.classList.toggle('is-active', b.dataset.tab === name));
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('is-active', t.id === `tab-${name}`));
  qs('pageTitle').textContent = name.charAt(0).toUpperCase() + name.slice(1);

  if (document.body.classList.contains('nav-open')){
    document.body.classList.remove('nav-open');
  }

  if (latest){
    if (name === 'overview'){
      updateKpis();
      renderParamGrid();
      renderBandList();
      renderBandDetail();
      renderFrequencySnapshot();
      updateCharts();
    }
    if (name === 'health'){
      renderHealthParamGrid();
      renderHealthDetailFromLatest();
      renderHealthBandsTable();
      renderHealthBandSelector();
      renderHealthBandMetrics();
      renderAllBandsSnapshot();
      renderSpectrum();
      refreshHealthHistory();
    }
    if (name === 'system'){
      renderSystemInfo();
    }
    if (name === 'mlinsights'){
      refreshMLInsights();
    }
    if (name === 'datasets'){
      refreshDatasets();
    }
  }
}

document.querySelectorAll('.nav__item').forEach(b => {
  b.addEventListener('click', () => setActiveTab(b.dataset.tab));
});

function setupMobileNav(){
  const toggle = qs('navToggle');
  const backdrop = qs('sidebarBackdrop');

  if (toggle){
    toggle.addEventListener('click', () => {
      document.body.classList.toggle('nav-open');
    });
  }

  if (backdrop){
    backdrop.addEventListener('click', () => {
      document.body.classList.remove('nav-open');
    });
  }
}

function levelForScalar(param, value){
  if (!thresholds) return 'normal';
  if (param === 'z_rms_mm_s'){
    if (value >= thresholds.z_rms_mm_s_alarm) return 'alarm';
    if (value >= thresholds.z_rms_mm_s_warning) return 'warning';
  }
  if (param === 'x_rms_mm_s'){
    if (value >= thresholds.x_rms_mm_s_alarm) return 'alarm';
    if (value >= thresholds.x_rms_mm_s_warning) return 'warning';
  }
  if (param === 'temp_c'){
    if (value >= thresholds.temp_c_alarm) return 'alarm';
    if (value >= thresholds.temp_c_warning) return 'warning';
  }
  return 'normal';
}

function levelForBand(axis, bandNum, kind, value){
  if (!thresholds) return 'normal';
  const bt = (thresholds.band_thresholds || []).find(b => b.axis === axis && b.band_number === bandNum);
  if (!bt) return 'normal';
  if (kind === 'total_rms'){
    if (value >= bt.total_rms_alarm) return 'alarm';
    if (value >= bt.total_rms_warning) return 'warning';
  }
  if (kind === 'peak_rms'){
    if (value >= bt.peak_rms_alarm) return 'alarm';
    if (value >= bt.peak_rms_warning) return 'warning';
  }
  return 'normal';
}

function dotClass(level){
  if (level === 'alarm') return 'is-bad';
  if (level === 'warning') return 'is-warn';
  return 'is-ok';
}

function _colorForLevel(level){
  if (level === 'alarm') return '#ef4444';
  if (level === 'warning') return '#f59e0b';
  return '#22c55e';
}

const PARAMS = [
  { key: 'z_rms_mm_s', label: 'Z RMS velocity', unit: 'mm/s', decimals: 3, threshold: 'z' },
  { key: 'x_rms_mm_s', label: 'X RMS velocity', unit: 'mm/s', decimals: 3, threshold: 'x' },
  { key: 'z_peak_mm_s', label: 'Z peak velocity', unit: 'mm/s', decimals: 3 },
  { key: 'x_peak_mm_s', label: 'X peak velocity', unit: 'mm/s', decimals: 3 },
  { key: 'z_rms_g', label: 'Z RMS acceleration', unit: 'g', decimals: 3 },
  { key: 'x_rms_g', label: 'X RMS acceleration', unit: 'g', decimals: 3 },
  { key: 'z_hf_rms_g', label: 'Z HF RMS acceleration', unit: 'g', decimals: 3 },
  { key: 'x_hf_rms_g', label: 'X HF RMS acceleration', unit: 'g', decimals: 3 },
  { key: 'z_kurtosis', label: 'Z kurtosis', unit: '', decimals: 3 },
  { key: 'x_kurtosis', label: 'X kurtosis', unit: '', decimals: 3 },
  { key: 'z_crest_factor', label: 'Z crest factor', unit: '', decimals: 3 },
  { key: 'x_crest_factor', label: 'X crest factor', unit: '', decimals: 3 },
  { key: 'temp_c', label: 'Temperature', unit: '°C', decimals: 2, threshold: 't' },
];

function statusForParamKey(key, value){
  if (key === 'z_rms_mm_s') return levelForScalar('z_rms_mm_s', value);
  if (key === 'x_rms_mm_s') return levelForScalar('x_rms_mm_s', value);
  if (key === 'temp_c') return levelForScalar('temp_c', value);
  return 'normal';
}

async function apiGet(path){
  const res = await fetch(API(path));
  if (!res.ok) throw new Error(await res.text());
  if (res.status === 204) return null;
  return await res.json();
}

async function apiPost(path, body){
  const res = await fetch(API(path), {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(body)
  });
  if (!res.ok) throw new Error(await res.text());
  return await res.json();
}

function setConnUI(ok, text, sub){
  const dot = qs('connDot');
  dot.classList.remove('is-ok','is-warn','is-bad');
  dot.classList.add(ok ? 'is-ok' : 'is-bad');
  qs('connLabel').textContent = ok ? 'Connected' : 'Disconnected';
  qs('connSub').textContent = ok ? text : (sub || 'No sensor connection');
  
  // Store connection state for other UI components
  window.connectionState = { ok, text, sub };
}

function updateKpis(){
  if (!latest) return;
  
  // Check if we're disconnected and show stale warning
  const isStale = window.connectionState && !window.connectionState.ok;
  const staleSuffix = isStale ? ' (stale)' : '';
  
  qs('kpiZ').textContent = fmt(latest.z_rms_mm_s, 3) + staleSuffix;
  qs('kpiX').textContent = fmt(latest.x_rms_mm_s, 3) + staleSuffix;
  qs('kpiT').textContent = fmt(latest.temp_c, 2) + staleSuffix;

  const zL = levelForScalar('z_rms_mm_s', Number(latest.z_rms_mm_s));
  const xL = levelForScalar('x_rms_mm_s', Number(latest.x_rms_mm_s));
  const tL = levelForScalar('temp_c', Number(latest.temp_c));

  const kz = qs('kpiZStatus');
  const kx = qs('kpiXStatus');
  const kt = qs('kpiTStatus');
  kz.className = `kpi__status ${dotClass(zL)}`;
  kx.className = `kpi__status ${dotClass(xL)}`;
  kt.className = `kpi__status ${dotClass(tL)}`;

  const active = alerts.filter(a => a.status === 'active').length;
  qs('kpiA').textContent = String(active);
  qs('alertsPill').textContent = String(active);
  
  // Update ML prediction KPI
  updateMLPredictionKpi();

   // Update ML state summary card
   updateMLStateCard();
   
   // Update ML Overview Hero box
   updateMLOverviewHero();
}

function updateMLOverviewHero() {
  const heroEl = qs('mlOverviewHero');
  const iconEl = qs('mlOverviewIcon');
  const predEl = qs('mlOverviewPrediction');
  const confEl = qs('mlOverviewConfidence');
  const stateEl = qs('mlOverviewState');
  const modelEl = qs('mlOverviewModel');
  
  if (!heroEl) return;
  
  // Get prediction data
  const pred = latest?.ml_prediction;
  
  if (!pred) {
    heroEl.className = 'ml-overview-hero';
    if (predEl) predEl.textContent = 'WAITING...';
    if (confEl) confEl.textContent = '—';
    if (stateEl) stateEl.textContent = '—';
    if (modelEl) modelEl.textContent = latest?.ml_error ? 'Error' : 'Loading';
    return;
  }
  
  const label = (pred.label || 'unknown').toLowerCase();
  const confidence = pred.confidence || 0;
  const confPercent = (confidence * 100).toFixed(0);
  
  // Prefer backend-provided train_state when available; fall back to RMS heuristic
  const backendState = latest?.train_state;
  const zRms = Number(latest?.z_rms_mm_s ?? 0);
  const xRms = Number(latest?.x_rms_mm_s ?? 0);
  const isIdle = (typeof backendState === 'string' ? backendState === 'idle' : (zRms < 0.05 && xRms < 0.05));
  
  // Update hero class based on prediction
  let heroClass = 'ml-overview-hero';
  let displayLabel = 'NORMAL';
  let iconName = 'shield-check';
  
  if (label === 'normal' || label === 'good') {
    heroClass = 'ml-overview-hero';
    displayLabel = 'TRACK OK';
    iconName = 'shield-check';
  } else if (label === 'expansion_gap' || label === 'gap') {
    heroClass = 'ml-overview-hero is-gap';
    displayLabel = 'EXPANSION GAP';
    iconName = 'minus-circle';
  } else if (label === 'crack' || label === 'defect') {
    heroClass = 'ml-overview-hero is-crack';
    displayLabel = 'CRACK DETECTED';
    iconName = 'alert-triangle';
  }
  
  heroEl.className = heroClass;
  if (predEl) predEl.textContent = displayLabel;
  if (confEl) confEl.textContent = `${confPercent}%`;
  if (stateEl) stateEl.textContent = (backendState || (isIdle ? 'idle' : 'moving')).toString().toUpperCase();
  if (modelEl) modelEl.textContent = 'Active';
  
  // Update icon
  if (iconEl) {
    iconEl.innerHTML = `<i data-lucide="${iconName}"></i>`;
    if (window.lucide) lucide.createIcons();
  }
}

function updateMLPredictionKpi(){
  const mlEl = qs('kpiML');
  const mlConfEl = qs('kpiMLConf');
  const mlStatusEl = qs('kpiMLStatus');
  
  // Also update the alert banner (new class structure)
  const mlBanner = qs('mlAlertBanner');
  const mlBannerIcon = qs('mlBannerIcon');
  const mlBannerText = qs('mlAlertText');
  const mlBannerConf = qs('mlAlertConf');
  
  // Check if latest reading has ml_prediction
  const pred = latest?.ml_prediction;
  
  // Debug log to see what we're getting
  console.log('[ML UI] latest.ml_prediction:', pred, 'latest.ml_error:', latest?.ml_error);
  
  if (!pred) {
    // No prediction available
    const mlError = latest?.ml_error;
    if (mlEl) mlEl.textContent = '—';
    if (mlConfEl) mlConfEl.textContent = mlError || 'No model loaded';
    if (mlStatusEl) mlStatusEl.className = 'kpi__status kpi__status--neutral';
    
    // Update banner - neutral state
    if (mlBanner) {
      mlBanner.className = 'ml-banner';
      if (mlBannerIcon) mlBannerIcon.innerHTML = '<i data-lucide="loader"></i>';
      if (mlBannerText) mlBannerText.textContent = mlError || 'Waiting for ML Prediction...';
      if (mlBannerConf) mlBannerConf.textContent = '';
      if (window.lucide) lucide.createIcons();
    }
    return;
  }
  
  // Display prediction label
  const label = (pred.label || 'unknown').toLowerCase();
  const confidence = pred.confidence || 0;
  const confPercent = (confidence * 100).toFixed(1);
  
  // Normalize label for comparison (handle gap vs expansion_gap)
  const normalizedLabel = label.replace('expansion_', '');
  
  // Format label for display
  let displayLabel = label.toUpperCase().replace(/_/g, ' ');
  let statusClass = 'kpi__status--ok';
  let bannerClass = 'ml-banner--normal';
  let bannerText = 'GOOD TRACK';
  let bannerIcon = 'shield-check';
  
  if (normalizedLabel === 'normal' || normalizedLabel === 'good') {
    statusClass = 'kpi__status--ok';
    bannerClass = 'ml-banner--normal';
    bannerText = 'TRACK NORMAL — ALL CLEAR';
    bannerIcon = 'shield-check';
    displayLabel = 'NORMAL';
  } else if (normalizedLabel === 'gap' || label === 'expansion_gap') {
    statusClass = 'kpi__status--info';
    bannerClass = 'ml-banner--gap';
    bannerText = 'EXPANSION GAP DETECTED';
    bannerIcon = 'alert-triangle';
    displayLabel = 'GAP';
  } else if (normalizedLabel === 'crack' || normalizedLabel === 'defect' || label === 'crack_or_defect') {
    statusClass = 'kpi__status--alarm';
    bannerClass = 'ml-banner--crack';
    bannerText = 'CRACK DETECTED — INSPECT NOW';
    bannerIcon = 'alert-octagon';
    displayLabel = 'CRACK';
  } else {
    // Unknown or other fault types
    statusClass = 'kpi__status--warning';
    bannerClass = '';
    bannerText = displayLabel;
    bannerIcon = 'help-circle';
  }

  // If backend reports train is idle, show a dedicated idle banner overriding ML banner
  if (latest?.train_state === 'idle'){
    bannerClass = 'ml-banner--idle';
    bannerText = 'TRAIN IDLE — Baseline readings';
    bannerIcon = 'pause';
  }
  
  // Update KPI elements
  if (mlEl) mlEl.textContent = displayLabel;
  if (mlConfEl) mlConfEl.textContent = `${confPercent}% confidence`;
  if (mlStatusEl) mlStatusEl.className = `kpi__status ${statusClass}`;
  
  // Update alert banner
  if (mlBanner) {
    mlBanner.className = `ml-banner ${bannerClass}`;
    if (mlBannerIcon) mlBannerIcon.innerHTML = `<i data-lucide="${bannerIcon}"></i>`;
    if (mlBannerText) mlBannerText.textContent = bannerText;
    if (mlBannerConf) mlBannerConf.textContent = (latest?.train_state === 'idle') ? '' : (confPercent + '%');
    if (window.lucide) lucide.createIcons();
  }
}

function updateMLStateCard(){
  const trainStateEl = qs('mlTrainState');
  const trainStateSubEl = qs('mlTrainStateSub');
  const trainStateStatusEl = qs('mlTrainStateStatus');
  const mlLabelEl = qs('mlStateLabel');
  const mlConfEl = qs('mlStateConf');
  const mlStatusEl = qs('mlStateStatus');

  if (!trainStateEl || !trainStateSubEl || !trainStateStatusEl || !mlLabelEl || !mlConfEl || !mlStatusEl){
    return;
  }

  if (!latest){
    trainStateEl.textContent = '—';
    trainStateSubEl.textContent = 'No live readings. Connect the sensor first.';
    trainStateStatusEl.className = 'kpi__status kpi__status--neutral';
    mlLabelEl.textContent = '—';
    mlConfEl.textContent = 'No readings available';
    mlStatusEl.className = 'kpi__status kpi__status--neutral';
    return;
  }

  // Prefer backend-provided train_state for display. If backend omits it, fall back to RMS heuristic.
  const backendState = (latest.train_state || '').toString().toLowerCase();
  const zRms = Number(latest.z_rms_mm_s ?? 0);
  const xRms = Number(latest.x_rms_mm_s ?? 0);

  const isIdle = backendState === 'idle' || (backendState === '' && zRms < 0.5 && xRms < 0.5);
  const stateLabel = isIdle ? 'IDLE' : 'MOVING';
  const stateSub = isIdle ? 'Very low vibration – train idle' : 'Vibration present – train moving or under test';
  const stateClass = isIdle ? 'kpi__status--info' : 'kpi__status--ok';

  trainStateEl.textContent = (backendState || stateLabel).toString().toUpperCase();
  trainStateSubEl.textContent = stateSub;
  trainStateStatusEl.className = `kpi__status ${stateClass}`;

  const pred = latest.ml_prediction;
  if (!pred){
    const mlError = latest.ml_error;
    mlLabelEl.textContent = '—';
    mlConfEl.textContent = mlError || 'No model loaded';
    mlStatusEl.className = 'kpi__status kpi__status--neutral';
    return;
  }

  const label = (pred.label || 'unknown').toLowerCase();
  const confidence = pred.confidence || 0;
  const confPercent = (confidence * 100).toFixed(1);

  const normalizedLabel = label.replace('expansion_', '');

  let displayLabel = label.toUpperCase().replace(/_/g, ' ');
  let statusClass = 'kpi__status--ok';

  if (normalizedLabel === 'normal' || normalizedLabel === 'good'){
    displayLabel = 'NORMAL';
    statusClass = 'kpi__status--ok';
  }else if (normalizedLabel === 'gap' || label === 'expansion_gap'){
    displayLabel = 'GAP';
    statusClass = 'kpi__status--info';
  }else if (normalizedLabel === 'crack' || normalizedLabel === 'defect' || label === 'crack_or_defect'){
    displayLabel = 'CRACK';
    statusClass = 'kpi__status--alarm';
  }else{
    statusClass = 'kpi__status--warning';
  }

  // If idle, downgrade severity to informational but keep label
  if (isIdle && (normalizedLabel === 'crack' || normalizedLabel === 'gap')){
    statusClass = 'kpi__status--info';
  }

  mlLabelEl.textContent = displayLabel;
  mlConfEl.textContent = `${confPercent}% confidence`;
  mlStatusEl.className = `kpi__status ${statusClass}`;
}

qs('mlTestBtn')?.addEventListener('click', async () => {
  const btn = qs('mlTestBtn');
  if (!btn) return;
  btn.disabled = true;
  btn.textContent = 'Testing...';
  try{
    const res = await apiGet('/api/ml/test');
    const confPct = ((res?.prediction?.confidence ?? 0) * 100).toFixed(1);
    alert(`Prediction: ${res?.prediction?.label || 'n/a'} (confidence ${confPct}%)\nState: ${res?.train_state || 'n/a'}\nTimestamp: ${res?.timestamp || 'n/a'}`);
  }catch(e){
    alert(`ML test failed: ${e?.message || e}`);
  }finally{
    btn.disabled = false;
    btn.textContent = 'Test ML Response';
  }
});

function renderParamGrid(){
  const grid = qs('paramGrid');
  grid.innerHTML = '';
  if (!latest) return;

  const items = [
    {k:'z_rms_mm_s', label:'Z RMS', unit:'mm/s', d:3},
    {k:'x_rms_mm_s', label:'X RMS', unit:'mm/s', d:3},
    {k:'z_peak_mm_s', label:'Z Peak', unit:'mm/s', d:3},
    {k:'x_peak_mm_s', label:'X Peak', unit:'mm/s', d:3},
    {k:'z_rms_g', label:'Z RMS Acc', unit:'g', d:3},
    {k:'x_rms_g', label:'X RMS Acc', unit:'g', d:3},
    {k:'z_hf_rms_g', label:'Z HF RMS', unit:'g', d:3},
    {k:'x_hf_rms_g', label:'X HF RMS', unit:'g', d:3},
    {k:'z_kurtosis', label:'Z Kurtosis', unit:'', d:3},
    {k:'x_kurtosis', label:'X Kurtosis', unit:'', d:3},
    {k:'z_crest_factor', label:'Z Crest', unit:'', d:3},
    {k:'x_crest_factor', label:'X Crest', unit:'', d:3},
    {k:'temp_c', label:'Temperature', unit:'°C', d:2},
  ];

  for (const it of items){
    const v = Number(latest[it.k]);
    const level = (it.k === 'temp_c' || it.k === 'z_rms_mm_s' || it.k === 'x_rms_mm_s')
      ? levelForScalar(it.k, v)
      : 'normal';

    const el = document.createElement('div');
    el.className = 'param';
    el.innerHTML = `
      <div class="param__top">
        <div class="param__label">${it.label}</div>
        <div class="param__dot ${dotClass(level)}"></div>
      </div>
      <div class="param__value">${fmt(v, it.d)}</div>
      <div class="param__unit">${it.unit}</div>
    `;
    grid.appendChild(el);
  }
}

function renderBandList(){
  const list = qs('bandList');
  list.innerHTML = '';
  if (!latest) return;

  const bands = getBandsFromReading(latest, selectedAxis);
  if (!bands.length){
    list.innerHTML = `<div class="note">No band data available for this axis.</div>`;
    selectedBand = null;
    renderFrequencySnapshot();
    return;
  }

  if (selectedBand == null){
    selectedBand = Number(bands[0].band_number);
  }

  const exists = bands.some(b => Number(b.band_number) === Number(selectedBand));
  if (!exists){
    selectedBand = Number(bands[0].band_number);
  }

  for (const b of bands){
    const n = Number(b.band_number);
    const level = levelForBand(selectedAxis, n, 'total_rms', Number(b.total_rms));

    const row = document.createElement('div');
    row.className = 'bandItem' + (n === selectedBand ? ' is-active' : '');
    row.innerHTML = `
      <div class="bandItem__meta">
        <div class="bandItem__title">${_bandPrimaryText(b)}</div>
        <div class="bandItem__sub">${_bandSecondaryText(b)}</div>
      </div>
      <div class="bandItem__right">
        <div class="bandItem__metric">Total RMS: ${fmt(b.total_rms,2)}</div>
        <div class="bandItem__metric">Peak freq: ${fmt(b.peak_freq_hz,1)} Hz</div>
        <div class="bandItem__metric">Peak RPM: ${fmt(b.peak_rpm,0)} RPM</div>
      </div>
      <div class="bandItem__dot ${dotClass(level)}"></div>
    `;
    row.addEventListener('click', () => {
      selectedBand = n;
      renderBandList();
      renderBandDetail();
      renderFrequencySnapshot();
    });
    list.appendChild(row);
  }
}

function renderBandDetail(){
  const head = qs('bandHead');
  const nameEl = qs('bandName');
  const cards = qs('bandCards');
  cards.innerHTML = '';
  if (nameEl) nameEl.textContent = '';

  if (!latest) return;
  const bands = getBandsFromReading(latest, selectedAxis);
  if (!bands.length){
    head.textContent = 'No band data available for this axis.';
    if (nameEl) nameEl.textContent = '';
    return;
  }
  if (selectedBand == null){
    head.textContent = 'Select a band to inspect';
    if (nameEl) nameEl.textContent = '';
    return;
  }
  const b = bands.find(x => Number(x.band_number) === Number(selectedBand));
  if (!b){
    head.textContent = 'Select a band to inspect';
    if (nameEl) nameEl.textContent = '';
    return;
  }

  head.textContent = `Band ${b.band_number} – ${bandMultiple(b)}× (${axisLabel(selectedAxis)} axis)`;

  if (nameEl) nameEl.textContent = _bandFriendlyName(b);

  const c = [
    {k:'total_rms', label:'Total RMS (mm/s)', v:fmt(b.total_rms,3)},
    {k:'peak_rms', label:'Peak RMS (mm/s)', v:fmt(b.peak_rms,3)},
    {k:'peak_freq_hz', label:'Peak frequency (Hz)', v:fmt(b.peak_freq_hz,2)},
    {k:'peak_rpm', label:'Peak RPM', v:fmt(b.peak_rpm,0)},
    {k:'bin_index', label:'Bin', v:String(b.bin_index ?? '—')},
  ];

  for (const it of c){
    const el = document.createElement('div');
    el.className = 'bandCard';
    el.innerHTML = `<div class="bandCard__k">${it.label}</div><div class="bandCard__v">${it.v}</div>`;
    cards.appendChild(el);
  }

  renderFrequencySnapshot();
}

function renderHealthBandName(){
  const el = qs('healthBandName');
  if (!el || !latest) return;
  const bands = getBandsFromReading(latest, selectedAxisHealth);
  const b = bands.find(x => Number(x.band_number) === Number(selectedHealthBand));
  el.textContent = b ? _bandFriendlyName(b) : '';
}

function renderBandsTable(){
  const table = qs('bandsTable');
  if (!table) return;
  const tbody = table.querySelector('tbody');
  tbody.innerHTML = '';
  if (!latest) return;

  const bands = selectedAxisHealth === 'z' ? (latest.bands_z || []) : (latest.bands_x || []);
  if (!bands.length){
    tbody.innerHTML = '<tr><td colspan="8" class="muted">No band data available</td></tr>';
    return;
  }

  for (const b of bands){
    const n = Number(b.band_number);
    const level = levelForBand(selectedAxisHealth, n, 'total_rms', Number(b.total_rms));
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${n}</td>
      <td>${b.multiple || n}×</td>
      <td>${fmt(b.total_rms,3)}</td>
      <td>${fmt(b.peak_rms,3)}</td>
      <td>${fmt(b.peak_freq_hz,2)}</td>
      <td>${fmt(b.peak_rpm,1)}</td>
      <td>${b.bin_index ?? '—'}</td>
      <td><span class="pill">${level.toUpperCase()}</span></td>
    `;
    tbody.appendChild(tr);
  }
}

function renderAlertsTable(){
  const tbody = qs('alertsTable').querySelector('tbody');
  tbody.innerHTML = '';

  for (const a of alerts){
    const tr = document.createElement('tr');
    const ackBtn = a.status === 'active'
      ? `<button class="btn" data-ack="${a.id}">Ack</button>`
      : '';

    tr.innerHTML = `
      <td>${new Date(a.timestamp).toLocaleString()}</td>
      <td>${a.severity}</td>
      <td>${a.parameter}</td>
      <td>${fmt(a.value,3)}</td>
      <td>${fmt(a.threshold,3)}</td>
      <td>${a.status}</td>
      <td>${ackBtn}</td>
    `;
    tbody.appendChild(tr);
  }

  tbody.querySelectorAll('[data-ack]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = btn.getAttribute('data-ack');
      await apiPost(`/api/alerts/${id}/ack`, null);
      await refreshAlerts();
    });
  });
}

let chartHealth;
function initHealthChart(){
  const base = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 0 },
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: 'rgba(232,237,247,.55)' }, grid: { color: 'rgba(255,255,255,.06)' } },
      y: { ticks: { color: 'rgba(232,237,247,.55)' }, grid: { color: 'rgba(255,255,255,.06)' } }
    }
  };

  chartHealth = new Chart(qs('chartHealth'), {
    type: 'line',
    data: { labels: [], datasets: [{ label: 'Value', data: [], borderColor: '#21c7b7', tension: .25, pointRadius: 0 }] },
    options: base
  });
}

function setHealthSelection(key){
  selectedHealthParam = key;
  renderHealthParamGrid();
  renderHealthDetailFromLatest();
  refreshHealthHistory();
}

function renderHealthParamGrid(){
  const grid = qs('healthParamGrid');
  if (!grid) return;
  grid.innerHTML = '';
  if (!latest) return;

  for (const p of PARAMS){
    const v = Number(latest[p.key]);
    const level = statusForParamKey(p.key, v);
    const el = document.createElement('div');
    el.className = 'pCard' + (p.key === selectedHealthParam ? ' is-active' : '');
    el.innerHTML = `
      <div class="pCard__top">
        <div class="pCard__title">${p.label}</div>
        <div class="pCard__dot ${dotClass(level)}"></div>
      </div>
      <div class="pCard__value">${fmt(v, p.decimals ?? 3)}</div>
      <div class="pCard__unit">${p.unit}</div>
      <svg class="pCard__spark" viewBox="0 0 100 24" preserveAspectRatio="none">
        <path d="M0 18 L20 16 L40 12 L60 14 L80 10 L100 12" fill="none" stroke="rgba(255,255,255,.22)" stroke-width="2" />
      </svg>
    `;
    el.addEventListener('click', () => setHealthSelection(p.key));
    grid.appendChild(el);
  }
}

function renderHealthDetailFromLatest(){
  const empty = qs('healthEmpty');
  const panel = qs('healthPanel');
  if (!empty || !panel) return;
  if (!latest) return;

  const p = PARAMS.find(x => x.key === selectedHealthParam);
  if (!p){
    empty.style.display = 'block';
    panel.style.display = 'none';
    return;
  }

  empty.style.display = 'none';
  panel.style.display = 'block';

  const v = Number(latest[p.key]);
  const level = statusForParamKey(p.key, v);

  qs('healthTitle').textContent = `${p.label} (${p.unit || '—'})`;
  qs('healthValue').textContent = `${fmt(v, p.decimals ?? 3)} ${p.unit}`.trim();

  const dot = qs('healthDot');
  dot.classList.remove('is-ok','is-warn','is-bad');
  dot.classList.add(dotClass(level));
  qs('healthStatus').textContent = level.toUpperCase();
}

async function refreshHealthHistory(){
  if (!chartHealth) return;
  const windowSel = qs('healthWindow');
  const seconds = windowSel ? Number(windowSel.value || 600) : 600;

  try{
    const rows = await apiGet(`/api/history?seconds=${seconds}`);
    const p = PARAMS.find(x => x.key === selectedHealthParam);
    if (!p) return;

    const labels = [];
    const data = [];
    let prev = null;
    for (const r of rows){
      const t = new Date(r.timestamp);
      labels.push(t.toLocaleTimeString());
      const raw = Number(r[p.key] ?? 0);
      prev = smooth(prev, raw);
      data.push(prev);
    }

    chartHealth.data.labels = labels;
    chartHealth.data.datasets[0].data = data;
    chartHealth.data.datasets[0].label = p.label;
    chartHealth.update('none');

    let labelsB = [];
    let total = [];
    let peak = [];
    let freq = [];

    if (chartBandRms || chartBandFreq){
      let pTotal = null;
      let pPeak = null;
      let pFreq = null;
      for (const r of rows){
        const t = new Date(r.timestamp);
        labelsB.push(t.toLocaleTimeString());
        const bands = getBandsFromReading(r, selectedAxisHealth);
        const b = selectedHealthBand == null ? null : bands.find(x => Number(x.band_number) === Number(selectedHealthBand));
        const totalRaw = b ? Number(b.total_rms ?? 0) : 0;
        const peakRaw = b ? Number(b.peak_rms ?? 0) : 0;
        const freqRaw = b ? Number(b.peak_freq_hz ?? 0) : 0;
        pTotal = smooth(pTotal, totalRaw);
        pPeak = smooth(pPeak, peakRaw);
        pFreq = smooth(pFreq, freqRaw);
        total.push(pTotal);
        peak.push(pPeak);
        freq.push(pFreq);
      }
      if (chartBandRms){
        chartBandRms.data.labels = labelsB;
        chartBandRms.data.datasets[0].data = total;
        chartBandRms.data.datasets[1].data = peak;
        chartBandRms.update('none');
      }
      if (chartBandFreq){
        chartBandFreq.data.labels = labelsB;
        chartBandFreq.data.datasets[0].data = freq;
        chartBandFreq.update('none');
      }
    }

    const stats = qs('healthStats');
    if (stats && data.length){
      const min = Math.min(...data);
      const max = Math.max(...data);
      const avg = data.reduce((a,b)=>a+b,0) / data.length;
      stats.innerHTML = `
        <div class="stat"><div class="stat__k">Min</div><div class="stat__v">${fmt(min, p.decimals ?? 3)}</div></div>
        <div class="stat"><div class="stat__k">Avg</div><div class="stat__v">${fmt(avg, p.decimals ?? 3)}</div></div>
        <div class="stat"><div class="stat__k">Max</div><div class="stat__v">${fmt(max, p.decimals ?? 3)}</div></div>
      `;
    }

    if (rows.length){
      _lastHealthTs = rows[rows.length - 1].timestamp;
      _smoothState.health = data.length ? data[data.length - 1] : null;
      _smoothState.healthBandTotal = total.length ? total[total.length - 1] : null;
      _smoothState.healthBandPeak = peak.length ? peak[peak.length - 1] : null;
      _smoothState.healthBandFreq = freq.length ? freq[freq.length - 1] : null;
    }
  }catch(e){
  }
}

function renderHealthBandsTable(){
  const table = qs('healthBandsTable');
  if (!table || !latest) return;
  const tbody = table.querySelector('tbody');
  tbody.innerHTML = '';
  const bands = getBandsFromReading(latest, selectedAxisHealth);
  if (!bands.length){
    tbody.innerHTML = '<tr><td colspan="6" class="muted">No band data available for this axis</td></tr>';
    return;
  }
  for (const b of bands){
    const n = Number(b.band_number);
    const level = levelForBand(selectedAxisHealth, n, 'total_rms', Number(b.total_rms));
    const tr = document.createElement('tr');
    tr.style.cursor = 'pointer';
    tr.classList.toggle('is-active', n === selectedHealthBand);
    tr.innerHTML = `
      <td>${_bandPrimaryText(b)}</td>
      <td>${_bandSecondaryText(b)}</td>
      <td>${fmt(b.total_rms,3)}</td>
      <td>${fmt(b.peak_freq_hz,2)} Hz</td>
      <td>${fmt(b.peak_rpm,0)} RPM</td>
      <td><span class="pill">${level.toUpperCase()}</span></td>
    `;
    tr.addEventListener('click', () => {
      selectedHealthBand = n;
      selectedAxis = selectedAxisHealth;
      selectedBand = n;
      const zBtn = qs('axisZ');
      const xBtn = qs('axisX');
      if (zBtn && xBtn){
        zBtn.classList.toggle('is-active', selectedAxis === 'z');
        xBtn.classList.toggle('is-active', selectedAxis === 'x');
      }
      renderBandList();
      renderBandDetail();
      renderHealthBandsTable();
      renderHealthBandSelector();
      renderHealthBandMetrics();
      renderAllBandsSnapshot();
      renderSpectrum();
      refreshHealthHistory();
    });
    tbody.appendChild(tr);
  }
}

function renderFrequencySnapshot(){
  const hzEl = qs('kpiFreqHz');
  const rpmEl = qs('kpiFreqRpm');
  const capEl = qs('kpiFreqCap');
  if (!hzEl || !rpmEl || !capEl) return;

  // Check if data is stale
  const isStale = window.connectionState && !window.connectionState.ok;
  const staleSuffix = isStale ? ' (stale)' : '';

  if (!latest){
    hzEl.textContent = '—';
    rpmEl.textContent = 'No data';
    capEl.textContent = '—';
    return;
  }

  const bands = getBandsFromReading(latest, selectedAxis);
  if (!bands.length){
    hzEl.textContent = '—';
    rpmEl.textContent = 'No band data';
    capEl.textContent = `${axisLabel(selectedAxis)} axis`;
    return;
  }

  if (selectedBand == null){
    // Auto-select first band if none selected
    selectedBand = Number(bands[0].band_number);
  }

  const b = bands.find(x => Number(x.band_number) === Number(selectedBand));
  if (!b){
    hzEl.textContent = '—';
    rpmEl.textContent = 'Band not found';
    capEl.textContent = `${axisLabel(selectedAxis)} axis`;
    return;
  }

  hzEl.textContent = `${fmt(b.peak_freq_hz, 1)} Hz${staleSuffix}`;
  rpmEl.textContent = `${fmt(b.peak_rpm, 0)} RPM${staleSuffix}`;
  capEl.textContent = `Band ${b.band_number} – ${bandMultiple(b)}× on ${axisLabel(selectedAxis)} axis`;
}

function afterThresholdsChanged(){
  updateKpis();
  renderParamGrid();
  renderBandList();
  renderBandDetail();
  renderFrequencySnapshot();
  renderHealthParamGrid();
  renderHealthDetailFromLatest();
  renderHealthBandsTable();
  renderHealthBandMetrics();
  renderAllBandsSnapshot();
  renderSpectrum();
}

function _ensureThresholds(){
  if (!thresholds) thresholds = { band_thresholds: [] };
  if (!Array.isArray(thresholds.band_thresholds)) thresholds.band_thresholds = [];
}

function validateThresholds(th){
  const errs = [];
  const nonNeg = (v) => Number.isFinite(v) && v >= 0;

  if (!nonNeg(Number(th.z_rms_mm_s_warning)) || !nonNeg(Number(th.z_rms_mm_s_alarm)) || Number(th.z_rms_mm_s_alarm) < Number(th.z_rms_mm_s_warning)){
    errs.push('Z RMS: alarm must be >= warning and both must be >= 0');
  }
  if (!nonNeg(Number(th.x_rms_mm_s_warning)) || !nonNeg(Number(th.x_rms_mm_s_alarm)) || Number(th.x_rms_mm_s_alarm) < Number(th.x_rms_mm_s_warning)){
    errs.push('X RMS: alarm must be >= warning and both must be >= 0');
  }
  if (!nonNeg(Number(th.temp_c_warning)) || !nonNeg(Number(th.temp_c_alarm)) || Number(th.temp_c_alarm) < Number(th.temp_c_warning)){
    errs.push('Temp: alarm must be >= warning and both must be >= 0');
  }

  for (const bt of (th.band_thresholds || [])){
    if (!nonNeg(Number(bt.total_rms_warning)) || !nonNeg(Number(bt.total_rms_alarm)) || Number(bt.total_rms_alarm) < Number(bt.total_rms_warning)){
      errs.push(`Band ${bt.axis.toUpperCase()}${bt.band_number} total_rms: alarm must be >= warning and both >= 0`);
      break;
    }
    if (!nonNeg(Number(bt.peak_rms_warning)) || !nonNeg(Number(bt.peak_rms_alarm)) || Number(bt.peak_rms_alarm) < Number(bt.peak_rms_warning)){
      errs.push(`Band ${bt.axis.toUpperCase()}${bt.band_number} peak_rms: alarm must be >= warning and both >= 0`);
      break;
    }
  }

  return errs.length ? errs.join('\n') : null;
}

function renderSpectrum(){
  if (!chartSpectrum || !latest) return;
  const bands = getBandsFromReading(latest, selectedAxisHealth);
  const points = [];

  for (const b of bands){
    const n = Number(b.band_number);
    const freq = Number(b.peak_freq_hz);
    const amp = Number.isFinite(Number(b.total_rms)) ? Number(b.total_rms) : Number(b.peak_rms);
    if (!Number.isFinite(freq) || !Number.isFinite(amp)) continue;
    const status = levelForBand(selectedAxisHealth, n, 'total_rms', Number(b.total_rms));
    points.push({
      x: freq,
      y: amp,
      band_number: n,
      multiple: Number(b.multiple || n),
      axis: selectedAxisHealth,
      status: status
    });
  }

  points.sort((a,b)=>a.x-b.x);

  chartSpectrum.data.datasets[0].data = points;
  chartSpectrum.data.datasets[0].pointBackgroundColor = points.map(p => _colorForLevel(p.status));
  chartSpectrum.data.datasets[0].pointBorderColor = points.map(p => (p.band_number === selectedHealthBand ? '#ffffff' : 'rgba(0,0,0,0)'));
  chartSpectrum.data.datasets[0].pointBorderWidth = points.map(p => (p.band_number === selectedHealthBand ? 2 : 0));
  chartSpectrum.data.datasets[0].pointRadius = points.map(p => (p.band_number === selectedHealthBand ? 7 : 5));
  chartSpectrum.update('none');
}

function renderSystemInfo(){
  const sys = qs('systemKv');
  const connKv = qs('connKv');
  if (!sys || !connKv) return;

  const model = 'Banner QM30VT2';
  const fw = '—';
  const sw = 'Gandiva Dashboard (frontend)';
  const up = `${Math.round(performance.now()/1000)} s`;

  sys.innerHTML = `
    <div class="kvRow"><div class="kvRow__k">Sensor model</div><div class="kvRow__v">${model}</div></div>
    <div class="kvRow"><div class="kvRow__k">Firmware</div><div class="kvRow__v">${fw}</div></div>
    <div class="kvRow"><div class="kvRow__k">Software</div><div class="kvRow__v">${sw}</div></div>
    <div class="kvRow"><div class="kvRow__k">Uptime (UI)</div><div class="kvRow__v">${up}</div></div>
  `;

  connKv.innerHTML = `
    <div class="kvRow"><div class="kvRow__k">Port</div><div class="kvRow__v">${connection?.port || '—'}</div></div>
    <div class="kvRow"><div class="kvRow__k">Baudrate</div><div class="kvRow__v">${connection?.baudrate || '—'}</div></div>
    <div class="kvRow"><div class="kvRow__k">Parity</div><div class="kvRow__v">${connection?.parity || '—'}</div></div>
    <div class="kvRow"><div class="kvRow__k">Slave ID</div><div class="kvRow__v">${connection?.slave_id || '—'}</div></div>
  `;
}

async function refreshLogs(){
  const table = qs('logsTable');
  if (!table) return;

  const seconds = Number(qs('logsWindow')?.value || 3600);
  try{
    const rows = await apiGet(`/api/history?seconds=${seconds}`);
    logsRows = rows.slice().reverse();
    logsPage = 1;
    renderLogsPage();
  }catch(e){
  }
}

function highestBandRms(row){
  const all = ([]).concat(getBandsFromReading(row, 'z') || [], getBandsFromReading(row, 'x') || []);
  let max = 0;
  for (const b of all){
    const v = Number(b.total_rms || 0);
    if (v > max) max = v;
  }
  return max;
}

function renderLogsPage(){
  const tbody = qs('logsTable')?.querySelector('tbody');
  if (!tbody) return;

  const totalPages = Math.max(1, Math.ceil(logsRows.length / LOGS_PAGE_SIZE));
  logsPage = Math.min(Math.max(1, logsPage), totalPages);

  const start = (logsPage - 1) * LOGS_PAGE_SIZE;
  const page = logsRows.slice(start, start + LOGS_PAGE_SIZE);

  tbody.innerHTML = '';
  for (const r of page){
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${new Date(r.timestamp).toLocaleString()}</td>
      <td>${fmt(r.z_rms_mm_s, 3)}</td>
      <td>${fmt(r.x_rms_mm_s, 3)}</td>
      <td>${fmt(r.temp_c, 2)}</td>
      <td>${fmt(highestBandRms(r), 3)}</td>
    `;
    tbody.appendChild(tr);
  }

  const info = qs('logsPageInfo');
  if (info) info.textContent = `Page ${logsPage} / ${totalPages}`;
}

function setupHelpModal(){
  const modal = qs('helpModal');
  if (!modal) return;

  function open(){
    modal.classList.add('is-open');
    modal.setAttribute('aria-hidden', 'false');
  }
  function close(){
    modal.classList.remove('is-open');
    modal.setAttribute('aria-hidden', 'true');
  }

  qs('helpBtn')?.addEventListener('click', open);
  qs('helpClose')?.addEventListener('click', close);
  qs('helpBackdrop')?.addEventListener('click', close);
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') close();
  });
}

let chartRms, chartTemp, chartBand;
function initCharts(){
  const base = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 0 },
    plugins: { legend: { labels: { color: 'rgba(232,237,247,.8)' } } },
    scales: {
      x: { ticks: { color: 'rgba(232,237,247,.55)' }, grid: { color: 'rgba(255,255,255,.06)' } },
      y: { ticks: { color: 'rgba(232,237,247,.55)' }, grid: { color: 'rgba(255,255,255,.06)' } }
    }
  };

  chartRms = new Chart(qs('chartRms'), {
    type: 'line',
    data: {
      labels: history.labels,
      datasets: [
        { label: 'Z RMS', data: history.z, borderColor: '#6ea8fe', tension: .25, pointRadius: 0 },
        { label: 'X RMS', data: history.x, borderColor: '#22c55e', tension: .25, pointRadius: 0 }
      ]
    },
    options: base
  });

  chartTemp = new Chart(qs('chartTemp'), {
    type: 'line',
    data: {
      labels: history.labels,
      datasets: [
        { label: 'Temp (°C)', data: history.t, borderColor: '#f59e0b', tension: .25, pointRadius: 0 }
      ]
    },
    options: base
  });

  chartBand = new Chart(qs('chartBand'), {
    type: 'line',
    data: {
      labels: history.labels,
      datasets: [
        { label: 'Band total RMS', data: history.band, borderColor: '#a78bfa', tension: .25, pointRadius: 0 }
      ]
    },
    options: base
  });
}

function pushHistoryPoint(r){
  const t = new Date(r.timestamp);
  const label = t.toLocaleTimeString();

  history.labels.push(label);

  const zRaw = Number(r.z_rms_mm_s ?? 0);
  _smoothState.z = smooth(_smoothState.z, zRaw);
  history.z.push(_smoothState.z);

  const xRaw = Number(r.x_rms_mm_s ?? 0);
  _smoothState.x = smooth(_smoothState.x, xRaw);
  history.x.push(_smoothState.x);

  const tRaw = Number(r.temp_c ?? 0);
  _smoothState.t = smooth(_smoothState.t, tRaw);
  history.t.push(_smoothState.t);

  let bandRaw = 0;
  if (selectedBand != null){
    const bands = getBandsFromReading(r, selectedAxis);
    const b = bands.find(x => Number(x.band_number) === Number(selectedBand));
    bandRaw = b ? Number(b.total_rms ?? 0) : 0;
  }
  _smoothState.band = smooth(_smoothState.band, bandRaw);
  history.band.push(_smoothState.band);

  const max = 120;
  if (history.labels.length > max){
    history.labels.shift();
    history.z.shift();
    history.x.shift();
    history.t.shift();
    history.band.shift();
  }
}

function updateCharts(){
  if (chartRms) chartRms.update('none');
  if (chartTemp) chartTemp.update('none');
  if (chartBand) chartBand.update('none');
}

function _trimChartSeries(labels, series, max){
  while (labels.length > max) labels.shift();
  for (const s of series) while (s.length > max) s.shift();
}

function appendHealthLatest(){
  if (!chartHealth || !latest) return;
  if (_lastHealthTs === latest.timestamp) return;

  const windowSel = qs('healthWindow');
  const max = windowSel ? Number(windowSel.value || 600) : 600;
  const maxPoints = Math.max(120, Math.min(max, 3600));

  const label = new Date(latest.timestamp).toLocaleTimeString();
  const p = PARAMS.find(x => x.key === selectedHealthParam);
  if (!p) return;

  const raw = Number(latest[p.key] ?? 0);
  _smoothState.health = smooth(_smoothState.health, raw);

  chartHealth.data.labels.push(label);
  chartHealth.data.datasets[0].data.push(_smoothState.health);
  _trimChartSeries(chartHealth.data.labels, [chartHealth.data.datasets[0].data], maxPoints);
  chartHealth.update('none');

  if (chartBandRms || chartBandFreq){
    const bands = getBandsFromReading(latest, selectedAxisHealth);
    const b = selectedHealthBand == null ? null : bands.find(x => Number(x.band_number) === Number(selectedHealthBand));
    const totalRaw = b ? Number(b.total_rms ?? 0) : 0;
    const peakRaw = b ? Number(b.peak_rms ?? 0) : 0;
    const freqRaw = b ? Number(b.peak_freq_hz ?? 0) : 0;

    _smoothState.healthBandTotal = smooth(_smoothState.healthBandTotal, totalRaw);
    _smoothState.healthBandPeak = smooth(_smoothState.healthBandPeak, peakRaw);
    _smoothState.healthBandFreq = smooth(_smoothState.healthBandFreq, freqRaw);

    if (chartBandRms){
      chartBandRms.data.labels.push(label);
      chartBandRms.data.datasets[0].data.push(_smoothState.healthBandTotal);
      chartBandRms.data.datasets[1].data.push(_smoothState.healthBandPeak);
      _trimChartSeries(chartBandRms.data.labels, [chartBandRms.data.datasets[0].data, chartBandRms.data.datasets[1].data], maxPoints);
      chartBandRms.update('none');
    }
    if (chartBandFreq){
      chartBandFreq.data.labels.push(label);
      chartBandFreq.data.datasets[0].data.push(_smoothState.healthBandFreq);
      _trimChartSeries(chartBandFreq.data.labels, [chartBandFreq.data.datasets[0].data], maxPoints);
      chartBandFreq.update('none');
    }
  }

  _lastHealthTs = latest.timestamp;
}

async function refreshLatest(){
  try{
    const response = await apiGetWithErrorHandling('/api/latest?envelope=true');
    
    // Handle new API response format with status
    if (!response){
      // No content
      setConnUI(false, '', 'No readings');
      hideErrorBanner();
      return;
    }

    // Envelope format
    if (response.status === 'error' || response.error_message) {
      const msg = response.error_message || 'Sensor read error – check connection';
      showErrorBanner(msg, true);
      consecutiveErrors++;
      lastError = msg;
      // Keep previous good readings if available
      if (response.reading) {
        latest = response.reading;
        await hydrateMlPredictionIfMissing();
      }
      setConnUI(false, '', msg);
    } else if (response.reading) {
      // OK envelope
      latest = response.reading;
      console.log('[GANDIVA] Got reading, ml_prediction:', latest.ml_prediction, 'ml_error:', latest.ml_error);
      await hydrateMlPredictionIfMissing();
      consecutiveErrors = 0;
      hideErrorBanner();
      lastError = null;
      setConnUI(true, `${connection?.port || '—'} · ${connection?.baudrate || 19200} ${connection?.parity || 'N'}81`, '');
    } else {
      // Fallback: treat as legacy raw reading
      latest = response;
      consecutiveErrors = 0;
      hideErrorBanner();
      setConnUI(true, `${connection?.port || '—'} · ${connection?.baudrate || 19200} ${connection?.parity || 'N'}81`, '');
    }
    
    syncBandSelectionFromLatest();
    pushHistoryPoint(latest);
    updateKpis();
    updateConnectionStatus();

    if (activeTab === 'overview'){
      try {
        renderParamGrid();
        renderBandList();
        renderBandDetail();
        renderFrequencySnapshot();
        updateCharts();
      } catch (renderError) {
        console.error('Render error in overview:', renderError);
      }
    }

    if (activeTab === 'health'){
      try {
        renderHealthParamGrid();
        renderHealthDetailFromLatest();
        renderHealthBandsTable();
        renderHealthBandSelector();
        renderHealthBandMetrics();
        renderAllBandsSnapshot();
        renderSpectrum();
        appendHealthLatest();
      } catch (renderError) {
        console.error('Render error in health:', renderError);
      }
    }

    if (activeTab === 'system'){
      try {
        renderSystemInfo();
      } catch (renderError) {
        console.error('Render error in system:', renderError);
      }
    }
  }catch(e){
    consecutiveErrors++;
    lastError = e.message || 'Network error';
    lastErrorTime = new Date().toISOString();
    showErrorBanner(e.message || 'Failed to fetch data – check connection', true);
    setConnUI(false, '', 'No readings');
    updateConnectionStatus();
  }
}

function startPolling(){
  console.log('[GANDIVA] startPolling called');
  const tickLatest = async () => {
    const t0 = performance.now();
    await refreshLatest();
    const dt = performance.now() - t0;
    // Poll latest reading more frequently so ML results feel responsive
    setTimeout(tickLatest, Math.max(0, 500 - dt));
  };
  tickLatest();

  const tickAlerts = async () => {
    const t0 = performance.now();
    await refreshAlerts();
    const dt = performance.now() - t0;
    setTimeout(tickAlerts, Math.max(0, 1500 - dt));
  };
  tickAlerts();
}

async function refreshThresholds(){
  try{
    thresholds = await apiGet('/api/thresholds');

    // Normalize scalar thresholds to numbers
    thresholds.z_rms_mm_s_warning = Number(thresholds.z_rms_mm_s_warning || 0);
    thresholds.z_rms_mm_s_alarm = Number(thresholds.z_rms_mm_s_alarm || 0);
    thresholds.x_rms_mm_s_warning = Number(thresholds.x_rms_mm_s_warning || 0);
    thresholds.x_rms_mm_s_alarm = Number(thresholds.x_rms_mm_s_alarm || 0);
    thresholds.temp_c_warning = Number(thresholds.temp_c_warning || 0);
    thresholds.temp_c_alarm = Number(thresholds.temp_c_alarm || 0);

    qs('th_z_warn').value = thresholds.z_rms_mm_s_warning;
    qs('th_z_alarm').value = thresholds.z_rms_mm_s_alarm;
    qs('th_x_warn').value = thresholds.x_rms_mm_s_warning;
    qs('th_x_alarm').value = thresholds.x_rms_mm_s_alarm;
    qs('th_t_warn').value = thresholds.temp_c_warning;
    qs('th_t_alarm').value = thresholds.temp_c_alarm;

    // Ensure band thresholds are normalized (numeric band_number and numeric fields)
    thresholds.band_thresholds = (thresholds.band_thresholds || []).map(bt => ({
      axis: bt.axis,
      band_number: Number(bt.band_number),
      total_rms_warning: Number(bt.total_rms_warning || 0),
      total_rms_alarm: Number(bt.total_rms_alarm || 0),
      peak_rms_warning: Number(bt.peak_rms_warning || 0),
      peak_rms_alarm: Number(bt.peak_rms_alarm || 0),
    }));

    loadBandEditorFromThresholds();
    afterThresholdsChanged();
  }catch(e){
  }
}

async function refreshConnection(){
  try{
    connection = await apiGet('/api/connection');
    qs('port').value = connection.port;
    qs('slaveId').value = connection.slave_id;
    qs('baudrate').value = connection.baudrate;
    qs('parity').value = connection.parity;
  }catch(e){
  }
}

async function refreshAlerts(){
  try{
    alerts = await apiGet('/api/alerts');
    renderAlertsTable();
    updateKpis();
  }catch(e){
  }
}

async function hydrateMlPredictionIfMissing(){
  if (!latest || latest.ml_prediction){
    return;
  }
  try{
    const probe = await apiGet('/api/ml/test');
    if (probe?.prediction){
      latest.ml_prediction = probe.prediction;
      if (!latest.train_state && probe.train_state){
        latest.train_state = probe.train_state;
      }
    }
  }catch(e){
    // Ignore – ML might genuinely be unavailable
  }
}

async function refreshMLStatus(){
  mlStatus = { loading: true };
  renderMLStatus();
  try{
    mlStatus = await apiGet('/ml_status');
    renderMLStatus();
  }catch(e){
    // Show failure in the panel but don't break the rest of the UI
    mlStatus = { error: e.message || 'Failed to query /ml_status' };
    renderMLStatus();
  }
}

function renderMLStatus(){
  const kv = qs('mlStatusKv');
  if (!kv) return;

  if (!mlStatus){
    kv.innerHTML = '<div class="kvRow"><div class="kvKey">Status</div><div class="kvVal">Not checked</div></div>';
    return;
  }

  if (mlStatus.loading){
    kv.innerHTML = '<div class="kvRow"><div class="kvKey">Status</div><div class="kvVal">Refreshing...</div></div>';
    return;
  }

  if (mlStatus.error){
    kv.innerHTML = `<div class="kvRow"><div class="kvKey">Status</div><div class="kvVal">Error: ${mlStatus.error}</div></div>`;
    return;
  }

  const loaded = mlStatus.model_loaded ?? mlStatus.loaded;
  const scalerLoaded = mlStatus.scaler_loaded ?? false;
  const classes = mlStatus.classes || Object.values(mlStatus.class_labels || {});

  kv.innerHTML = `
    <div class="kvRow"><div class="kvKey">Model loaded</div><div class="kvVal">${loaded ? 'Yes' : 'No'}</div></div>
    <div class="kvRow"><div class="kvKey">Scaler loaded</div><div class="kvVal">${scalerLoaded ? 'Yes' : 'No'}</div></div>
    <div class="kvRow"><div class="kvKey">Model path</div><div class="kvVal">${mlStatus.model_path || mlStatus.model_file || 'n/a'}</div></div>
    <div class="kvRow"><div class="kvKey">Classes</div><div class="kvVal">${classes.join(', ') || 'n/a'}</div></div>
  `;
}

async function scanPorts(){
  const tbody = qs('portsTable').querySelector('tbody');
  tbody.innerHTML = '<tr><td colspan="3" class="muted">Scanning...</td></tr>';
  try{
    const ports = await apiGet('/api/ports/scan');
    if (!ports.length){
      tbody.innerHTML = '<tr><td colspan="3" class="muted">No ports found. Ensure your sensor/USB adapter is plugged in and recognised in Windows Device Manager. You can still type a port name (e.g. COM5) in the manual connection box and click Apply.</td></tr>';
      return;
    }
    tbody.innerHTML = '';
    for (const p of ports){
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${p.port}</td>
        <td>${p.description || ''}</td>
        <td><button class="btn btn--primary" data-connect="${p.port}">Connect</button></td>
      `;
      tbody.appendChild(tr);
    }
    tbody.querySelectorAll('[data-connect]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const port = btn.getAttribute('data-connect');
        const slave = Number(qs('autoSlaveId').value || 1);
        await connect({ port, slave_id: slave, baudrate: 19200, bytesize: 8, parity: 'N', stopbits: 1, timeout_s: 3.0 });
      })
    })
  }catch(e){
    tbody.innerHTML = `<tr><td colspan="3" class="muted">${String(e.message || e)}</td></tr>`;
  }
}

async function connect(cfg){
  try{
    const r = await apiPost('/api/ports/connect', cfg);
    connection = r.connection;
    await refreshLatest();
  }catch(e){
    setConnUI(false, '', 'Connect failed');
  }
}

qs('scanPortsBtn').addEventListener('click', scanPorts);
qs('applyConnBtn').addEventListener('click', async () => {
  const cfg = {
    port: qs('port').value,
    slave_id: Number(qs('slaveId').value || 1),
    baudrate: Number(qs('baudrate').value || 19200),
    bytesize: 8,
    parity: qs('parity').value,
    stopbits: 1,
    timeout_s: 3.0
  };
  await connect(cfg);
});

qs('axisZ').addEventListener('click', () => setOverviewAxis('z'));
qs('axisX').addEventListener('click', () => setOverviewAxis('x'));

qs('healthAxisZ').addEventListener('click', () => setHealthAxis('z'));
qs('healthAxisX').addEventListener('click', () => setHealthAxis('x'));
qs('spectrumAxisZ')?.addEventListener('click', () => setHealthAxis('z'));
qs('spectrumAxisX')?.addEventListener('click', () => setHealthAxis('x'));
qs('bandAxisZ')?.addEventListener('click', () => setHealthAxis('z'));
qs('bandAxisX')?.addEventListener('click', () => setHealthAxis('x'));
qs('mlStatusRefreshBtn')?.addEventListener('click', refreshMLStatus);

qs('healthBandNum')?.addEventListener('change', () => {
  const v = Number(qs('healthBandNum').value);
  if (!Number.isFinite(v)) return;
  selectedHealthBand = v;
  selectedAxis = selectedAxisHealth;
  selectedBand = v;
  renderHealthBandsTable();
  renderHealthBandSelector();
  renderHealthBandMetrics();
  renderAllBandsSnapshot();
  renderSpectrum();
  renderBandList();
  renderBandDetail();
  refreshHealthHistory();
});

qs('healthWindow')?.addEventListener('change', refreshHealthHistory);

function loadBandEditorFromThresholds(){
  if (!thresholds) return;
  const axis = qs('bandAxisSelect').value;
  const n = Number(qs('bandNumSelect').value || 1);
  const bt = (thresholds.band_thresholds || []).find(b => b.axis === axis && Number(b.band_number) === n);
  qs('band_total_warn').value = bt ? bt.total_rms_warning : 0;
  qs('band_total_alarm').value = bt ? bt.total_rms_alarm : 0;
  qs('band_peak_warn').value = bt ? bt.peak_rms_warning : 0;
  qs('band_peak_alarm').value = bt ? bt.peak_rms_alarm : 0;
}

function setupThresholdBindings(){
  _updateScalarThresholdFromInput('th_z_warn', 'z_rms_mm_s_warning');
  _updateScalarThresholdFromInput('th_z_alarm', 'z_rms_mm_s_alarm');
  _updateScalarThresholdFromInput('th_x_warn', 'x_rms_mm_s_warning');
  _updateScalarThresholdFromInput('th_x_alarm', 'x_rms_mm_s_alarm');
  _updateScalarThresholdFromInput('th_t_warn', 'temp_c_warning');
  _updateScalarThresholdFromInput('th_t_alarm', 'temp_c_alarm');

  qs('band_total_warn')?.addEventListener('input', () => _updateBandThresholdFromEditor({ total_rms_warning: Number(qs('band_total_warn').value || 0) }));
  qs('band_total_alarm')?.addEventListener('input', () => _updateBandThresholdFromEditor({ total_rms_alarm: Number(qs('band_total_alarm').value || 0) }));
  qs('band_peak_warn')?.addEventListener('input', () => _updateBandThresholdFromEditor({ peak_rms_warning: Number(qs('band_peak_warn').value || 0) }));
  qs('band_peak_alarm')?.addEventListener('input', () => _updateBandThresholdFromEditor({ peak_rms_alarm: Number(qs('band_peak_alarm').value || 0) }));
}

function _updateScalarThresholdFromInput(id, key){
  const el = qs(id);
  if (!el) return;
  el.addEventListener('input', () => {
    _ensureThresholds();
    thresholds[key] = Number(el.value || 0);
    afterThresholdsChanged();
  });
}

function _updateBandThresholdFromEditor(partial){
  _ensureThresholds();
  const axis = qs('bandAxisSelect')?.value;
  const n = Number(qs('bandNumSelect')?.value || 1);
  if (!axis || !Number.isFinite(n)) return;

  const prev = (thresholds.band_thresholds || []).find(b => b.axis === axis && Number(b.band_number) === n);
  const next = {
    band_number: Number(n),
    axis,
    total_rms_warning: prev ? Number(prev.total_rms_warning) : 0,
    total_rms_alarm: prev ? Number(prev.total_rms_alarm) : 0,
    peak_rms_warning: prev ? Number(prev.peak_rms_warning) : 0,
    peak_rms_alarm: prev ? Number(prev.peak_rms_alarm) : 0,
    ...partial,
  };
  thresholds.band_thresholds = (thresholds.band_thresholds || []).filter(b => !(b.axis === axis && Number(b.band_number) === n));
  thresholds.band_thresholds.push(next);
  afterThresholdsChanged();
}

qs('bandAxisSelect').addEventListener('change', loadBandEditorFromThresholds);
qs('bandNumSelect').addEventListener('change', loadBandEditorFromThresholds);

qs('applyBandBtn').addEventListener('click', () => {
  _updateBandThresholdFromEditor({
    total_rms_warning: Number(qs('band_total_warn').value || 0),
    total_rms_alarm: Number(qs('band_total_alarm').value || 0),
    peak_rms_warning: Number(qs('band_peak_warn').value || 0),
    peak_rms_alarm: Number(qs('band_peak_alarm').value || 0),
  });
});

qs('applyAllBtn').addEventListener('click', () => {
  _ensureThresholds();
  const axis = qs('bandAxisSelect').value;
  const next = {
    total_rms_warning: Number(qs('band_total_warn').value || 0),
    total_rms_alarm: Number(qs('band_total_alarm').value || 0),
    peak_rms_warning: Number(qs('band_peak_warn').value || 0),
    peak_rms_alarm: Number(qs('band_peak_alarm').value || 0)
  };
  thresholds.band_thresholds = (thresholds.band_thresholds || []).filter(b => b.axis !== axis);
  for (let i=1;i<=20;i++){
    thresholds.band_thresholds.push({ band_number:i, axis, ...next });
  }
  afterThresholdsChanged();
});

qs('saveThresholdsBtn').addEventListener('click', async () => {
  _ensureThresholds();
  thresholds.z_rms_mm_s_warning = Number(qs('th_z_warn').value || 0);
  thresholds.z_rms_mm_s_alarm = Number(qs('th_z_alarm').value || 0);
  thresholds.x_rms_mm_s_warning = Number(qs('th_x_warn').value || 0);
  thresholds.x_rms_mm_s_alarm = Number(qs('th_x_alarm').value || 0);
  thresholds.temp_c_warning = Number(qs('th_t_warn').value || 0);
  thresholds.temp_c_alarm = Number(qs('th_t_alarm').value || 0);

  const msg = validateThresholds(thresholds);
  if (msg){
    alert(msg);
    return;
  }

  try{
    await apiPost('/api/thresholds', thresholds);
    await refreshThresholds();
  }catch(e){
    alert(String(e.message || e));
  }
});

// ML model reload button (System tab)
const reloadModelBtn = qs('reloadModelBtn');
if (reloadModelBtn){
  reloadModelBtn.addEventListener('click', async () => {
    try{
      reloadModelBtn.disabled = true;
      reloadModelBtn.textContent = 'Reloading...';
      const res = await apiPostWithErrorHandling('/ml/reload', {});
      const ok = !!res?.ok && !!res?.model_loaded;
      reloadModelBtn.textContent = ok ? 'Model Reloaded' : 'Reload Failed';
      await refreshMLStatus();
      setTimeout(() => {
        reloadModelBtn.disabled = false;
        reloadModelBtn.textContent = 'Reload ML Model';
      }, 2000);
    }catch(e){
      console.error('Failed to reload ML model', e);
      reloadModelBtn.disabled = false;
      reloadModelBtn.textContent = 'Reload ML Model';
      alert('Failed to reload ML model. See console for details.');
    }
  });
}

qs('exportCsvBtn').addEventListener('click', () => {
  const url = API('/api/alerts/csv?since_seconds=86400');
  window.open(url, '_blank');
});

qs('toggleSoundBtn').addEventListener('click', async () => {
  try{
    const st = await apiGet('/api/sound');
    const next = !st.enabled;
    await apiPost('/api/sound', { enabled: next });
    const st2 = await apiGet('/api/sound');
    qs('soundState').textContent = `Sound: ${st2.enabled ? 'enabled' : 'disabled'}`;
  }catch(e){
    qs('soundState').textContent = 'Sound: unavailable';
  }
});

qs('testBeepBtn').addEventListener('click', async () => {
  try{
    await apiPost('/api/test-beep', {});
  }catch(e){}
});

async function boot(){
  await refreshConnection();
  setupThresholdBindings();
  await refreshThresholds();
  await refreshAlerts();
  try{
    const st = await apiGet('/api/sound');
    qs('soundState').textContent = `Sound: ${st.enabled ? 'enabled' : 'disabled'}`;
  }catch(e){
    qs('soundState').textContent = 'Sound: unavailable';
  }
  initCharts();
  initHealthChart();
  initSpectrumChart();
  initBandAnalysisCharts();
  initMLInsightsCharts();
  setupHelpModal();
  setupMobileNav();

  qs('logsRefreshBtn')?.addEventListener('click', refreshLogs);
  qs('logsPrevBtn')?.addEventListener('click', () => { logsPage -= 1; renderLogsPage(); });
  qs('logsNextBtn')?.addEventListener('click', () => { logsPage += 1; renderLogsPage(); });
  qs('logsWindow')?.addEventListener('change', refreshLogs);

  await refreshLatest();
  setHealthSelection(selectedHealthParam);
  setHealthAxis(selectedAxisHealth);
  await refreshLogs();
  await refreshMLStatus();
  
  // Initialize ML Insights and Datasets
  initMLInsights();
  initDatasets();
  
  startPolling();
}

boot();

// ============================================
// PREMIUM ML INSIGHTS TAB FUNCTIONALITY
// ============================================

let chartMlDistribution = null;
let chartMlConfidence = null;
let mlPredictionHistory = [];
let mlStats = { normal: 0, gap: 0, crack: 0, total: 0 };

function initMLInsightsCharts() {
  const distEl = qs('chartMlDistribution');
  const confEl = qs('chartMlConfidence');
  
  if (distEl) {
    chartMlDistribution = new Chart(distEl, {
      type: 'doughnut',
      data: {
        labels: ['Normal', 'Expansion Gap', 'Crack'],
        datasets: [{
          data: [0, 0, 0],
          backgroundColor: [
            'rgba(70, 230, 139, 0.85)',
            'rgba(244, 180, 0, 0.85)',
            'rgba(239, 68, 68, 0.85)'
          ],
          borderColor: [
            'rgba(70, 230, 139, 1)',
            'rgba(244, 180, 0, 1)',
            'rgba(239, 68, 68, 1)'
          ],
          borderWidth: 2,
          hoverOffset: 8
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '65%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: 'rgba(232,237,247,.75)',
              padding: 20,
              usePointStyle: true,
              pointStyle: 'circle'
            }
          }
        }
      }
    });
  }
  
  if (confEl) {
    chartMlConfidence = new Chart(confEl, {
      type: 'bar',
      data: {
        labels: ['High (>80%)', 'Medium (50-80%)', 'Low (<50%)'],
        datasets: [{
          label: 'Predictions',
          data: [0, 0, 0],
          backgroundColor: [
            'rgba(70, 230, 139, 0.75)',
            'rgba(244, 180, 0, 0.75)',
            'rgba(239, 68, 68, 0.75)'
          ],
          borderRadius: 8,
          borderWidth: 0,
          barThickness: 24
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y',
        plugins: { legend: { display: false } },
        scales: {
          x: { 
            ticks: { color: 'rgba(232,237,247,.5)' },
            grid: { color: 'rgba(255,255,255,.04)' }
          },
          y: { 
            ticks: { color: 'rgba(232,237,247,.6)', font: { weight: 600 } },
            grid: { display: false }
          }
        }
      }
    });
  }
}

function initMLInsights() {
  // Event listeners for ML Insights tab
  qs('mlRefreshBtn')?.addEventListener('click', refreshMLInsights);
  qs('mlReloadBtn2')?.addEventListener('click', reloadMLModel);
  qs('mlCaptureBtn')?.addEventListener('click', openCaptureModal);
  
  // Initial load when tab is active
  if (activeTab === 'mlinsights') {
    refreshMLInsights();
  }
}

async function refreshMLInsights() {
  try {
    // Get ML realtime stats from API
    const resp = await apiGet('/api/ml/realtime-stats');
    const stats = resp.data || resp;
    
    // Extract class distribution
    const classDist = stats.class_distribution || {};
    mlStats.normal = classDist['normal'] || 0;
    mlStats.gap = classDist['expansion_gap'] || 0;
    mlStats.crack = classDist['crack'] || 0;
    mlStats.total = mlStats.normal + mlStats.gap + mlStats.crack;
    
    // Update stat cards with counts
    qs('mlNormalCount').textContent = mlStats.normal;
    qs('mlGapCount').textContent = mlStats.gap;
    qs('mlCrackCount').textContent = mlStats.crack;
    qs('mlTotalCount').textContent = mlStats.total;
    
    // Calculate and update percentages
    const normalPct = mlStats.total > 0 ? (mlStats.normal / mlStats.total * 100).toFixed(1) : 0;
    const gapPct = mlStats.total > 0 ? (mlStats.gap / mlStats.total * 100).toFixed(1) : 0;
    const crackPct = mlStats.total > 0 ? (mlStats.crack / mlStats.total * 100).toFixed(1) : 0;
    
    qs('mlNormalPercent').textContent = `${normalPct}%`;
    qs('mlGapPercent').textContent = `${gapPct}%`;
    qs('mlCrackPercent').textContent = `${crackPct}%`;
    
    // Update ring charts
    updateStatRing('ringNormal', normalPct);
    updateStatRing('ringGap', gapPct);
    updateStatRing('ringCrack', crackPct);
    
    // Average confidence
    const avgConf = stats.average_confidence ? (stats.average_confidence * 100).toFixed(1) : 0;
    qs('mlAvgConfidence').textContent = `Avg: ${avgConf}%`;
    
    // Update charts
    if (chartMlDistribution) {
      chartMlDistribution.data.datasets[0].data = [mlStats.normal, mlStats.gap, mlStats.crack];
      chartMlDistribution.update('none');
    }
    
    if (chartMlConfidence) {
      const confDist = stats.confidence_distribution || {};
      chartMlConfidence.data.datasets[0].data = [
        confDist['high'] || 0,
        confDist['medium'] || 0,
        confDist['low'] || 0
      ];
      chartMlConfidence.update('none');
    }
    
    // Update predictions table
    const predictions = stats.recent_predictions || [];
    renderMLPredictionsTable(predictions);
    qs('predictionCountBadge').textContent = `${predictions.length} predictions`;
    
    // Update hero section from latest sensor data
    updateMLHero();
    
    // Update model info
    await refreshMLModelInfo();
    
  } catch (e) {
    console.error('Failed to refresh ML insights:', e);
  }
}

function updateStatRing(id, percentage) {
  const ring = document.getElementById(id);
  if (ring) {
    ring.setAttribute('stroke-dasharray', `${percentage}, 100`);
  }
}

function updateMLHero() {
  // Use the latest sensor reading
  if (latest && latest.ml_prediction) {
    const pred = latest.ml_prediction;
    const label = pred.label || 'unknown';
    const conf = pred.confidence || 0;
    
    // Update prediction text
    const predEl = qs('mlHeroPrediction');
    if (predEl) {
      predEl.textContent = label.replace('_', ' ').toUpperCase();
      predEl.className = 'ml-hero__prediction' + 
        (label === 'crack' ? ' is-alert' : label === 'expansion_gap' ? ' is-warn' : '');
    }
    
    // Update icon state
    const iconEl = qs('mlHeroIcon');
    if (iconEl) {
      iconEl.className = 'ml-hero__icon' + 
        (label === 'crack' ? ' is-alert' : label === 'expansion_gap' ? ' is-warn' : '');
    }
    
    // Update confidence
    qs('mlHeroConfidence').innerHTML = `<i data-lucide="target"></i> Confidence: ${(conf * 100).toFixed(1)}%`;
    
    // Update time
    const timeStr = latest.timestamp ? new Date(latest.timestamp).toLocaleTimeString() : 'Now';
    qs('mlHeroTime').innerHTML = `<i data-lucide="clock"></i> Last: ${timeStr}`;
    
    if (window.lucide) lucide.createIcons();
  }
}

function renderMLPredictionsTable(predictions) {
  const tbody = document.querySelector('#mlPredictionsTable tbody');
  if (!tbody) return;
  
  if (!predictions || predictions.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" class="muted" style="text-align:center;padding:32px">No predictions yet. Connect sensor to start capturing ML predictions.</td></tr>';
    return;
  }
  
  tbody.innerHTML = predictions.slice(0, 20).map(p => {
    const labelClass = p.label === 'crack' ? 'is-crack' : 
                       p.label === 'expansion_gap' ? 'is-gap' : 'is-normal';
    const confPct = ((p.confidence || 0) * 100).toFixed(1);
    const timestamp = p.timestamp ? new Date(p.timestamp).toLocaleTimeString() : '—';
    
    return `
      <tr>
        <td>${timestamp}</td>
        <td><span class="label-tag ${labelClass}">${(p.label || '—').replace('_', ' ')}</span></td>
        <td>${confPct}%</td>
        <td>${fmt(p.z_rms, 3)}</td>
        <td>${fmt(p.x_rms, 3)}</td>
        <td>${fmt(p.temp, 1)}°C</td>
      </tr>
    `;
  }).join('');
}

async function refreshMLModelInfo() {
  try {
    const status = await apiGet('/ml_status');
    
    // Update model status
    const statusText = status.model_loaded ? 'Loaded & Active' : 'Not Loaded';
    qs('mlModelStatus').textContent = statusText;
    
    const statusIcon = qs('modelStatusIcon');
    if (statusIcon) {
      statusIcon.className = 'model-item__icon ' + (status.model_loaded ? 'is-success' : '');
    }
    
    // Update scaler status
    const scalerText = status.scaler_loaded ? 'Active' : 'Not Loaded';
    qs('mlScalerStatus').textContent = scalerText;
    
    const scalerIcon = qs('scalerStatusIcon');
    if (scalerIcon) {
      scalerIcon.className = 'model-item__icon ' + (status.scaler_loaded ? 'is-success' : '');
    }
    
  } catch (e) {
    console.error('Failed to get ML model info:', e);
    qs('mlModelStatus').textContent = 'Error';
  }
}

async function reloadMLModel() {
  const btn = qs('mlReloadBtn2');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i data-lucide="loader" class="btn__icon spin"></i>Reloading...';
  }
  
  try {
    await apiPost('/reload_model', {});
    showToast('ML model reloaded successfully', 'success');
    await refreshMLModelInfo();
  } catch (e) {
    console.error('Failed to reload ML model:', e);
    showToast('Failed to reload ML model', 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<i data-lucide="refresh-cw" class="btn__icon"></i>Reload Model';
      if (window.lucide) lucide.createIcons();
    }
  }
}

// ============================================
// PREMIUM DATASETS TAB FUNCTIONALITY
// ============================================

let datasetsData = [];
let currentDataset = null;
let datasetPage = 0;
const DATASET_PAGE_SIZE = 50;
let chartDatasetLabels = null;

function initDatasets() {
  // Dataset event listeners
  qs('refreshDatasetsBtn')?.addEventListener('click', refreshDatasets);
  qs('captureDataBtn')?.addEventListener('click', openCaptureModal);
  qs('deleteDatasetBtn')?.addEventListener('click', deleteCurrentDataset);
  qs('datasetPrevBtn')?.addEventListener('click', () => {
    if (datasetPage > 0) {
      datasetPage--;
      loadDatasetPage();
    }
  });
  qs('datasetNextBtn')?.addEventListener('click', () => {
    datasetPage++;
    loadDatasetPage();
  });
  
  // Capture modal event listeners
  qs('confirmCaptureBtn')?.addEventListener('click', confirmCaptureSample);
  
  // Initial load
  if (activeTab === 'datasets') {
    refreshDatasets();
  }
}

async function refreshDatasets() {
  const container = qs('datasetsList');
  if (container) {
    container.innerHTML = `<div class="ds-empty"><i data-lucide="loader" class="spin"></i><h3>Loading Datasets...</h3><p>Scanning data directory</p></div>`;
    if (window.lucide) lucide.createIcons();
  }
  
  try {
    const resp = await apiGet('/api/datasets');
    datasetsData = resp.data || [];
    
    // Update stats
    qs('totalDatasetsCount').textContent = datasetsData.length;
    
    let totalRows = 0;
    let totalSize = 0;
    let uniqueLabels = new Set();
    
    datasetsData.forEach(d => {
      totalRows += d.row_count || 0;
      totalSize += d.size_bytes || 0;
      if (d.label_counts) {
        Object.keys(d.label_counts).forEach(l => uniqueLabels.add(l));
      }
    });
    
    qs('totalRowsCount').textContent = totalRows.toLocaleString();
    qs('totalSizeCount').textContent = formatFileSize(totalSize);
    qs('totalLabelsCount').textContent = uniqueLabels.size;
    
    // Render dataset grid
    renderDatasetsGrid();
    
  } catch (e) {
    console.error('Failed to refresh datasets:', e);
    if (container) {
      container.innerHTML = `<div class="ds-empty"><i data-lucide="alert-circle"></i><h3>Failed to Load</h3><p>${e.message || 'Could not connect to server'}</p></div>`;
      if (window.lucide) lucide.createIcons();
    }
  }
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function renderDatasetsGrid() {
  const container = qs('datasetsList');
  if (!container) return;
  
  if (!datasetsData || datasetsData.length === 0) {
    container.innerHTML = `
      <div class="ds-empty">
        <i data-lucide="folder-open"></i>
        <h3>No Datasets Found</h3>
        <p>No CSV files in the data directory. Capture training samples to create datasets.</p>
      </div>
    `;
    if (window.lucide) lucide.createIcons();
    return;
  }
  
  container.innerHTML = datasetsData.map(d => {
    const labelTags = d.label_counts ? Object.entries(d.label_counts).map(([label, count]) => {
      const cls = label === 'crack' ? 'is-crack' : label === 'expansion_gap' ? 'is-gap' : 'is-normal';
      return `<span class="label-tag ${cls}">${label}: ${count}</span>`;
    }).join('') : '<span class="muted">No labels</span>';
    
    const modified = d.modified_at ? new Date(d.modified_at).toLocaleDateString() : '—';
    
    return `
      <div class="ds-card" onclick="openDatasetPreview('${d.filename}')">
        <div class="ds-card__head">
          <div class="ds-card__icon"><i data-lucide="file-spreadsheet"></i></div>
          <div>
            <div class="ds-card__title">${d.filename}</div>
            <div class="ds-card__meta">Modified: ${modified}</div>
          </div>
        </div>
        <div class="ds-card__stats">
          <div class="ds-card__stat">
            <div class="ds-card__stat-value">${(d.row_count || 0).toLocaleString()}</div>
            <div class="ds-card__stat-label">Rows</div>
          </div>
          <div class="ds-card__stat">
            <div class="ds-card__stat-value">${d.column_count || '—'}</div>
            <div class="ds-card__stat-label">Columns</div>
          </div>
          <div class="ds-card__stat">
            <div class="ds-card__stat-value">${formatFileSize(d.size_bytes)}</div>
            <div class="ds-card__stat-label">Size</div>
          </div>
        </div>
        <div class="ds-card__labels">${labelTags}</div>
      </div>
    `;
  }).join('');
  
  if (window.lucide) lucide.createIcons();
}

async function openDatasetPreview(filename) {
  currentDataset = filename;
  datasetPage = 0;
  
  qs('previewFilename').textContent = filename;
  qs('datasetPreview').style.display = 'flex';
  
  // Initialize label chart if needed
  if (!chartDatasetLabels) {
    const el = qs('chartDatasetLabels');
    if (el) {
      chartDatasetLabels = new Chart(el, {
        type: 'bar',
        data: {
          labels: [],
          datasets: [{
            label: 'Count',
            data: [],
            backgroundColor: ['rgba(70,230,139,.8)', 'rgba(244,180,0,.8)', 'rgba(239,68,68,.8)', 'rgba(110,168,254,.8)'],
            borderRadius: 6,
            borderWidth: 0,
            barThickness: 32
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { ticks: { color: 'rgba(232,237,247,.6)' }, grid: { display: false } },
            y: { ticks: { color: 'rgba(232,237,247,.5)' }, grid: { color: 'rgba(255,255,255,.05)' } }
          }
        }
      });
    }
  }
  
  await loadDatasetPage();
}

function closeDatasetPreview() {
  qs('datasetPreview').style.display = 'none';
  currentDataset = null;
}

async function loadDatasetPage() {
  if (!currentDataset) return;
  
  try {
    const offset = datasetPage * DATASET_PAGE_SIZE;
    const resp = await apiGet(`/api/datasets/${currentDataset}?limit=${DATASET_PAGE_SIZE}&offset=${offset}`);
    const data = resp.data || {};
    
    // Update info
    const info = data.info || {};
    qs('previewInfo').textContent = `${(info.row_count || 0).toLocaleString()} rows · ${info.columns?.length || 0} columns`;
    
    // Update label chart
    if (chartDatasetLabels && info.label_counts) {
      chartDatasetLabels.data.labels = Object.keys(info.label_counts);
      chartDatasetLabels.data.datasets[0].data = Object.values(info.label_counts);
      chartDatasetLabels.update('none');
    }
    
    // Render table
    renderDatasetTable(data.rows || [], info.columns || []);
    
    // Update pagination
    const totalRows = data.total_rows || 0;
    const pageNum = datasetPage + 1;
    const totalPages = Math.ceil(totalRows / DATASET_PAGE_SIZE) || 1;
    qs('datasetPageInfo').textContent = `Page ${pageNum} of ${totalPages}`;
    
    qs('datasetPrevBtn').disabled = datasetPage === 0;
    qs('datasetNextBtn').disabled = !data.has_more;
    
  } catch (e) {
    console.error('Failed to load dataset page:', e);
    showToast('Failed to load dataset', 'error');
  }
}

function renderDatasetTable(rows, columns) {
  const thead = document.querySelector('#datasetPreviewTable thead');
  const tbody = document.querySelector('#datasetPreviewTable tbody');
  
  if (!thead || !tbody) return;
  
  // Render header
  thead.innerHTML = '<tr>' + columns.map(c => `<th>${c}</th>`).join('') + '</tr>';
  
  // Render rows
  if (!rows || rows.length === 0) {
    tbody.innerHTML = `<tr><td colspan="${columns.length}" class="muted" style="text-align:center;padding:32px">No data available</td></tr>`;
    return;
  }
  
  tbody.innerHTML = rows.map(row => {
    return '<tr>' + columns.map(c => {
      let val = row[c];
      if (typeof val === 'number') {
        val = Number.isInteger(val) ? val : val.toFixed(4);
      }
      if (c === 'label' && val) {
        const cls = val === 'crack' ? 'is-crack' : val === 'expansion_gap' ? 'is-gap' : 'is-normal';
        return `<td><span class="label-tag ${cls}">${val}</span></td>`;
      }
      return `<td>${val ?? '—'}</td>`;
    }).join('') + '</tr>';
  }).join('');
}

async function deleteCurrentDataset() {
  if (!currentDataset) return;
  
  if (!confirm(`Are you sure you want to delete "${currentDataset}"? This cannot be undone.`)) return;
  
  try {
    await apiDelete(`/api/datasets/${currentDataset}`);
    showToast('Dataset deleted successfully', 'success');
    closeDatasetPreview();
    await refreshDatasets();
  } catch (e) {
    console.error('Failed to delete dataset:', e);
    showToast('Failed to delete dataset', 'error');
  }
}

// ============================================
// CAPTURE TRAINING SAMPLE FUNCTIONALITY
// ============================================

function openCaptureModal() {
  // Populate current sensor values
  if (latest) {
    qs('captureZRms').textContent = latest.z_rms_mm_s ? latest.z_rms_mm_s.toFixed(3) : '—';
    qs('captureXRms').textContent = latest.x_rms_mm_s ? latest.x_rms_mm_s.toFixed(3) : '—';
    qs('captureTemp').textContent = latest.temperature_c ? `${latest.temperature_c.toFixed(1)}°C` : '—';
  } else {
    qs('captureZRms').textContent = '—';
    qs('captureXRms').textContent = '—';
    qs('captureTemp').textContent = '—';
  }
  
  // Reset form
  qs('captureLabel').value = 'normal';
  qs('captureNotes').value = '';
  
  // Show modal
  qs('captureModal').style.display = 'flex';
}

function closeCaptureModal() {
  qs('captureModal').style.display = 'none';
}

async function confirmCaptureSample() {
  const label = qs('captureLabel').value;
  const notes = qs('captureNotes').value || '';
  
  if (!latest) {
    showToast('No sensor data available to capture', 'error');
    return;
  }
  
  const btn = qs('confirmCaptureBtn');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i data-lucide="loader" class="btn__icon spin"></i>Saving...';
  }
  
  try {
    // Build sample data from current sensor reading
    const sample = {
      z_rms: latest.z_rms_mm_s || 0,
      x_rms: latest.x_rms_mm_s || 0,
      temperature: latest.temperature_c || 0,
      z_peak: latest.z_peak_mm_s || 0,
      x_peak: latest.x_peak_mm_s || 0,
      label: label,
      notes: notes,
      timestamp: new Date().toISOString()
    };
    
    // Add band energy data if available
    if (latest.z_band_energy) {
      sample.z_band_energy = latest.z_band_energy;
    }
    if (latest.x_band_energy) {
      sample.x_band_energy = latest.x_band_energy;
    }
    
    // Send to API
    const resp = await apiPost('/api/training/capture', sample);
    
    showToast(`Sample captured with label: ${label}`, 'success');
    closeCaptureModal();
    
    // Refresh datasets if on that tab
    if (activeTab === 'datasets') {
      await refreshDatasets();
    }
    
  } catch (e) {
    console.error('Failed to capture sample:', e);
    showToast('Failed to capture sample: ' + (e.message || 'Unknown error'), 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<i data-lucide="save" class="btn__icon"></i>Save Sample';
      if (window.lucide) lucide.createIcons();
    }
  }
}

// Helper for DELETE requests
async function apiDelete(url) {
  const resp = await fetch(API(url), { method: 'DELETE' });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || 'Request failed');
  }
  return resp.json();
}
