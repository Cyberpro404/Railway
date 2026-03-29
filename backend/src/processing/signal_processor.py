"""
Signal Processor - Advanced signal processing for vibration data.
Includes speed normalization, temperature compensation, and rolling baseline.
"""
import logging
import numpy as np
from typing import Dict, Any, Optional, List, Deque
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from scipy import signal
from scipy.stats import norm

logger = logging.getLogger(__name__)


@dataclass
class ProcessingConfig:
    """Signal processing configuration"""
    # Baseline settings
    baseline_window_size: int = 300  # 5 minutes at 1 Hz
    baseline_update_interval: int = 60  # Update every 60 samples
    
    # Temperature compensation
    temp_compensation_enabled: bool = True
    temp_reference: float = 25.0  # Reference temperature in °C
    temp_coefficient: float = 0.02  # Vibration change per °C
    
    # Speed normalization
    speed_normalization_enabled: bool = False
    reference_speed_kmh: float = 60.0
    speed_exponent: float = 1.5  # Exponent for speed scaling
    
    # Filtering
    lowpass_cutoff: float = 1000.0  # Hz
    highpass_cutoff: float = 1.0  # Hz
    filter_order: int = 4
    
    # Spectral analysis
    fft_window_size: int = 1024
    spectral_bands: List[tuple] = field(default_factory=lambda: [
        (1, 10),      # Band 1: Very low frequency
        (10, 50),     # Band 2: Low frequency
        (50, 100),    # Band 3: Mid frequency
        (100, 500),   # Band 4: High frequency
        (500, 1000),  # Band 5: Very high frequency
    ])


@dataclass
class BaselineStats:
    """Rolling baseline statistics"""
    mean: float = 0.0
    std: float = 0.0
    min: float = 0.0
    max: float = 0.0
    count: int = 0
    last_update: Optional[datetime] = None


class SignalProcessor:
    """
    Advanced signal processor for vibration monitoring.
    Provides: temperature compensation, speed normalization, baseline calculation, spectral analysis.
    """
    
    def __init__(self, device_id: str, config: Optional[ProcessingConfig] = None):
        self.device_id = device_id
        self.config = config or ProcessingConfig()
        
        # Data buffers for rolling calculations
        self._z_rms_buffer: Deque[float] = deque(maxlen=self.config.baseline_window_size)
        self._x_rms_buffer: Deque[float] = deque(maxlen=self.config.baseline_window_size)
        self._temp_buffer: Deque[float] = deque(maxlen=self.config.baseline_window_size)
        
        # Baseline statistics
        self._z_baseline = BaselineStats()
        self._x_baseline = BaselineStats()
        self._temp_baseline = BaselineStats()
        
        # Update counter
        self._sample_count = 0
        
        # Spectral buffer (for FFT)
        self._spectral_buffer: Deque[float] = deque(maxlen=self.config.fft_window_size)
        
        logger.info(f"SignalProcessor initialized for device {device_id}")
    
    def process(self, data: Dict[str, Any], train_speed_kmh: Optional[float] = None) -> Dict[str, Any]:
        """
        Process raw sensor data.
        
        Args:
            data: Raw sensor data from Modbus
            train_speed_kmh: Optional train speed for normalization
            
        Returns:
            Processed data with normalized values and derived metrics
        """
        if not data:
            return {}
        
        result = data.copy()
        
        # Extract raw values
        z_rms = data.get("z_rms_mm", data.get("z_rms", 0))
        x_rms = data.get("x_rms_mm", data.get("x_rms", 0))
        temperature = data.get("temperature", 25.0)
        
        # Update buffers
        self._update_buffers(z_rms, x_rms, temperature)
        
        # Calculate baselines (adaptive thresholds)
        self._update_baselines()
        
        # Temperature compensation
        if self.config.temp_compensation_enabled:
            z_rms, x_rms = self._compensate_temperature(z_rms, x_rms, temperature)
            result["temperature_compensated"] = True
            result["temperature_compensation_factor"] = round(
                1 + self.config.temp_coefficient * (temperature - self.config.temp_reference), 4
            )
        
        # Speed normalization
        if self.config.speed_normalization_enabled and train_speed_kmh:
            z_rms, x_rms = self._normalize_speed(z_rms, x_rms, train_speed_kmh)
            result["speed_normalized"] = True
            result["normalization_speed"] = train_speed_kmh
        
        # Calculate normalized values (relative to baseline)
        if self._z_baseline.std > 0:
            result["z_rms_normalized"] = round((z_rms - self._z_baseline.mean) / self._z_baseline.std, 3)
            result["z_rms_baseline"] = round(self._z_baseline.mean, 3)
            result["z_rms_sigma"] = round(self._z_baseline.std, 3)
        
        if self._x_baseline.std > 0:
            result["x_rms_normalized"] = round((x_rms - self._x_baseline.mean) / self._x_baseline.std, 3)
            result["x_rms_baseline"] = round(self._x_baseline.mean, 3)
            result["x_rms_sigma"] = round(self._x_baseline.std, 3)
        
        # Calculate trends
        result["z_rms_trend"] = self._calculate_trend(self._z_rms_buffer)
        result["x_rms_trend"] = self._calculate_trend(self._x_rms_buffer)
        result["temp_trend"] = self._calculate_trend(self._temp_buffer)
        
        # Calculate overall metrics
        result["overall_rms"] = round(np.sqrt(z_rms**2 + x_rms**2), 3)
        
        # Multi-parameter correlation
        result["correlation_metrics"] = self._calculate_correlations()
        
        # Spectral analysis (if frequency data available)
        if "z_peak_freq" in data and data["z_peak_freq"] > 0:
            result["spectral_analysis"] = self._analyze_spectral_content(data)
        
        # Health score calculation
        result["health_scores"] = self._calculate_health_scores(z_rms, x_rms, temperature)
        
        # ISO classification
        result["iso_class"] = self._classify_iso(z_rms)
        
        # Update processed values
        result["z_rms_processed"] = round(z_rms, 3)
        result["x_rms_processed"] = round(x_rms, 3)
        result["processing_timestamp"] = datetime.now().isoformat()
        
        return result
    
    def _update_buffers(self, z_rms: float, x_rms: float, temperature: float):
        """Update rolling buffers"""
        self._z_rms_buffer.append(z_rms)
        self._x_rms_buffer.append(x_rms)
        self._temp_buffer.append(temperature)
        self._sample_count += 1
    
    def _update_baselines(self):
        """Update rolling baseline statistics"""
        # Only update periodically
        if self._sample_count % self.config.baseline_update_interval != 0:
            return
        
        if len(self._z_rms_buffer) >= 10:
            z_array = np.array(list(self._z_rms_buffer))
            self._z_baseline.mean = float(np.mean(z_array))
            self._z_baseline.std = float(np.std(z_array))
            self._z_baseline.min = float(np.min(z_array))
            self._z_baseline.max = float(np.max(z_array))
            self._z_baseline.count = len(z_array)
            self._z_baseline.last_update = datetime.now()
        
        if len(self._x_rms_buffer) >= 10:
            x_array = np.array(list(self._x_rms_buffer))
            self._x_baseline.mean = float(np.mean(x_array))
            self._x_baseline.std = float(np.std(x_array))
            self._x_baseline.min = float(np.min(x_array))
            self._x_baseline.max = float(np.max(x_array))
            self._x_baseline.count = len(x_array)
            self._x_baseline.last_update = datetime.now()
        
        if len(self._temp_buffer) >= 10:
            t_array = np.array(list(self._temp_buffer))
            self._temp_baseline.mean = float(np.mean(t_array))
            self._temp_baseline.std = float(np.std(t_array))
            self._temp_baseline.count = len(t_array)
            self._temp_baseline.last_update = datetime.now()
    
    def _compensate_temperature(self, z_rms: float, x_rms: float, temperature: float) -> tuple:
        """
        Compensate vibration readings for temperature effects.
        Vibration typically increases with temperature due to bearing expansion.
        """
        temp_diff = temperature - self.config.temp_reference
        compensation_factor = 1 / (1 + self.config.temp_coefficient * temp_diff)
        
        z_compensated = z_rms * compensation_factor
        x_compensated = x_rms * compensation_factor
        
        return z_compensated, x_compensated
    
    def _normalize_speed(self, z_rms: float, x_rms: float, speed_kmh: float) -> tuple:
        """
        Normalize vibration readings for train speed.
        Vibration generally scales with speed according to power law.
        """
        if speed_kmh <= 0:
            return z_rms, x_rms
        
        speed_ratio = self.config.reference_speed_kmh / speed_kmh
        normalization_factor = speed_ratio ** self.config.speed_exponent
        
        z_normalized = z_rms * normalization_factor
        x_normalized = x_rms * normalization_factor
        
        return z_normalized, x_normalized
    
    def _calculate_trend(self, buffer: Deque[float], window: int = 10) -> float:
        """Calculate short-term trend using linear regression"""
        if len(buffer) < window:
            return 0.0
        
        recent = list(buffer)[-window:]
        x = np.arange(len(recent))
        y = np.array(recent)
        
        # Simple linear regression slope
        if len(x) > 1:
            slope = np.polyfit(x, y, 1)[0]
            return round(slope, 4)
        return 0.0
    
    def _calculate_correlations(self) -> Dict[str, float]:
        """Calculate correlations between multiple parameters"""
        correlations = {}
        
        if len(self._z_rms_buffer) >= 10 and len(self._temp_buffer) >= 10:
            z_array = np.array(list(self._z_rms_buffer)[-100:])
            t_array = np.array(list(self._temp_buffer)[-100:])
            
            if len(z_array) == len(t_array):
                correlations["z_temp_correlation"] = round(np.corrcoef(z_array, t_array)[0, 1], 3)
        
        if len(self._z_rms_buffer) >= 10 and len(self._x_rms_buffer) >= 10:
            z_array = np.array(list(self._z_rms_buffer)[-100:])
            x_array = np.array(list(self._x_rms_buffer)[-100:])
            
            if len(z_array) == len(x_array):
                correlations["zx_correlation"] = round(np.corrcoef(z_array, x_array)[0, 1], 3)
        
        return correlations
    
    def _analyze_spectral_content(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze spectral content of vibration signal"""
        analysis = {
            "dominant_frequency": data.get("z_peak_freq", 0),
            "frequency_z": data.get("z_peak_freq", 0),
            "frequency_x": data.get("x_peak_freq", 0),
            "frequency_ratio": 0.0,
            "spectral_imbalance": 0.0
        }
        
        z_freq = data.get("z_peak_freq", 0)
        x_freq = data.get("x_peak_freq", 0)
        
        if z_freq > 0 and x_freq > 0:
            analysis["frequency_ratio"] = round(x_freq / z_freq, 2)
            analysis["spectral_imbalance"] = round(abs(z_freq - x_freq) / max(z_freq, x_freq), 3)
        
        # Calculate band energy ratios if we have enough data
        if len(self._spectral_buffer) >= self.config.fft_window_size:
            analysis["band_analysis"] = self._calculate_band_energies()
        
        return analysis
    
    def _calculate_band_energies(self) -> Dict[str, float]:
        """Calculate energy distribution across frequency bands"""
        # This is a placeholder - actual implementation would require raw time-series data
        # For now, return empty structure
        return {
            "band_1_10hz": 0.0,
            "band_10_50hz": 0.0,
            "band_50_100hz": 0.0,
            "band_100_500hz": 0.0,
            "band_500_1000hz": 0.0,
        }
    
    def _calculate_health_scores(self, z_rms: float, x_rms: float, temperature: float) -> Dict[str, Any]:
        """Calculate health scores for different components"""
        scores = {}
        
        # Bearing health (based on HF RMS and kurtosis)
        hf_rms = max(z_rms, x_rms)  # Simplified
        if hf_rms < 2.0:
            bearing_score = 95
        elif hf_rms < 5.0:
            bearing_score = 85 - (hf_rms - 2.0) * 5
        elif hf_rms < 10.0:
            bearing_score = 70 - (hf_rms - 5.0) * 4
        else:
            bearing_score = max(30, 50 - (hf_rms - 10.0) * 2)
        
        scores["bearing_health"] = round(bearing_score, 1)
        
        # Temperature health
        if temperature < 40:
            temp_score = 100
        elif temperature < 60:
            temp_score = 90 - (temperature - 40) * 1.5
        elif temperature < 80:
            temp_score = 60 - (temperature - 60) * 2
        else:
            temp_score = max(20, 20 - (temperature - 80))
        
        scores["temperature_health"] = round(temp_score, 1)
        
        # Overall health (weighted average)
        scores["overall"] = round(
            bearing_score * 0.6 + temp_score * 0.4,
            1
        )
        
        return scores
    
    def _classify_iso(self, z_rms: float) -> str:
        """Classify vibration according to ISO 10816 standards"""
        if z_rms < 1.8:
            return "Zone A"  # Good
        elif z_rms < 2.8:
            return "Zone B"  # Satisfactory
        elif z_rms < 4.5:
            return "Zone C"  # Unsatisfactory
        else:
            return "Zone D"  # Unacceptable
    
    def get_baseline_stats(self) -> Dict[str, Any]:
        """Get current baseline statistics"""
        return {
            "z_rms": {
                "mean": round(self._z_baseline.mean, 3),
                "std": round(self._z_baseline.std, 3),
                "min": round(self._z_baseline.min, 3),
                "max": round(self._z_baseline.max, 3),
                "samples": self._z_baseline.count,
                "last_update": self._z_baseline.last_update.isoformat() if self._z_baseline.last_update else None
            },
            "x_rms": {
                "mean": round(self._x_baseline.mean, 3),
                "std": round(self._x_baseline.std, 3),
                "min": round(self._x_baseline.min, 3),
                "max": round(self._x_baseline.max, 3),
                "samples": self._x_baseline.count,
                "last_update": self._x_baseline.last_update.isoformat() if self._x_baseline.last_update else None
            },
            "temperature": {
                "mean": round(self._temp_baseline.mean, 1),
                "std": round(self._temp_baseline.std, 1),
                "samples": self._temp_baseline.count
            }
        }
    
    def reset_baselines(self):
        """Reset baseline calculations (e.g., after maintenance)"""
        self._z_rms_buffer.clear()
        self._x_rms_buffer.clear()
        self._temp_buffer.clear()
        self._z_baseline = BaselineStats()
        self._x_baseline = BaselineStats()
        self._temp_baseline = BaselineStats()
        self._sample_count = 0
        logger.info(f"[{self.device_id}] Baselines reset")
