/**
 * ============================================================================
 * GANDIVA LEVEL 10 - COMPREHENSIVE API TESTING UTILITIES
 * Enterprise-Grade API Testing & Error Handling System
 * ============================================================================
 */

// ============================================================================
// CONFIGURATION
// ============================================================================

const API_TEST_CONFIG = {
  baseURL: window.location.origin,
  timeout: 10000, // 10 seconds
  retryAttempts: 3,
  retryDelay: 1000, // 1 second
  enableLogging: true,
  enablePerformanceMonitoring: true
};

// ============================================================================
// API ENDPOINT REGISTRY
// ============================================================================

const API_ENDPOINTS = {
  // Connection endpoints
  connection: {
    listPorts: '/connection/ports',
    connect: '/connection/connect',
    disconnect: '/connection/disconnect',
    status: '/connection/status',
    autoDetect: '/connection/auto-detect'
  },
  
  // Sensor endpoints
  sensor: {
    latest: '/sensor/latest',
    history: '/sensor/history',
    realtime: '/sensor/realtime',
    stats: '/sensor/stats'
  },
  
  // ML/Prediction endpoints
  prediction: {
    predict: '/predict',
    modelStatus: '/predict/model-status',
    modelInfo: '/predict/model-info'
  },
  
  // Training endpoints
  training: {
    datasets: '/training/datasets',
    startTraining: '/training/train',
    trainingStatus: '/training/status',
    uploadDataset: '/training/upload'
  },
  
  // Monitoring endpoints
  monitoring: {
    alerts: '/monitoring/alerts',
    logs: '/monitoring/logs',
    health: '/monitoring/health',
    metrics: '/monitoring/metrics'
  },
  
  // Dataset endpoints
  dataset: {
    list: '/dataset/list',
    info: '/dataset/info',
    delete: '/dataset/delete',
    download: '/dataset/download'
  },
  
  // Industrial diagnostics endpoints
  diagnostics: {
    status: '/industrial/status',
    metrics: '/industrial/metrics',
    thresholds: '/industrial/thresholds',
    updateThresholds: '/industrial/thresholds/update'
  }
};

// ============================================================================
// ERROR HANDLING UTILITIES
// ============================================================================

class APIError extends Error {
  constructor(message, statusCode, endpoint, originalError) {
    super(message);
    this.name = 'APIError';
    this.statusCode = statusCode;
    this.endpoint = endpoint;
    this.originalError = originalError;
    this.timestamp = new Date().toISOString();
  }
}

class NetworkError extends Error {
  constructor(message, endpoint) {
    super(message);
    this.name = 'NetworkError';
    this.endpoint = endpoint;
    this.timestamp = new Date().toISOString();
  }
}

class TimeoutError extends Error {
  constructor(message, endpoint) {
    super(message);
    this.name = 'TimeoutError';
    this.endpoint = endpoint;
    this.timestamp = new Date().toISOString();
  }
}

// ============================================================================
// PERFORMANCE MONITORING
// ============================================================================

class PerformanceMonitor {
  constructor() {
    this.metrics = new Map();
  }

  start(endpoint) {
    this.metrics.set(endpoint, {
      startTime: performance.now(),
      endpoint
    });
  }

  end(endpoint, success = true) {
    const metric = this.metrics.get(endpoint);
    if (!metric) return null;

    const endTime = performance.now();
    const duration = endTime - metric.startTime;

    const result = {
      endpoint,
      duration: Math.round(duration),
      success,
      timestamp: new Date().toISOString()
    };

    this.metrics.delete(endpoint);
    
    if (API_TEST_CONFIG.enableLogging) {
      console.log(`[API Performance] ${endpoint}: ${duration.toFixed(2)}ms - ${success ? '✓' : '✗'}`);
    }

    return result;
  }

  getStats() {
    return Array.from(this.metrics.values());
  }
}

const perfMonitor = new PerformanceMonitor();

// ============================================================================
// RETRY LOGIC WITH EXPONENTIAL BACKOFF
// ============================================================================

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function retryWithBackoff(fn, options = {}) {
  const {
    attempts = API_TEST_CONFIG.retryAttempts,
    delay = API_TEST_CONFIG.retryDelay,
    backoffMultiplier = 2,
    onRetry = null
  } = options;

  let lastError;

  for (let attempt = 1; attempt <= attempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      
      if (attempt === attempts) {
        throw lastError;
      }

      const waitTime = delay * Math.pow(backoffMultiplier, attempt - 1);
      
      if (onRetry) {
        onRetry(attempt, attempts, waitTime, error);
      }

      if (API_TEST_CONFIG.enableLogging) {
        console.warn(`[API Retry] Attempt ${attempt}/${attempts} failed. Retrying in ${waitTime}ms...`, error.message);
      }

      await sleep(waitTime);
    }
  }

  throw lastError;
}

// ============================================================================
// ENHANCED FETCH WITH TIMEOUT
// ============================================================================

async function fetchWithTimeout(url, options = {}, timeout = API_TEST_CONFIG.timeout) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      throw new TimeoutError(`Request timeout after ${timeout}ms`, url);
    }
    throw error;
  }
}

// ============================================================================
// MAIN API CLIENT
// ============================================================================

class APIClient {
  constructor(config = API_TEST_CONFIG) {
    this.config = config;
    this.requestQueue = [];
    this.activeRequests = new Set();
  }

  /**
   * Build full URL from endpoint path
   */
  buildURL(path) {
    return `${this.config.baseURL}${path}`;
  }

  /**
   * Enhanced GET request with retry logic
   */
  async get(endpoint, options = {}) {
    const url = this.buildURL(endpoint);
    
    if (this.config.enablePerformanceMonitoring) {
      perfMonitor.start(endpoint);
    }

    try {
      const response = await retryWithBackoff(async () => {
        const res = await fetchWithTimeout(url, {
          method: 'GET',
          headers: {
            'Accept': 'application/json',
            ...options.headers
          }
        }, options.timeout || this.config.timeout);

        if (!res.ok) {
          throw new APIError(
            `HTTP ${res.status}: ${res.statusText}`,
            res.status,
            endpoint
          );
        }

        // Handle 204 No Content
        if (res.status === 204) {
          return null;
        }

        const contentType = res.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          return await res.json();
        }

        return await res.text();
      }, {
        attempts: options.retryAttempts || this.config.retryAttempts,
        delay: options.retryDelay || this.config.retryDelay,
        onRetry: options.onRetry
      });

      if (this.config.enablePerformanceMonitoring) {
        perfMonitor.end(endpoint, true);
      }

      return { success: true, data: response, error: null };

    } catch (error) {
      if (this.config.enablePerformanceMonitoring) {
        perfMonitor.end(endpoint, false);
      }

      if (this.config.enableLogging) {
        console.error(`[API Error] GET ${endpoint}:`, error);
      }

      return { success: false, data: null, error };
    }
  }

  /**
   * Enhanced POST request with retry logic
   */
  async post(endpoint, body = null, options = {}) {
    const url = this.buildURL(endpoint);
    
    if (this.config.enablePerformanceMonitoring) {
      perfMonitor.start(endpoint);
    }

    try {
      const response = await retryWithBackoff(async () => {
        const res = await fetchWithTimeout(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            ...options.headers
          },
          body: body ? JSON.stringify(body) : null
        }, options.timeout || this.config.timeout);

        if (!res.ok) {
          throw new APIError(
            `HTTP ${res.status}: ${res.statusText}`,
            res.status,
            endpoint
          );
        }

        const contentType = res.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          return await res.json();
        }

        return await res.text();
      }, {
        attempts: options.retryAttempts || this.config.retryAttempts,
        delay: options.retryDelay || this.config.retryDelay,
        onRetry: options.onRetry
      });

      if (this.config.enablePerformanceMonitoring) {
        perfMonitor.end(endpoint, true);
      }

      return { success: true, data: response, error: null };

    } catch (error) {
      if (this.config.enablePerformanceMonitoring) {
        perfMonitor.end(endpoint, false);
      }

      if (this.config.enableLogging) {
        console.error(`[API Error] POST ${endpoint}:`, error);
      }

      return { success: false, data: null, error };
    }
  }

  /**
   * PUT request
   */
  async put(endpoint, body = null, options = {}) {
    const url = this.buildURL(endpoint);
    
    try {
      const res = await fetchWithTimeout(url, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          ...options.headers
        },
        body: body ? JSON.stringify(body) : null
      }, options.timeout || this.config.timeout);

      if (!res.ok) {
        throw new APIError(`HTTP ${res.status}: ${res.statusText}`, res.status, endpoint);
      }

      return { success: true, data: await res.json(), error: null };
    } catch (error) {
      return { success: false, data: null, error };
    }
  }

  /**
   * DELETE request
   */
  async delete(endpoint, options = {}) {
    const url = this.buildURL(endpoint);
    
    try {
      const res = await fetchWithTimeout(url, {
        method: 'DELETE',
        headers: {
          'Accept': 'application/json',
          ...options.headers
        }
      }, options.timeout || this.config.timeout);

      if (!res.ok) {
        throw new APIError(`HTTP ${res.status}: ${res.statusText}`, res.status, endpoint);
      }

      return { success: true, data: await res.json(), error: null };
    } catch (error) {
      return { success: false, data: null, error };
    }
  }
}

// ============================================================================
// API TEST SUITE
// ============================================================================

class APITestSuite {
  constructor(client) {
    this.client = client;
    this.results = [];
  }

  /**
   * Test a single endpoint
   */
  async testEndpoint(name, endpoint, method = 'GET', body = null) {
    console.log(`Testing: ${name} (${method} ${endpoint})`);
    
    const startTime = Date.now();
    let result;

    if (method === 'GET') {
      result = await this.client.get(endpoint);
    } else if (method === 'POST') {
      result = await this.client.post(endpoint, body);
    }

    const duration = Date.now() - startTime;

    const testResult = {
      name,
      endpoint,
      method,
      success: result.success,
      duration,
      status: result.success ? 'PASS' : 'FAIL',
      error: result.error ? result.error.message : null,
      timestamp: new Date().toISOString()
    };

    this.results.push(testResult);

    const statusIcon = result.success ? '✓' : '✗';
    const statusColor = result.success ? 'color: green' : 'color: red';
    console.log(`%c${statusIcon} ${name}: ${testResult.status} (${duration}ms)`, statusColor);

    return testResult;
  }

  /**
   * Test all connection endpoints
   */
  async testConnectionEndpoints() {
    console.log('\n=== Testing Connection Endpoints ===');
    await this.testEndpoint('List Ports', API_ENDPOINTS.connection.listPorts);
    await this.testEndpoint('Connection Status', API_ENDPOINTS.connection.status);
    await this.testEndpoint('Auto Detect', API_ENDPOINTS.connection.autoDetect, 'POST');
  }

  /**
   * Test all sensor endpoints
   */
  async testSensorEndpoints() {
    console.log('\n=== Testing Sensor Endpoints ===');
    await this.testEndpoint('Latest Sensor Data', API_ENDPOINTS.sensor.latest);
    await this.testEndpoint('Sensor History', API_ENDPOINTS.sensor.history);
    await this.testEndpoint('Sensor Stats', API_ENDPOINTS.sensor.stats);
  }

  /**
   * Test all prediction endpoints
   */
  async testPredictionEndpoints() {
    console.log('\n=== Testing Prediction Endpoints ===');
    await this.testEndpoint('Model Status', API_ENDPOINTS.prediction.modelStatus);
    await this.testEndpoint('Model Info', API_ENDPOINTS.prediction.modelInfo);
  }

  /**
   * Test all monitoring endpoints
   */
  async testMonitoringEndpoints() {
    console.log('\n=== Testing Monitoring Endpoints ===');
    await this.testEndpoint('Alerts', API_ENDPOINTS.monitoring.alerts);
    await this.testEndpoint('Logs', API_ENDPOINTS.monitoring.logs);
    await this.testEndpoint('Health', API_ENDPOINTS.monitoring.health);
  }

  /**
   * Test all dataset endpoints
   */
  async testDatasetEndpoints() {
    console.log('\n=== Testing Dataset Endpoints ===');
    await this.testEndpoint('List Datasets', API_ENDPOINTS.dataset.list);
  }

  /**
   * Run all tests
   */
  async runAllTests() {
    console.log('╔════════════════════════════════════════════════════════╗');
    console.log('║  GANDIVA API TEST SUITE - COMPREHENSIVE TESTING       ║');
    console.log('╚════════════════════════════════════════════════════════╝\n');

    this.results = [];
    const overallStart = Date.now();

    await this.testConnectionEndpoints();
    await this.testSensorEndpoints();
    await this.testPredictionEndpoints();
    await this.testMonitoringEndpoints();
    await this.testDatasetEndpoints();

    const overallDuration = Date.now() - overallStart;
    const passCount = this.results.filter(r => r.success).length;
    const failCount = this.results.length - passCount;
    const passRate = ((passCount / this.results.length) * 100).toFixed(1);

    console.log('\n╔════════════════════════════════════════════════════════╗');
    console.log('║  TEST SUMMARY                                         ║');
    console.log('╚════════════════════════════════════════════════════════╝');
    console.log(`Total Tests: ${this.results.length}`);
    console.log(`%cPassed: ${passCount}`, 'color: green; font-weight: bold');
    console.log(`%cFailed: ${failCount}`, 'color: red; font-weight: bold');
    console.log(`Pass Rate: ${passRate}%`);
    console.log(`Total Duration: ${overallDuration}ms`);

    return {
      total: this.results.length,
      passed: passCount,
      failed: failCount,
      passRate,
      duration: overallDuration,
      results: this.results
    };
  }

  /**
   * Generate HTML report
   */
  generateHTMLReport() {
    const passCount = this.results.filter(r => r.success).length;
    const failCount = this.results.length - passCount;
    
    let html = `
      <div style="font-family: monospace; background: #1e1e1e; color: #d4d4d4; padding: 20px; border-radius: 8px;">
        <h2 style="color: #33ddc8;">🧪 API Test Results</h2>
        <div style="margin: 20px 0;">
          <span style="color: #4ec9b0;">Total: ${this.results.length}</span> | 
          <span style="color: #4fc3f7;">Passed: ${passCount}</span> | 
          <span style="color: #f48771;">Failed: ${failCount}</span>
        </div>
        <table style="width: 100%; border-collapse: collapse;">
          <thead>
            <tr style="border-bottom: 2px solid #333;">
              <th style="text-align: left; padding: 8px;">Status</th>
              <th style="text-align: left; padding: 8px;">Test Name</th>
              <th style="text-align: left; padding: 8px;">Endpoint</th>
              <th style="text-align: right; padding: 8px;">Duration</th>
            </tr>
          </thead>
          <tbody>
    `;

    this.results.forEach(result => {
      const statusIcon = result.success ? '✓' : '✗';
      const statusColor = result.success ? '#4fc3f7' : '#f48771';
      html += `
        <tr style="border-bottom: 1px solid #333;">
          <td style="padding: 8px; color: ${statusColor}; font-weight: bold;">${statusIcon}</td>
          <td style="padding: 8px;">${result.name}</td>
          <td style="padding: 8px; color: #9cdcfe;">${result.endpoint}</td>
          <td style="padding: 8px; text-align: right;">${result.duration}ms</td>
        </tr>
      `;
    });

    html += `
          </tbody>
        </table>
      </div>
    `;

    return html;
  }
}

// ============================================================================
// GLOBAL API CLIENT INSTANCE
// ============================================================================

const apiClient = new APIClient();
const apiTestSuite = new APITestSuite(apiClient);

// ============================================================================
// CONVENIENCE FUNCTIONS
// ============================================================================

// Export simplified API functions
window.api = {
  // Connection
  listPorts: () => apiClient.get(API_ENDPOINTS.connection.listPorts),
  connectPort: (port, baudrate) => apiClient.post(API_ENDPOINTS.connection.connect, { port, baudrate }),
  disconnect: () => apiClient.post(API_ENDPOINTS.connection.disconnect),
  connectionStatus: () => apiClient.get(API_ENDPOINTS.connection.status),
  autoDetect: () => apiClient.post(API_ENDPOINTS.connection.autoDetect),

  // Sensor
  getLatest: () => apiClient.get(API_ENDPOINTS.sensor.latest),
  getHistory: (params) => apiClient.get(`${API_ENDPOINTS.sensor.history}?${new URLSearchParams(params)}`),
  getSensorStats: () => apiClient.get(API_ENDPOINTS.sensor.stats),

  // Prediction
  predict: (data) => apiClient.post(API_ENDPOINTS.prediction.predict, data),
  modelStatus: () => apiClient.get(API_ENDPOINTS.prediction.modelStatus),
  modelInfo: () => apiClient.get(API_ENDPOINTS.prediction.modelInfo),

  // Monitoring
  getAlerts: () => apiClient.get(API_ENDPOINTS.monitoring.alerts),
  getLogs: (page, pageSize) => apiClient.get(`${API_ENDPOINTS.monitoring.logs}?page=${page}&page_size=${pageSize}`),
  getHealth: () => apiClient.get(API_ENDPOINTS.monitoring.health),

  // Dataset
  listDatasets: () => apiClient.get(API_ENDPOINTS.dataset.list),
  getDatasetInfo: (name) => apiClient.get(`${API_ENDPOINTS.dataset.info}?name=${name}`),
  deleteDataset: (name) => apiClient.delete(`${API_ENDPOINTS.dataset.delete}?name=${name}`),

  // Testing
  runTests: () => apiTestSuite.runAllTests(),
  getTestResults: () => apiTestSuite.results,
  generateReport: () => apiTestSuite.generateHTMLReport()
};

// ============================================================================
// CONSOLE HELPER
// ============================================================================

console.log('%c🚀 Gandiva API Test Suite Loaded!', 'color: #33ddc8; font-size: 16px; font-weight: bold;');
console.log('%cRun api.runTests() to test all endpoints', 'color: #9cdcfe;');
console.log('%cAccess individual endpoints via window.api object', 'color: #9cdcfe;');

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    APIClient,
    APITestSuite,
    API_ENDPOINTS,
    apiClient,
    apiTestSuite
  };
}
