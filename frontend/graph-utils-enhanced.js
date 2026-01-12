/**
 * ============================================================================
 * GANDIVA LEVEL 10 - ENHANCED GRAPH UTILITIES
 * Professional Chart.js initialization, error handling, and animations
 * ============================================================================
 */

// ============================================================================
// CHART.JS CONFIGURATION
// ============================================================================

// Professional color palette
const CHART_COLORS = {
  primary: 'rgba(51, 221, 200, 1)',
  primaryLight: 'rgba(51, 221, 200, 0.6)',
  primaryFill: 'rgba(51, 221, 200, 0.1)',
  secondary: 'rgba(59, 130, 246, 1)',
  secondaryLight: 'rgba(59, 130, 246, 0.6)',
  secondaryFill: 'rgba(59, 130, 246, 0.1)',
  success: 'rgba(70, 230, 139, 1)',
  successLight: 'rgba(70, 230, 139, 0.6)',
  successFill: 'rgba(70, 230, 139, 0.1)',
  warning: 'rgba(244, 180, 0, 1)',
  warningLight: 'rgba(244, 180, 0, 0.6)',
  warningFill: 'rgba(244, 180, 0, 0.1)',
  danger: 'rgba(239, 68, 68, 1)',
  dangerLight: 'rgba(239, 68, 68, 0.6)',
  dangerFill: 'rgba(239, 68, 68, 0.1)',
  info: 'rgba(59, 130, 246, 1)',
  infoLight: 'rgba(59, 130, 246, 0.6)',
  infoFill: 'rgba(59, 130, 246, 0.1)',
  gradient1: 'rgba(99, 102, 241, 1)',
  gradient2: 'rgba(168, 85, 247, 1)',
  gradient3: 'rgba(236, 72, 153, 1)'
};

// Chart.js professional defaults
const CHART_DEFAULTS = {
  responsive: true,
  maintainAspectRatio: false,
  animation: {
    duration: 750,
    easing: 'easeOutQuart',
    delay: (context) => {
      let delay = 0;
      if (context.type === 'data' && context.mode === 'default') {
        delay = context.dataIndex * 20 + context.datasetIndex * 100;
      }
      return delay;
    }
  },
  plugins: {
    legend: {
      display: true,
      position: 'top',
      align: 'start',
      labels: {
        usePointStyle: true,
        padding: 15,
        font: {
          family: 'Inter, system-ui, sans-serif',
          size: 12,
          weight: '500'
        },
        color: 'rgba(237, 242, 251, 0.85)',
        boxWidth: 10,
        boxHeight: 10
      }
    },
    tooltip: {
      enabled: true,
      backgroundColor: 'rgba(14, 22, 40, 0.95)',
      titleColor: 'rgba(237, 242, 251, 0.9)',
      bodyColor: 'rgba(237, 242, 251, 0.7)',
      borderColor: 'rgba(51, 221, 200, 0.3)',
      borderWidth: 1,
      padding: 12,
      cornerRadius: 8,
      displayColors: true,
      titleFont: {
        family: 'Inter, system-ui, sans-serif',
        size: 13,
        weight: '600'
      },
      bodyFont: {
        family: 'Inter, system-ui, sans-serif',
        size: 12
      },
      callbacks: {
        label: function(context) {
          let label = context.dataset.label || '';
          if (label) {
            label += ': ';
          }
          if (context.parsed.y !== null) {
            label += typeof context.parsed.y === 'number' 
              ? context.parsed.y.toFixed(3) 
              : context.parsed.y;
          }
          return label;
        }
      }
    }
  },
  scales: {
    x: {
      grid: {
        color: 'rgba(255, 255, 255, 0.05)',
        drawBorder: false,
        lineWidth: 1
      },
      ticks: {
        color: 'rgba(237, 242, 251, 0.6)',
        font: {
          family: 'Inter, system-ui, sans-serif',
          size: 11
        },
        maxRotation: 0,
        autoSkip: true,
        maxTicksLimit: 10
      }
    },
    y: {
      grid: {
        color: 'rgba(255, 255, 255, 0.05)',
        drawBorder: false,
        lineWidth: 1
      },
      ticks: {
        color: 'rgba(237, 242, 251, 0.6)',
        font: {
          family: 'Inter, system-ui, sans-serif',
          size: 11
        },
        precision: 2
      },
      beginAtZero: true
    }
  },
  interaction: {
    intersect: false,
    mode: 'index'
  }
};

// Chart registry for cleanup and management
const chartRegistry = new Map();

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Deep merge objects
 */
function deepMerge(target, source) {
  const output = { ...target };
  if (isObject(target) && isObject(source)) {
    Object.keys(source).forEach(key => {
      if (isObject(source[key])) {
        if (!(key in target)) {
          Object.assign(output, { [key]: source[key] });
        } else {
          output[key] = deepMerge(target[key], source[key]);
        }
      } else {
        Object.assign(output, { [key]: source[key] });
      }
    });
  }
  return output;
}

function isObject(item) {
  return item && typeof item === 'object' && !Array.isArray(item);
}

/**
 * Wait for Chart.js to load
 */
async function waitForChartJS(maxWaitMs = 5000) {
  const startTime = Date.now();
  
  while (typeof Chart === 'undefined') {
    if (Date.now() - startTime > maxWaitMs) {
      throw new Error('Chart.js failed to load');
    }
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  
  return true;
}

/**
 * Create gradient fill
 */
function createGradient(ctx, color1, color2, height = 300) {
  const gradient = ctx.createLinearGradient(0, 0, 0, height);
  gradient.addColorStop(0, color1);
  gradient.addColorStop(1, color2);
  return gradient;
}

/**
 * Generate time labels
 */
function generateTimeLabels(count, intervalSeconds = 1) {
  const labels = [];
  for (let i = 0; i < count; i++) {
    labels.push(`${i * intervalSeconds}s`);
  }
  return labels;
}

// ============================================================================
// CHART INITIALIZATION FUNCTIONS
// ============================================================================

/**
 * Initialize a line chart with professional defaults
 */
async function initLineChart(canvasId, config = {}) {
  try {
    // Wait for Chart.js to load
    await waitForChartJS();
    
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
      console.warn(`[Graph Utils] Canvas not found: ${canvasId}`);
      return null;
    }

    // Destroy existing chart if present
    if (chartRegistry.has(canvasId)) {
      const existingChart = chartRegistry.get(canvasId);
      existingChart.destroy();
      chartRegistry.delete(canvasId);
    }

    const ctx = canvas.getContext('2d');
    
    const defaultConfig = {
      type: 'line',
      data: {
        labels: [],
        datasets: []
      },
      options: { ...CHART_DEFAULTS }
    };

    const mergedConfig = deepMerge(defaultConfig, config);
    
    // Add gradient backgrounds if not specified
    if (mergedConfig.data.datasets) {
      mergedConfig.data.datasets.forEach((dataset, index) => {
        if (!dataset.borderColor) {
          const colors = [
            CHART_COLORS.primary,
            CHART_COLORS.secondary,
            CHART_COLORS.success,
            CHART_COLORS.warning
          ];
          dataset.borderColor = colors[index % colors.length];
        }
        
        if (!dataset.backgroundColor && dataset.fill) {
          const fillColors = [
            CHART_COLORS.primaryFill,
            CHART_COLORS.secondaryFill,
            CHART_COLORS.successFill,
            CHART_COLORS.warningFill
          ];
          dataset.backgroundColor = fillColors[index % fillColors.length];
        }
        
        // Professional line styling
        dataset.tension = dataset.tension !== undefined ? dataset.tension : 0.4;
        dataset.borderWidth = dataset.borderWidth || 2;
        dataset.pointRadius = dataset.pointRadius !== undefined ? dataset.pointRadius : 0;
        dataset.pointHoverRadius = dataset.pointHoverRadius || 5;
        dataset.pointHoverBackgroundColor = dataset.borderColor;
      });
    }

    const chart = new Chart(ctx, mergedConfig);
    
    // Register chart
    chartRegistry.set(canvasId, chart);
    
    // Add animation class to container
    const container = canvas.closest('.chartBox, .chart-container');
    if (container) {
      container.classList.add('animate-fadeIn');
    }

    console.log(`[Graph Utils] ✓ Line chart initialized: ${canvasId}`);
    return chart;
  } catch (error) {
    console.error(`[Graph Utils] ✗ Error initializing line chart ${canvasId}:`, error);
    showChartError(canvasId, 'Failed to initialize chart');
    return null;
  }
}

/**
 * Initialize a bar chart
 */
async function initBarChart(canvasId, config = {}) {
  try {
    await waitForChartJS();
    
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
      console.warn(`[Graph Utils] Canvas not found: ${canvasId}`);
      return null;
    }

    if (chartRegistry.has(canvasId)) {
      chartRegistry.get(canvasId).destroy();
      chartRegistry.delete(canvasId);
    }

    const ctx = canvas.getContext('2d');
    
    const defaultConfig = {
      type: 'bar',
      data: {
        labels: [],
        datasets: []
      },
      options: {
        ...CHART_DEFAULTS,
        plugins: {
          ...CHART_DEFAULTS.plugins,
          legend: {
            ...CHART_DEFAULTS.plugins.legend,
            display: config.showLegend !== false
          }
        }
      }
    };

    const mergedConfig = deepMerge(defaultConfig, config);
    
    // Add professional bar styling
    if (mergedConfig.data.datasets) {
      mergedConfig.data.datasets.forEach((dataset, index) => {
        const colors = [
          CHART_COLORS.primary,
          CHART_COLORS.secondary,
          CHART_COLORS.success,
          CHART_COLORS.warning
        ];
        dataset.backgroundColor = dataset.backgroundColor || colors[index % colors.length];
        dataset.borderWidth = dataset.borderWidth || 0;
        dataset.borderRadius = dataset.borderRadius !== undefined ? dataset.borderRadius : 4;
        dataset.borderSkipped = false;
      });
    }

    const chart = new Chart(ctx, mergedConfig);
    chartRegistry.set(canvasId, chart);
    
    const container = canvas.closest('.chartBox, .chart-container');
    if (container) {
      container.classList.add('animate-fadeIn');
    }

    console.log(`[Graph Utils] ✓ Bar chart initialized: ${canvasId}`);
    return chart;
  } catch (error) {
    console.error(`[Graph Utils] ✗ Error initializing bar chart ${canvasId}:`, error);
    showChartError(canvasId, 'Failed to initialize chart');
    return null;
  }
}

/**
 * Initialize a doughnut chart
 */
async function initDoughnutChart(canvasId, config = {}) {
  try {
    await waitForChartJS();
    
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
      console.warn(`[Graph Utils] Canvas not found: ${canvasId}`);
      return null;
    }

    if (chartRegistry.has(canvasId)) {
      chartRegistry.get(canvasId).destroy();
      chartRegistry.delete(canvasId);
    }

    const ctx = canvas.getContext('2d');
    
    const defaultConfig = {
      type: 'doughnut',
      data: {
        labels: [],
        datasets: []
      },
      options: {
        ...CHART_DEFAULTS,
        cutout: '70%'
      }
    };

    const mergedConfig = deepMerge(defaultConfig, config);
    
    // Add professional doughnut styling
    if (mergedConfig.data.datasets) {
      mergedConfig.data.datasets.forEach((dataset) => {
        if (!dataset.backgroundColor) {
          dataset.backgroundColor = [
            CHART_COLORS.primary,
            CHART_COLORS.secondary,
            CHART_COLORS.success,
            CHART_COLORS.warning,
            CHART_COLORS.danger,
            CHART_COLORS.info
          ];
        }
        dataset.borderWidth = dataset.borderWidth || 0;
        dataset.hoverOffset = dataset.hoverOffset || 10;
      });
    }

    const chart = new Chart(ctx, mergedConfig);
    chartRegistry.set(canvasId, chart);
    
    const container = canvas.closest('.chartBox, .chart-container');
    if (container) {
      container.classList.add('animate-fadeIn');
    }

    console.log(`[Graph Utils] ✓ Doughnut chart initialized: ${canvasId}`);
    return chart;
  } catch (error) {
    console.error(`[Graph Utils] ✗ Error initializing doughnut chart ${canvasId}:`, error);
    showChartError(canvasId, 'Failed to initialize chart');
    return null;
  }
}

/**
 * Initialize a radar chart
 */
async function initRadarChart(canvasId, config = {}) {
  try {
    await waitForChartJS();
    
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;

    if (chartRegistry.has(canvasId)) {
      chartRegistry.get(canvasId).destroy();
      chartRegistry.delete(canvasId);
    }

    const ctx = canvas.getContext('2d');
    
    const defaultConfig = {
      type: 'radar',
      data: {
        labels: [],
        datasets: []
      },
      options: {
        ...CHART_DEFAULTS,
        scales: {
          r: {
            grid: {
              color: 'rgba(255, 255, 255, 0.05)'
            },
            ticks: {
              color: 'rgba(237, 242, 251, 0.6)',
              backdropColor: 'transparent'
            },
            pointLabels: {
              color: 'rgba(237, 242, 251, 0.8)',
              font: {
                family: 'Inter, system-ui, sans-serif',
                size: 11
              }
            }
          }
        }
      }
    };

    const mergedConfig = deepMerge(defaultConfig, config);
    const chart = new Chart(ctx, mergedConfig);
    chartRegistry.set(canvasId, chart);

    console.log(`[Graph Utils] ✓ Radar chart initialized: ${canvasId}`);
    return chart;
  } catch (error) {
    console.error(`[Graph Utils] ✗ Error initializing radar chart ${canvasId}:`, error);
    return null;
  }
}

// ============================================================================
// CHART UPDATE FUNCTIONS
// ============================================================================

/**
 * Update chart data with animation
 */
function updateChartData(chartId, newData, animate = true) {
  const chart = chartRegistry.get(chartId);
  if (!chart) {
    console.warn(`[Graph Utils] Chart not found: ${chartId}`);
    return false;
  }

  try {
    if (newData.labels) {
      chart.data.labels = newData.labels;
    }

    if (newData.datasets) {
      newData.datasets.forEach((newDataset, index) => {
        if (chart.data.datasets[index]) {
          chart.data.datasets[index].data = newDataset.data || newDataset;
        }
      });
    }

    chart.update(animate ? 'default' : 'none');
    return true;
  } catch (error) {
    console.error(`[Graph Utils] Error updating chart ${chartId}:`, error);
    return false;
  }
}

/**
 * Append data to chart (for real-time updates)
 */
function appendChartData(chartId, label, values, maxDataPoints = 60) {
  const chart = chartRegistry.get(chartId);
  if (!chart) return false;

  try {
    // Add new label
    chart.data.labels.push(label);
    
    // Add new data points
    if (Array.isArray(values)) {
      values.forEach((value, index) => {
        if (chart.data.datasets[index]) {
          chart.data.datasets[index].data.push(value);
        }
      });
    } else {
      if (chart.data.datasets[0]) {
        chart.data.datasets[0].data.push(values);
      }
    }

    // Remove old data points
    if (chart.data.labels.length > maxDataPoints) {
      chart.data.labels.shift();
      chart.data.datasets.forEach(dataset => {
        dataset.data.shift();
      });
    }

    chart.update('active');
    return true;
  } catch (error) {
    console.error(`[Graph Utils] Error appending chart data ${chartId}:`, error);
    return false;
  }
}

/**
 * Clear chart data
 */
function clearChartData(chartId) {
  const chart = chartRegistry.get(chartId);
  if (!chart) return false;

  try {
    chart.data.labels = [];
    chart.data.datasets.forEach(dataset => {
      dataset.data = [];
    });
    chart.update('none');
    return true;
  } catch (error) {
    console.error(`[Graph Utils] Error clearing chart ${chartId}:`, error);
    return false;
  }
}

// ============================================================================
// CHART MANAGEMENT FUNCTIONS
// ============================================================================

/**
 * Destroy a chart
 */
function destroyChart(chartId) {
  const chart = chartRegistry.get(chartId);
  if (chart) {
    chart.destroy();
    chartRegistry.delete(chartId);
    console.log(`[Graph Utils] Chart destroyed: ${chartId}`);
    return true;
  }
  return false;
}

/**
 * Destroy all charts
 */
function destroyAllCharts() {
  chartRegistry.forEach((chart, id) => {
    chart.destroy();
    console.log(`[Graph Utils] Chart destroyed: ${id}`);
  });
  chartRegistry.clear();
}

/**
 * Get chart instance
 */
function getChart(chartId) {
  return chartRegistry.get(chartId) || null;
}

/**
 * Show chart error message
 */
function showChartError(canvasId, message = 'Chart initialization failed') {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;

  const container = canvas.closest('.chartBox, .chart-container') || canvas.parentElement;
  if (!container) return;

  const errorDiv = document.createElement('div');
  errorDiv.className = 'chart-error animate-fadeIn';
  errorDiv.innerHTML = `
    <div style="
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      text-align: center;
      color: rgba(239, 68, 68, 0.8);
      padding: 20px;
      background: rgba(14, 22, 40, 0.8);
      border-radius: 8px;
      border: 1px solid rgba(239, 68, 68, 0.3);
    ">
      <div style="font-size: 32px; margin-bottom: 10px;">⚠️</div>
      <div style="font-size: 14px; font-weight: 600;">${message}</div>
    </div>
  `;

  container.style.position = 'relative';
  container.appendChild(errorDiv);
}

/**
 * Show chart loading state
 */
function showChartLoading(canvasId) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;

  const container = canvas.closest('.chartBox, .chart-container') || canvas.parentElement;
  if (!container) return;

  const loadingDiv = document.createElement('div');
  loadingDiv.className = 'chart-loading animate-fadeIn';
  loadingDiv.id = `loading-${canvasId}`;
  loadingDiv.innerHTML = `
    <div style="
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      text-align: center;
      color: rgba(51, 221, 200, 0.8);
    ">
      <div class="loading-spinner" style="width: 40px; height: 40px; margin: 0 auto 15px;"></div>
      <div style="font-size: 13px;">Loading chart...</div>
    </div>
  `;

  container.style.position = 'relative';
  container.appendChild(loadingDiv);
}

/**
 * Hide chart loading state
 */
function hideChartLoading(canvasId) {
  const loadingDiv = document.getElementById(`loading-${canvasId}`);
  if (loadingDiv) {
    loadingDiv.remove();
  }
}

// ============================================================================
// EXPORT
// ============================================================================

// Check if Chart.js is loaded on script load
if (typeof Chart !== 'undefined') {
  console.log('%c✓ Chart.js loaded successfully', 'color: #46e68b; font-weight: bold');
} else {
  console.warn('%c⚠ Chart.js not loaded yet', 'color: #f4b400; font-weight: bold');
}

// Export functions
window.GraphUtils = {
  // Initialization
  initLineChart,
  initBarChart,
  initDoughnutChart,
  initRadarChart,
  
  // Updates
  updateChartData,
  appendChartData,
  clearChartData,
  
  // Management
  destroyChart,
  destroyAllCharts,
  getChart,
  
  // UI
  showChartLoading,
  hideChartLoading,
  showChartError,
  
  // Utilities
  createGradient,
  generateTimeLabels,
  
  // Constants
  CHART_COLORS,
  CHART_DEFAULTS
};

console.log('%c🚀 Graph Utils Module Loaded', 'color: #33ddc8; font-size: 14px; font-weight: bold');
