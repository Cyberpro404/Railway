/**
 * ============================================================================
 * GANDIVA LEVEL 10 - PROFESSIONAL LOADING STATES COMPONENT
 * Enterprise-grade loading animations and skeletons
 * ============================================================================
 */

// ============================================================================
// LOADING STATE MANAGER
// ============================================================================

class LoadingStateManager {
  constructor() {
    this.activeLoaders = new Map();
  }

  /**
   * Show loading overlay on element
   */
  show(elementId, options = {}) {
    const {
      message = 'Loading...',
      type = 'spinner', // spinner, dots, pulse, skeleton
      size = 'medium', // small, medium, large
      overlay = true
    } = options;

    const element = document.getElementById(elementId);
    if (!element) {
      console.warn(`[Loading] Element not found: ${elementId}`);
      return null;
    }

    // Remove existing loader if present
    this.hide(elementId);

    const loaderId = `loader-${elementId}-${Date.now()}`;
    const loader = this.createLoader(type, message, size, overlay);
    loader.id = loaderId;
    
    element.style.position = 'relative';
    element.appendChild(loader);
    
    this.activeLoaders.set(elementId, loaderId);
    
    return loaderId;
  }

  /**
   * Hide loading state
   */
  hide(elementId) {
    const loaderId = this.activeLoaders.get(elementId);
    if (loaderId) {
      const loader = document.getElementById(loaderId);
      if (loader) {
        loader.classList.add('animate-fadeOut');
        setTimeout(() => loader.remove(), 300);
      }
      this.activeLoaders.delete(elementId);
    }
  }

  /**
   * Create loader element
   */
  createLoader(type, message, size, overlay) {
    const container = document.createElement('div');
    container.className = `loading-container animate-fadeIn`;
    
    if (overlay) {
      container.style.cssText = `
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(7, 12, 24, 0.85);
        backdrop-filter: blur(4px);
        z-index: 999;
        border-radius: inherit;
      `;
    }

    let loaderHTML = '';
    
    switch (type) {
      case 'spinner':
        loaderHTML = this.createSpinner(size);
        break;
      case 'dots':
        loaderHTML = this.createDots(size);
        break;
      case 'pulse':
        loaderHTML = this.createPulse(size);
        break;
      case 'bars':
        loaderHTML = this.createBars(size);
        break;
      default:
        loaderHTML = this.createSpinner(size);
    }

    container.innerHTML = `
      <div style="text-align: center;">
        ${loaderHTML}
        ${message ? `<div style="margin-top: 15px; font-size: 13px; color: rgba(237, 242, 251, 0.7);">${message}</div>` : ''}
      </div>
    `;

    return container;
  }

  /**
   * Create spinner loader
   */
  createSpinner(size) {
    const sizes = {
      small: '24px',
      medium: '40px',
      large: '60px'
    };
    
    const spinnerSize = sizes[size] || sizes.medium;

    return `
      <div style="
        width: ${spinnerSize};
        height: ${spinnerSize};
        border: 3px solid rgba(51, 221, 200, 0.2);
        border-top-color: #33ddc8;
        border-radius: 50%;
        margin: 0 auto;
        animation: spin 0.8s linear infinite;
      "></div>
    `;
  }

  /**
   * Create dots loader
   */
  createDots(size) {
    const sizes = {
      small: '6px',
      medium: '10px',
      large: '14px'
    };
    
    const dotSize = sizes[size] || sizes.medium;

    return `
      <div style="display: flex; gap: 8px; justify-content: center;">
        <span style="
          width: ${dotSize};
          height: ${dotSize};
          background: #33ddc8;
          border-radius: 50%;
          display: inline-block;
          animation: dotPulse 1.4s infinite ease-in-out both;
        "></span>
        <span style="
          width: ${dotSize};
          height: ${dotSize};
          background: #33ddc8;
          border-radius: 50%;
          display: inline-block;
          animation: dotPulse 1.4s infinite ease-in-out both;
          animation-delay: 0.2s;
        "></span>
        <span style="
          width: ${dotSize};
          height: ${dotSize};
          background: #33ddc8;
          border-radius: 50%;
          display: inline-block;
          animation: dotPulse 1.4s infinite ease-in-out both;
          animation-delay: 0.4s;
        "></span>
      </div>
    `;
  }

  /**
   * Create pulse loader
   */
  createPulse(size) {
    const sizes = {
      small: '30px',
      medium: '50px',
      large: '70px'
    };
    
    const pulseSize = sizes[size] || sizes.medium;

    return `
      <div style="
        position: relative;
        width: ${pulseSize};
        height: ${pulseSize};
        margin: 0 auto;
      ">
        <div style="
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: rgba(51, 221, 200, 0.6);
          border-radius: 50%;
          animation: pulseGlow 2s ease-in-out infinite;
        "></div>
        <div style="
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          width: 60%;
          height: 60%;
          background: #33ddc8;
          border-radius: 50%;
        "></div>
      </div>
    `;
  }

  /**
   * Create bars loader
   */
  createBars(size) {
    const heights = {
      small: '20px',
      medium: '30px',
      large: '40px'
    };
    
    const barHeight = heights[size] || heights.medium;

    return `
      <div style="display: flex; gap: 6px; justify-content: center; height: ${barHeight}; align-items: flex-end;">
        ${[...Array(5)].map((_, i) => `
          <div style="
            width: 4px;
            background: #33ddc8;
            border-radius: 2px;
            animation: wave 1.2s ease-in-out infinite;
            animation-delay: ${i * 0.1}s;
          "></div>
        `).join('')}
      </div>
    `;
  }

  /**
   * Show skeleton loader
   */
  showSkeleton(elementId, type = 'card') {
    const element = document.getElementById(elementId);
    if (!element) return;

    let skeletonHTML = '';

    switch (type) {
      case 'card':
        skeletonHTML = this.createSkeletonCard();
        break;
      case 'table':
        skeletonHTML = this.createSkeletonTable();
        break;
      case 'list':
        skeletonHTML = this.createSkeletonList();
        break;
      case 'chart':
        skeletonHTML = this.createSkeletonChart();
        break;
      default:
        skeletonHTML = this.createSkeletonCard();
    }

    const container = document.createElement('div');
    container.className = 'skeleton-container animate-fadeIn';
    container.id = `skeleton-${elementId}`;
    container.innerHTML = skeletonHTML;
    
    element.appendChild(container);
  }

  /**
   * Hide skeleton loader
   */
  hideSkeleton(elementId) {
    const skeleton = document.getElementById(`skeleton-${elementId}`);
    if (skeleton) {
      skeleton.classList.add('animate-fadeOut');
      setTimeout(() => skeleton.remove(), 300);
    }
  }

  /**
   * Create skeleton card
   */
  createSkeletonCard() {
    return `
      <div style="padding: 20px;">
        <div class="skeleton" style="height: 20px; width: 60%; margin-bottom: 15px;"></div>
        <div class="skeleton" style="height: 14px; width: 40%; margin-bottom: 20px;"></div>
        <div class="skeleton" style="height: 100px; width: 100%; margin-bottom: 15px;"></div>
        <div class="skeleton" style="height: 14px; width: 80%; margin-bottom: 8px;"></div>
        <div class="skeleton" style="height: 14px; width: 70%;"></div>
      </div>
    `;
  }

  /**
   * Create skeleton table
   */
  createSkeletonTable() {
    return `
      <div style="padding: 20px;">
        ${[...Array(5)].map(() => `
          <div style="display: flex; gap: 15px; margin-bottom: 15px;">
            <div class="skeleton" style="height: 16px; flex: 1;"></div>
            <div class="skeleton" style="height: 16px; flex: 1;"></div>
            <div class="skeleton" style="height: 16px; flex: 1;"></div>
          </div>
        `).join('')}
      </div>
    `;
  }

  /**
   * Create skeleton list
   */
  createSkeletonList() {
    return `
      <div style="padding: 20px;">
        ${[...Array(6)].map(() => `
          <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 15px;">
            <div class="skeleton" style="width: 40px; height: 40px; border-radius: 50%;"></div>
            <div style="flex: 1;">
              <div class="skeleton" style="height: 14px; width: 70%; margin-bottom: 8px;"></div>
              <div class="skeleton" style="height: 12px; width: 50%;"></div>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  /**
   * Create skeleton chart
   */
  createSkeletonChart() {
    return `
      <div style="padding: 20px; height: 300px; display: flex; align-items: flex-end; justify-content: space-around;">
        ${[...Array(8)].map((_, i) => {
          const height = 40 + Math.random() * 60;
          return `<div class="skeleton" style="width: 40px; height: ${height}%; border-radius: 4px;"></div>`;
        }).join('')}
      </div>
    `;
  }

  /**
   * Show progress bar
   */
  showProgress(elementId, progress = 0, message = '') {
    const element = document.getElementById(elementId);
    if (!element) return;

    const progressId = `progress-${elementId}`;
    let progressBar = document.getElementById(progressId);

    if (!progressBar) {
      progressBar = document.createElement('div');
      progressBar.id = progressId;
      progressBar.className = 'progress-container animate-fadeIn';
      progressBar.innerHTML = `
        <div style="padding: 20px;">
          ${message ? `<div style="font-size: 13px; color: rgba(237, 242, 251, 0.7); margin-bottom: 10px;">${message}</div>` : ''}
          <div style="
            height: 6px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 3px;
            overflow: hidden;
          ">
            <div class="progress-bar" style="
              height: 100%;
              background: linear-gradient(90deg, #33ddc8, #18c4d8);
              width: ${progress}%;
              transition: width 0.3s ease;
              border-radius: 3px;
            "></div>
          </div>
          <div class="progress-text" style="
            font-size: 12px;
            color: rgba(237, 242, 251, 0.5);
            margin-top: 8px;
            text-align: right;
          ">${progress}%</div>
        </div>
      `;
      element.appendChild(progressBar);
    } else {
      const bar = progressBar.querySelector('.progress-bar');
      const text = progressBar.querySelector('.progress-text');
      if (bar) bar.style.width = `${progress}%`;
      if (text) text.textContent = `${progress}%`;
    }
  }

  /**
   * Hide progress bar
   */
  hideProgress(elementId) {
    const progressBar = document.getElementById(`progress-${elementId}`);
    if (progressBar) {
      progressBar.classList.add('animate-fadeOut');
      setTimeout(() => progressBar.remove(), 300);
    }
  }
}

// ============================================================================
// GLOBAL INSTANCE
// ============================================================================

const loadingManager = new LoadingStateManager();

// ============================================================================
// CONVENIENCE FUNCTIONS
// ============================================================================

window.LoadingStates = {
  // Basic loading
  show: (elementId, options) => loadingManager.show(elementId, options),
  hide: (elementId) => loadingManager.hide(elementId),
  
  // Skeleton loaders
  showSkeleton: (elementId, type) => loadingManager.showSkeleton(elementId, type),
  hideSkeleton: (elementId) => loadingManager.hideSkeleton(elementId),
  
  // Progress bars
  showProgress: (elementId, progress, message) => loadingManager.showProgress(elementId, progress, message),
  hideProgress: (elementId) => loadingManager.hideProgress(elementId),
  
  // Quick loaders
  showSpinner: (elementId, message) => loadingManager.show(elementId, { type: 'spinner', message }),
  showDots: (elementId, message) => loadingManager.show(elementId, { type: 'dots', message }),
  showPulse: (elementId, message) => loadingManager.show(elementId, { type: 'pulse', message })
};

console.log('%c✓ Loading States Module Loaded', 'color: #46e68b; font-weight: bold');
