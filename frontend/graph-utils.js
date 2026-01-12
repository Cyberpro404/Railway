/**
 * GANDIVA LEVEL 10 UI - Enhanced Graph Utilities
 * Professional graph initialization, error handling, and animations
 */

// Chart.js configuration with professional defaults
const CHART_DEFAULTS = {
  responsive: true,
  maintainAspectRatio: false,
  animation: {
    duration: 750,
    easing: 'easeOutQuart'
  },
  plugins: {
    legend: {
      display: true,
      position: 'top',
      labels: {
        usePointStyle: true,
        padding: 15,
        font: {
          family: 'Inter, system-ui, sans-serif',
          size: 12,
          weight: '500'
        },
        color: 'rgba(237, 242, 251, 0.85)'
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
        drawBorder: false
      },
      ticks: {
        color: 'rgba(237, 242, 251, 0.6)',
        font: {
          family: 'Inter, system-ui, sans-serif',
          size: 11
        }
      }
    },
    y: {
      grid: {
        color: 'rgba(255, 255, 255, 0.05)',
        drawBorder: false
      },
      ticks: {
        color: 'rgba(237, 242, 251, 0.6)',
        font: {
          family: 'Inter, system-ui, sans-serif',
          size: 11
        }
      },
      beginAtZero: true
    }
  },
  interaction: {
    intersect: false,
    mode: 'index'
  }
};

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
  infoFill: 'rgba(59, 130, 246, 0.1)'
};

// Chart registry for cleanup
const chartRegistry = new Map();

/**
 * Initialize a line chart with professional defaults
 */
function initLineChart(canvasId, config = {}) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) {
    console.warn(`[Graph Utils] Canvas not found: ${canvasId}`);
    return null;
  }

  // Check if Chart.js is loaded
  if (typeof Chart === 'undefined') {
    console.error('[Graph Utils] Chart.js not loaded');
    return null;
  }

  // Destroy existing chart if present
  if (chartRegistry.has(canvasId)) {
    const existingChart = chartRegistry.get(canvasId);
    existingChart.destroy();
  }

  try {
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
    const chart = new Chart(ctx, mergedConfig);
    
    // Register chart
    chartRegistry.set(canvasId, chart);
    
    // Add animation class to container
    const container = canvas.closest('.chartBox, .chart-container');
    if (container) {
      container.classList.add('animate-fadeIn', 'gpu-accelerated');
    }

    console.log(`[Graph Utils] Chart initialized: ${canvasId}`);
    return chart;
  } catch (error) {
    console.error(`[Graph Utils] Error initializing chart ${canvasId}:`, error);
    return null;
  }
}

/**
 * Initialize a bar chart
 */
function initBarChart(canvasId, config = {}) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) {
    console.warn(`[Graph Utils] Canvas not found: ${canvasId}`);
    return null;
  }

  if (typeof Chart === 'undefined') {
    console.error('[Graph Utils] Chart.js not loaded');
    return null;
  }

  if (chartRegistry.has(canvasId)) {
    chartRegistry.get(canvasId).destroy();
  }

  try {
    const ctx = canvas.getContext('2d');
    
    const defaultConfig = {
      type: 'bar',
      data: {
        labels: [],
        datasets: []
      },
      options: {
        ...CHART_DEFAULTS,
        scales: {
          ...CHART_DEFAULTS.scales,
          y: {
            ...CHART_DEFAULTS.scales.y,
            beginAtZero: true
          }
        }
      }
    };

    const mergedConfig = deepMerge(defaultConfig, config);
    const chart = new Chart(ctx, mergedConfig);
    
    chartRegistry.set(canvasId, chart);
    
    const container = canvas.closest('.chartBox, .chart-container');
    if (container) {
      container.classList.add('animate-fadeIn', 'gpu-accelerated');
    }

    console.log(`[Graph Utils] Bar chart initialized: ${canvasId}`);
    return chart;
  } catch (error) {
    console.error(`[Graph Utils] Error initializing bar chart ${canvasId}:`, error);
    return null;
  }
}

/**
 * Initialize a scatter chart
 */
function initScatterChart(canvasId, config = {}) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) {
    console.warn(`[Graph Utils] Canvas not found: ${canvasId}`);
    return null;
  }

  if (typeof Chart === 'undefined') {
    console.error('[Graph Utils] Chart.js not loaded');
    return null;
  }

  if (chartRegistry.has(canvasId)) {
    chartRegistry.get(canvasId).destroy();
  }

  try {
    const ctx = canvas.getContext('2d');
    
    const defaultConfig = {
      type: 'scatter',
      data: {
        datasets: []
      },
      options: {
        ...CHART_DEFAULTS,
        scales: {
          ...CHART_DEFAULTS.scales,
          x: {
            ...CHART_DEFAULTS.scales.x,
            type: 'linear',
            position: 'bottom'
          }
        }
      }
    };

    const mergedConfig = deepMerge(defaultConfig, config);
    const chart = new Chart(ctx, mergedConfig);
    
    chartRegistry.set(canvasId, chart);
    
    const container = canvas.closest('.chartBox, .chart-container');
    if (container) {
      container.classList.add('animate-fadeIn', 'gpu-accelerated');
    }

    console.log(`[Graph Utils] Scatter chart initialized: ${canvasId}`);
    return chart;
  } catch (error) {
    console.error(`[Graph Utils] Error initializing scatter chart ${canvasId}:`, error);
    return null;
  }
}

/**
 * Update chart data with smooth animation
 */
function updateChartData(chart, newData, animate = true) {
  if (!chart) {
    console.warn('[Graph Utils] Chart is null, cannot update');
    return;
  }

  try {
    if (newData.labels) {
      chart.data.labels = newData.labels;
    }

    if (newData.datasets) {
      chart.data.datasets = newData.datasets;
    }

    chart.update(animate ? 'active' : 'none');
  } catch (error) {
    console.error('[Graph Utils] Error updating chart data:', error);
  }
}

/**
 * Add dataset to chart
 */
function addDataset(chart, dataset, animate = true) {
  if (!chart) return;
  
  try {
    chart.data.datasets.push(dataset);
    chart.update(animate ? 'active' : 'none');
  } catch (error) {
    console.error('[Graph Utils] Error adding dataset:', error);
  }
}

/**
 * Remove dataset from chart
 */
function removeDataset(chart, index, animate = true) {
  if (!chart || !chart.data.datasets[index]) return;
  
  try {
    chart.data.datasets.splice(index, 1);
    chart.update(animate ? 'active' : 'none');
  } catch (error) {
    console.error('[Graph Utils] Error removing dataset:', error);
  }
}

/**
 * Destroy chart and clean up
 */
function destroyChart(canvasId) {
  if (chartRegistry.has(canvasId)) {
    const chart = chartRegistry.get(canvasId);
    chart.destroy();
    chartRegistry.delete(canvasId);
    console.log(`[Graph Utils] Chart destroyed: ${canvasId}`);
  }
}

/**
 * Destroy all charts
 */
function destroyAllCharts() {
  chartRegistry.forEach((chart, canvasId) => {
    chart.destroy();
    console.log(`[Graph Utils] Chart destroyed: ${canvasId}`);
  });
  chartRegistry.clear();
}

/**
 * Get chart instance
 */
function getChart(canvasId) {
  return chartRegistry.get(canvasId) || null;
}

/**
 * Check if chart exists
 */
function hasChart(canvasId) {
  return chartRegistry.has(canvasId);
}

/**
 * Create dataset configuration
 */
function createDataset(label, data, color = CHART_COLORS.primary, options = {}) {
  const defaultOptions = {
    label: label,
    data: data,
    borderColor: color,
    backgroundColor: color.replace('1)', '0.1)'),
    borderWidth: 2,
    pointRadius: 0,
    pointHoverRadius: 4,
    tension: 0.3,
    fill: false
  };

  return { ...defaultOptions, ...options };
}

/**
 * Deep merge utility
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
 * Export for use in other modules
 */
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    initLineChart,
    initBarChart,
    initScatterChart,
    updateChartData,
    addDataset,
    removeDataset,
    destroyChart,
    destroyAllCharts,
    getChart,
    hasChart,
    createDataset,
    CHART_COLORS,
    CHART_DEFAULTS
  };
}

