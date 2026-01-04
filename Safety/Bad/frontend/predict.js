/**
 * Project Gandiva - Frontend Prediction Client
 * 
 * This module provides functions to call the /predict endpoint
 * and handle fault classification results.
 */

// API Configuration
const API_BASE_URL = 'http://localhost:8000';  // Adjust if using different port

// Fault class labels (must match backend)
const FAULT_LABELS = {
    0: 'normal',
    1: 'misalignment',
    2: 'unbalance',
    3: 'looseness',
    4: 'crack'
};

// Fault severity colors for UI
const FAULT_COLORS = {
    normal: '#22c55e',      // green
    misalignment: '#f59e0b', // amber
    unbalance: '#f97316',    // orange
    looseness: '#ef4444',    // red
    crack: '#dc2626'         // dark red
};

/**
 * Send vibration features to the /predict endpoint.
 * 
 * @param {Object} features - Object containing 8 vibration features
 * @param {number} features.rms - Root Mean Square
 * @param {number} features.peak - Peak amplitude
 * @param {number} features.band_1x - 1x frequency band energy
 * @param {number} features.band_2x - 2x frequency band energy
 * @param {number} features.band_3x - 3x frequency band energy
 * @param {number} features.band_5x - 5x frequency band energy
 * @param {number} features.band_7x - 7x frequency band energy
 * @param {number} features.temperature - Sensor temperature
 * @returns {Promise<Object>} Prediction result
 */
async function predictFault(features) {
    try {
        const response = await fetch(`${API_BASE_URL}/predict`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(features),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail?.message || `HTTP ${response.status}`);
        }

        const result = await response.json();
        return result;

    } catch (error) {
        console.error('Prediction error:', error);
        throw error;
    }
}

/**
 * Send multiple samples for batch prediction.
 * 
 * @param {Array<Object>} samples - Array of feature objects
 * @returns {Promise<Array<Object>>} Array of prediction results
 */
async function predictBatch(samples) {
    try {
        const response = await fetch(`${API_BASE_URL}/predict/batch`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(samples),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail?.message || `HTTP ${response.status}`);
        }

        return await response.json();

    } catch (error) {
        console.error('Batch prediction error:', error);
        throw error;
    }
}

/**
 * Check if the ML model is loaded and ready.
 * 
 * @returns {Promise<Object>} Model status
 */
async function checkModelStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/model/status`);
        return await response.json();
    } catch (error) {
        console.error('Model status check failed:', error);
        return { loaded: false, error: error.message };
    }
}

/**
 * Format prediction result for display.
 * 
 * @param {Object} result - Prediction result from API
 * @returns {Object} Formatted result with UI-friendly properties
 */
function formatPredictionResult(result) {
    return {
        ...result,
        color: FAULT_COLORS[result.class_label],
        confidencePercent: (result.confidence * 100).toFixed(1) + '%',
        isNormal: result.class_index === 0,
        isCritical: result.class_index === 4,  // crack is critical
        probabilitiesFormatted: result.probabilities.map((p, i) => ({
            label: FAULT_LABELS[i],
            value: p,
            percent: (p * 100).toFixed(1) + '%'
        }))
    };
}


// ============================================================
// EXAMPLE USAGE
// ============================================================

// Example: Single prediction
async function exampleSinglePrediction() {
    const sensorData = {
        rms: 2.5,
        peak: 8.3,
        band_1x: 1.2,
        band_2x: 0.8,
        band_3x: 0.5,
        band_5x: 0.3,
        band_7x: 0.1,
        temperature: 45.2
    };

    try {
        const result = await predictFault(sensorData);
        console.log('Prediction:', result);
        // Output:
        // {
        //   class_index: 0,
        //   class_label: "normal",
        //   probabilities: [0.85, 0.05, 0.04, 0.03, 0.03],
        //   confidence: 0.85
        // }

        const formatted = formatPredictionResult(result);
        console.log('Formatted:', formatted);
    } catch (error) {
        console.error('Failed:', error.message);
    }
}


// Example: React component usage
/*
import React, { useState, useEffect } from 'react';

function FaultPredictionWidget({ sensorData }) {
    const [prediction, setPrediction] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const handlePredict = async () => {
        setLoading(true);
        setError(null);
        
        try {
            const result = await predictFault(sensorData);
            setPrediction(formatPredictionResult(result));
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fault-prediction">
            <button onClick={handlePredict} disabled={loading}>
                {loading ? 'Analyzing...' : 'Predict Fault'}
            </button>
            
            {error && (
                <div className="error">{error}</div>
            )}
            
            {prediction && (
                <div className="result" style={{ borderColor: prediction.color }}>
                    <h3 style={{ color: prediction.color }}>
                        {prediction.class_label.toUpperCase()}
                    </h3>
                    <p>Confidence: {prediction.confidencePercent}</p>
                    
                    <div className="probabilities">
                        {prediction.probabilitiesFormatted.map(p => (
                            <div key={p.label} className="prob-bar">
                                <span>{p.label}</span>
                                <div 
                                    className="bar" 
                                    style={{ width: p.percent }}
                                />
                                <span>{p.percent}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

export default FaultPredictionWidget;
*/


// Example: Plain HTML/JS usage
/*
<script>
document.getElementById('predictBtn').addEventListener('click', async () => {
    const features = {
        rms: parseFloat(document.getElementById('rms').value),
        peak: parseFloat(document.getElementById('peak').value),
        band_1x: parseFloat(document.getElementById('band_1x').value),
        band_2x: parseFloat(document.getElementById('band_2x').value),
        band_3x: parseFloat(document.getElementById('band_3x').value),
        band_5x: parseFloat(document.getElementById('band_5x').value),
        band_7x: parseFloat(document.getElementById('band_7x').value),
        temperature: parseFloat(document.getElementById('temperature').value)
    };
    
    try {
        const result = await predictFault(features);
        document.getElementById('result').innerHTML = `
            <strong>Prediction:</strong> ${result.class_label}<br>
            <strong>Confidence:</strong> ${(result.confidence * 100).toFixed(1)}%
        `;
    } catch (error) {
        document.getElementById('result').innerHTML = `Error: ${error.message}`;
    }
});
</script>
*/


// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        predictFault,
        predictBatch,
        checkModelStatus,
        formatPredictionResult,
        FAULT_LABELS,
        FAULT_COLORS
    };
}
