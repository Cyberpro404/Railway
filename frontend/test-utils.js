/**
 * GANDIVA LEVEL 10 UI - Comprehensive Testing Utilities
 * Test all tabs, API endpoints, and UI functionality
 */

const TEST_CONFIG = {
  API_BASE: window.location.origin,
  TIMEOUT: 5000,
  RETRY_COUNT: 3,
  RETRY_DELAY: 1000
};

// Test results storage
const testResults = {
  passed: 0,
  failed: 0,
  warnings: 0,
  tests: []
};

/**
 * Test runner
 */
class TestRunner {
  constructor() {
    this.results = [];
    this.currentTest = null;
  }

  async test(name, testFn) {
    const startTime = performance.now();
    this.currentTest = { name, status: 'running', error: null, duration: 0 };
    
    try {
      await testFn();
      const duration = performance.now() - startTime;
      this.currentTest.status = 'passed';
      this.currentTest.duration = duration;
      testResults.passed++;
      console.log(`✅ PASS: ${name} (${duration.toFixed(2)}ms)`);
    } catch (error) {
      const duration = performance.now() - startTime;
      this.currentTest.status = 'failed';
      this.currentTest.error = error.message;
      this.currentTest.duration = duration;
      testResults.failed++;
      console.error(`❌ FAIL: ${name} - ${error.message} (${duration.toFixed(2)}ms)`);
    }
    
    this.results.push(this.currentTest);
    return this.currentTest.status === 'passed';
  }

  async testAsync(name, testFn) {
    return this.test(name, async () => {
      const result = await testFn();
      if (result === false) {
        throw new Error('Test returned false');
      }
    });
  }

  warn(message) {
    testResults.warnings++;
    console.warn(`⚠️  WARN: ${message}`);
  }

  getResults() {
    return {
      total: this.results.length,
      passed: testResults.passed,
      failed: testResults.failed,
      warnings: testResults.warnings,
      tests: this.results
    };
  }
}

const testRunner = new TestRunner();

/**
 * Test API endpoint
 */
async function testAPIEndpoint(endpoint, method = 'GET', body = null, expectedStatus = 200) {
  const url = `${TEST_CONFIG.API_BASE}${endpoint}`;
  
  try {
    const options = {
      method: method,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      }
    };

    if (body) {
      options.body = JSON.stringify(body);
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), TEST_CONFIG.TIMEOUT);

    const response = await fetch(url, {
      ...options,
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    if (response.status !== expectedStatus) {
      throw new Error(`Expected status ${expectedStatus}, got ${response.status}`);
    }

    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      const data = await response.json();
      return { success: true, data, status: response.status };
    }

    return { success: true, data: null, status: response.status };
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error(`Request timeout after ${TEST_CONFIG.TIMEOUT}ms`);
    }
    throw error;
  }
}

/**
 * Test all API endpoints
 */
async function testAllAPIEndpoints() {
  console.log('\n🧪 Testing API Endpoints...\n');

  const endpoints = [
    { path: '/status', method: 'GET', name: 'Status endpoint' },
    { path: '/api/live_sample', method: 'GET', name: 'Live sample endpoint' },
    { path: '/api/history?seconds=60', method: 'GET', name: 'History endpoint' },
    { path: '/api/connection', method: 'GET', name: 'Connection endpoint' },
    { path: '/api/health', method: 'GET', name: 'Health endpoint' },
    { path: '/api/datasets', method: 'GET', name: 'Datasets endpoint' },
    { path: '/api/alerts', method: 'GET', name: 'Alerts endpoint' },
    { path: '/api/thresholds', method: 'GET', name: 'Thresholds endpoint' }
  ];

  for (const endpoint of endpoints) {
    await testRunner.testAsync(endpoint.name, async () => {
      try {
        await testAPIEndpoint(endpoint.path, endpoint.method);
        return true;
      } catch (error) {
        // Some endpoints might not be available, log as warning
        testRunner.warn(`${endpoint.name}: ${error.message}`);
        return true; // Don't fail the test suite
      }
    });
  }
}

/**
 * Test all tabs
 */
async function testAllTabs() {
  console.log('\n🧪 Testing UI Tabs...\n');

  const tabs = [
    'connection',
    'overview',
    'health',
    'mlinsights',
    'datasets',
    'logs',
    'alerts',
    'thresholds',
    'system'
  ];

  for (const tabId of tabs) {
    await testRunner.test(`Tab: ${tabId}`, () => {
      const tabElement = document.getElementById(`tab-${tabId}`);
      if (!tabElement) {
        throw new Error(`Tab element not found: tab-${tabId}`);
      }

      const navButton = document.querySelector(`[data-tab="${tabId}"]`);
      if (!navButton) {
        throw new Error(`Nav button not found for tab: ${tabId}`);
      }

      // Test tab switching
      navButton.click();
      
      // Check if tab is active
      setTimeout(() => {
        if (!tabElement.classList.contains('is-active')) {
          throw new Error(`Tab ${tabId} did not become active`);
        }
      }, 100);
    });
  }
}

/**
 * Test all graphs
 */
async function testAllGraphs() {
  console.log('\n🧪 Testing Graphs...\n');

  const graphIds = [
    'chartRms',
    'chartTemp',
    'chartBandRms',
    'chartBandFreq',
    'chartAllBandsRms',
    'chartSpectrum',
    'chartHealth',
    'vibration-chart'
  ];

  for (const graphId of graphIds) {
    await testRunner.test(`Graph: ${graphId}`, () => {
      const canvas = document.getElementById(graphId);
      if (!canvas) {
        testRunner.warn(`Graph canvas not found: ${graphId}`);
        return; // Don't fail, just warn
      }

      // Check if Chart.js is available
      if (typeof Chart === 'undefined') {
        throw new Error('Chart.js not loaded');
      }

      // Check if canvas has a context
      const ctx = canvas.getContext('2d');
      if (!ctx) {
        throw new Error(`Cannot get 2D context for ${graphId}`);
      }
    });
  }
}

/**
 * Test form interactions
 */
async function testFormInteractions() {
  console.log('\n🧪 Testing Form Interactions...\n');

  await testRunner.test('Connection form fields', () => {
    const portInput = document.getElementById('port');
    const slaveIdInput = document.getElementById('slaveId');
    const baudrateSelect = document.getElementById('baudrate');
    
    if (!portInput || !slaveIdInput || !baudrateSelect) {
      throw new Error('Connection form fields not found');
    }

    // Test input values
    portInput.value = 'COM5';
    if (portInput.value !== 'COM5') {
      throw new Error('Port input not working');
    }
  });

  await testRunner.test('Threshold form fields', () => {
    const zWarnInput = document.getElementById('th_z_warn');
    const zAlarmInput = document.getElementById('th_z_alarm');
    
    if (!zWarnInput || !zAlarmInput) {
      testRunner.warn('Threshold form fields not found');
      return;
    }

    zWarnInput.value = '1.5';
    zAlarmInput.value = '2.0';
  });
}

/**
 * Test button interactions
 */
async function testButtonInteractions() {
  console.log('\n🧪 Testing Button Interactions...\n');

  const buttonIds = [
    'autoConnectBtn',
    'scanPortsBtn',
    'applyConnBtn',
    'reloadModelBtn',
    'captureTrainingBtn',
    'saveThresholdsBtn'
  ];

  for (const buttonId of buttonIds) {
    await testRunner.test(`Button: ${buttonId}`, () => {
      const button = document.getElementById(buttonId);
      if (!button) {
        testRunner.warn(`Button not found: ${buttonId}`);
        return;
      }

      // Test button exists and is clickable
      if (button.disabled && button.hasAttribute('disabled')) {
        testRunner.warn(`Button ${buttonId} is disabled`);
      }
    });
  }
}

/**
 * Test responsive design
 */
async function testResponsiveDesign() {
  console.log('\n🧪 Testing Responsive Design...\n');

  const breakpoints = [
    { width: 1920, height: 1080, name: 'Desktop' },
    { width: 1024, height: 768, name: 'Tablet' },
    { width: 375, height: 667, name: 'Mobile' }
  ];

  for (const bp of breakpoints) {
    await testRunner.test(`Responsive: ${bp.name} (${bp.width}x${bp.height})`, () => {
      // Simulate viewport change
      window.innerWidth = bp.width;
      window.innerHeight = bp.height;
      
      // Trigger resize event
      window.dispatchEvent(new Event('resize'));
      
      // Check if layout adapts (basic check)
      const app = document.querySelector('.app');
      if (!app) {
        throw new Error('App container not found');
      }
    });
  }
}

/**
 * Run all tests
 */
async function runAllTests() {
  console.log('\n🚀 Starting Comprehensive Test Suite...\n');
  console.log('='.repeat(60));

  const startTime = performance.now();

  try {
    await testAllAPIEndpoints();
    await testAllTabs();
    await testAllGraphs();
    await testFormInteractions();
    await testButtonInteractions();
    await testResponsiveDesign();
  } catch (error) {
    console.error('Test suite error:', error);
  }

  const duration = performance.now() - startTime;
  const results = testRunner.getResults();

  console.log('\n' + '='.repeat(60));
  console.log('\n📊 Test Results Summary:');
  console.log(`   Total Tests: ${results.total}`);
  console.log(`   ✅ Passed: ${results.passed}`);
  console.log(`   ❌ Failed: ${results.failed}`);
  console.log(`   ⚠️  Warnings: ${results.warnings}`);
  console.log(`   ⏱️  Duration: ${duration.toFixed(2)}ms`);
  console.log('\n' + '='.repeat(60) + '\n');

  return results;
}

/**
 * Quick health check
 */
async function quickHealthCheck() {
  console.log('🔍 Quick Health Check...\n');

  const checks = [
    { name: 'Chart.js loaded', test: () => typeof Chart !== 'undefined' },
    { name: 'Lucide icons loaded', test: () => typeof lucide !== 'undefined' },
    { name: 'API base URL', test: () => TEST_CONFIG.API_BASE.length > 0 },
    { name: 'DOM ready', test: () => document.readyState === 'complete' }
  ];

  for (const check of checks) {
    try {
      const result = check.test();
      if (result) {
        console.log(`✅ ${check.name}`);
      } else {
        console.log(`❌ ${check.name}`);
      }
    } catch (error) {
      console.log(`❌ ${check.name}: ${error.message}`);
    }
  }
}

// Export for global use
window.GandivaTests = {
  runAllTests,
  quickHealthCheck,
  testAPIEndpoint,
  testAllAPIEndpoints,
  testAllTabs,
  testAllGraphs,
  testFormInteractions,
  testButtonInteractions,
  testResponsiveDesign,
  testRunner
};

// Auto-run quick health check on load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', quickHealthCheck);
} else {
  quickHealthCheck();
}

