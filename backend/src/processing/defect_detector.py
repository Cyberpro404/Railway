"""
Defect Detector - Signature detection algorithms for railway rolling stock defects.
Implements detection for: wheel flats, bearing defects, imbalance, misalignment.
"""
import logging
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
from enum import Enum

logger = logging.getLogger(__name__)


class DefectType(Enum):
    """Types of mechanical defects"""
    WHEEL_FLAT = "wheel_flat"
    BEARING_OUTER_RACE = "bearing_outer_race"
    BEARING_INNER_RACE = "bearing_inner_race"
    BEARING_BALL = "bearing_ball"
    IMBALANCE = "imbalance"
    MISALIGNMENT = "misalignment"
    LOOSENESS = "looseness"
    GEAR_FAULT = "gear_fault"


class SeverityLevel(Enum):
    """Severity levels 1-5"""
    LEVEL_1 = 1  # Minor - monitor
    LEVEL_2 = 2  # Low - schedule inspection
    LEVEL_3 = 3  # Medium - inspect soon
    LEVEL_4 = 4  # High - inspect immediately
    LEVEL_5 = 5  # Critical - stop operation


@dataclass
class DefectSignature:
    """Detected defect signature"""
    defect_type: DefectType
    confidence_score: float  # 0-100%
    severity_level: int  # 1-5
    detected_frequency: Optional[float] = None
    amplitude: Optional[float] = None
    threshold_exceeded: Optional[float] = None
    supporting_metrics: Dict[str, float] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    device_id: str = ""


@dataclass
class DetectionConfig:
    """Configuration for defect detection algorithms"""
    # Wheel flat detection
    wheel_flat_threshold: float = 3.0  # Kurtosis threshold
    wheel_flat_peak_threshold: float = 10.0  # Peak acceleration threshold
    wheel_flat_freq_range: Tuple[float, float] = (5, 50)  # Hz
    
    # Bearing defect detection
    bearing_hf_threshold: float = 2.0  # HF RMS threshold (G)
    bearing_kurtosis_threshold: float = 3.5
    bearing_crest_factor_threshold: float = 6.0
    
    # Imbalance detection
    imbalance_rms_threshold: float = 4.0  # mm/s
    imbalance_crest_factor_max: float = 3.0  # Low crest factor indicates imbalance
    
    # Misalignment detection
    misalignment_axial_rise: float = 1.5  # Ratio of axial to radial
    misalignment_both_axes: bool = True  # Both axes elevated
    
    # Looseness detection
    looseness_half_freq: bool = True  # Half frequency components
    looseness_non_linear: bool = True  # Non-linear response
    
    # General settings
    min_confidence: float = 60.0  # Minimum confidence to report
    history_window: int = 50  # Samples for pattern matching


class DefectDetector:
    """
    Detects mechanical defects from vibration signatures.
    Uses statistical pattern matching and threshold-based detection.
    """
    
    def __init__(self, device_id: str, config: Optional[DetectionConfig] = None):
        self.device_id = device_id
        self.config = config or DetectionConfig()
        
        # History buffers for pattern detection
        self._peak_history: deque = deque(maxlen=self.config.history_window)
        self._kurtosis_history: deque = deque(maxlen=self.config.history_window)
        self._hf_rms_history: deque = deque(maxlen=self.config.history_window)
        self._rms_history: deque = deque(maxlen=self.config.history_window)
        
        # Detection state
        self._detection_count: Dict[DefectType, int] = {dt: 0 for dt in DefectType}
        self._last_detection: Dict[DefectType, datetime] = {}
        
        logger.info(f"DefectDetector initialized for device {device_id}")
    
    def detect(self, data: Dict[str, Any]) -> List[DefectSignature]:
        """
        Analyze sensor data and detect defect signatures.
        
        Args:
            data: Processed sensor data
            
        Returns:
            List of detected defect signatures
        """
        detections: List[DefectSignature] = []
        
        # Update history buffers
        self._update_history(data)
        
        # Run detection algorithms
        wheel_flat = self._detect_wheel_flat(data)
        if wheel_flat:
            detections.append(wheel_flat)
        
        bearing_outer = self._detect_bearing_outer_race(data)
        if bearing_outer:
            detections.append(bearing_outer)
        
        bearing_inner = self._detect_bearing_inner_race(data)
        if bearing_inner:
            detections.append(bearing_inner)
        
        imbalance = self._detect_imbalance(data)
        if imbalance:
            detections.append(imbalance)
        
        misalignment = self._detect_misalignment(data)
        if misalignment:
            detections.append(misalignment)
        
        looseness = self._detect_looseness(data)
        if looseness:
            detections.append(looseness)
        
        # Update detection tracking
        for detection in detections:
            self._detection_count[detection.defect_type] += 1
            self._last_detection[detection.defect_type] = datetime.now()
        
        return detections
    
    def _update_history(self, data: Dict[str, Any]):
        """Update detection history buffers"""
        self._peak_history.append(data.get("z_peak_accel", 0))
        self._kurtosis_history.append(data.get("z_kurtosis", 0))
        self._hf_rms_history.append(data.get("z_hf_rms_accel", 0))
        self._rms_history.append(data.get("z_rms_mm", data.get("z_rms", 0)))
    
    def _detect_wheel_flat(self, data: Dict[str, Any]) -> Optional[DefectSignature]:
        """
        Detect wheel flats from vibration signature.
        
        Characteristics:
        - High kurtosis (impulsive events)
        - Periodic high-peak events
        - Elevated crest factor
        """
        z_kurtosis = data.get("z_kurtosis", 0)
        z_peak_accel = data.get("z_peak_accel", 0)
        z_crest_factor = data.get("z_crest_factor", 0)
        z_peak_freq = data.get("z_peak_freq", 0)
        
        # Check thresholds
        kurtosis_ok = z_kurtosis > self.config.wheel_flat_threshold
        peak_ok = z_peak_accel > self.config.wheel_flat_peak_threshold
        
        # Check for periodicity in peak history
        periodicity_score = self._calculate_periodicity(self._peak_history)
        
        # Calculate confidence
        confidence = 0.0
        if kurtosis_ok:
            confidence += 30
        if peak_ok:
            confidence += 30
        if periodicity_score > 0.7:
            confidence += 25
        if z_crest_factor > 5:
            confidence += 15
        
        if confidence >= self.config.min_confidence and (kurtosis_ok or peak_ok):
            severity = self._calculate_severity(
                z_kurtosis, self.config.wheel_flat_threshold,
                z_peak_accel, self.config.wheel_flat_peak_threshold
            )
            
            return DefectSignature(
                defect_type=DefectType.WHEEL_FLAT,
                confidence_score=round(min(confidence, 100), 1),
                severity_level=severity,
                detected_frequency=z_peak_freq if z_peak_freq > 0 else None,
                amplitude=z_peak_accel,
                threshold_exceeded=self.config.wheel_flat_peak_threshold,
                supporting_metrics={
                    "kurtosis": z_kurtosis,
                    "crest_factor": z_crest_factor,
                    "periodicity": round(periodicity_score, 2)
                },
                device_id=self.device_id
            )
        return None
    
    def _detect_bearing_outer_race(self, data: Dict[str, Any]) -> Optional[DefectSignature]:
        """
        Detect bearing outer race defects.
        
        Characteristics:
        - Elevated HF RMS (high-frequency acceleration)
        - Increased kurtosis
        - Specific frequency patterns (BPFI - Ball Pass Frequency Outer)
        """
        z_hf_rms = data.get("z_hf_rms_accel", 0)
        x_hf_rms = data.get("x_hf_rms_accel", 0)
        z_kurtosis = data.get("z_kurtosis", 0)
        
        avg_hf_rms = (z_hf_rms + x_hf_rms) / 2
        
        hf_ok = avg_hf_rms > self.config.bearing_hf_threshold
        kurtosis_ok = z_kurtosis > self.config.bearing_kurtosis_threshold
        
        confidence = 0.0
        if hf_ok:
            confidence += 40 + min(30, (avg_hf_rms - self.config.bearing_hf_threshold) * 10)
        if kurtosis_ok:
            confidence += 25
        if data.get("z_crest_factor", 0) > self.config.bearing_crest_factor_threshold:
            confidence += 20
        
        if confidence >= self.config.min_confidence:
            severity = self._calculate_severity(
                avg_hf_rms, self.config.bearing_hf_threshold,
                z_kurtosis, self.config.bearing_kurtosis_threshold
            )
            
            return DefectSignature(
                defect_type=DefectType.BEARING_OUTER_RACE,
                confidence_score=round(min(confidence, 100), 1),
                severity_level=severity,
                amplitude=avg_hf_rms,
                threshold_exceeded=self.config.bearing_hf_threshold,
                supporting_metrics={
                    "hf_rms_z": z_hf_rms,
                    "hf_rms_x": x_hf_rms,
                    "kurtosis": z_kurtosis,
                    "crest_factor": data.get("z_crest_factor", 0)
                },
                device_id=self.device_id
            )
        return None
    
    def _detect_bearing_inner_race(self, data: Dict[str, Any]) -> Optional[DefectSignature]:
        """
        Detect bearing inner race defects.
        
        Characteristics:
        - Modulated high-frequency content
        - Higher frequency than outer race defects
        - Often shows sidebands
        """
        z_hf_rms = data.get("z_hf_rms_accel", 0)
        z_kurtosis = data.get("z_kurtosis", 0)
        z_peak_freq = data.get("z_peak_freq", 0)
        
        # Inner race defects typically at higher frequencies
        freq_ok = z_peak_freq > 100 if z_peak_freq > 0 else True
        hf_ok = z_hf_rms > self.config.bearing_hf_threshold * 1.2  # Higher threshold
        
        confidence = 0.0
        if hf_ok:
            confidence += 35
        if z_kurtosis > self.config.bearing_kurtosis_threshold * 1.1:
            confidence += 30
        if freq_ok:
            confidence += 20
        
        # Check for modulation (simplified)
        if len(self._hf_rms_history) >= 10:
            variation = np.std(list(self._hf_rms_history)[-10:])
            if variation > 0.5:
                confidence += 15
        
        if confidence >= self.config.min_confidence:
            severity = self._calculate_severity(
                z_hf_rms, self.config.bearing_hf_threshold * 1.2
            )
            
            return DefectSignature(
                defect_type=DefectType.BEARING_INNER_RACE,
                confidence_score=round(min(confidence, 100), 1),
                severity_level=severity,
                detected_frequency=z_peak_freq if z_peak_freq > 0 else None,
                amplitude=z_hf_rms,
                threshold_exceeded=self.config.bearing_hf_threshold * 1.2,
                supporting_metrics={
                    "hf_rms": z_hf_rms,
                    "kurtosis": z_kurtosis,
                    "peak_frequency": z_peak_freq
                },
                device_id=self.device_id
            )
        return None
    
    def _detect_imbalance(self, data: Dict[str, Any]) -> Optional[DefectSignature]:
        """
        Detect rotor imbalance.
        
        Characteristics:
        - Elevated RMS at rotational frequency
        - Low crest factor (smooth sinusoidal)
        - Dominant 1x frequency component
        """
        z_rms = data.get("z_rms_mm", data.get("z_rms", 0))
        x_rms = data.get("x_rms_mm", data.get("x_rms", 0))
        z_crest_factor = data.get("z_crest_factor", 0)
        z_peak_freq = data.get("z_peak_freq", 0)
        
        # Imbalance thresholds
        rms_avg = (z_rms + x_rms) / 2
        rms_ok = rms_avg > self.config.imbalance_rms_threshold
        crest_ok = z_crest_factor < self.config.imbalance_crest_factor_max
        
        confidence = 0.0
        if rms_ok:
            confidence += 35 + min(25, (rms_avg - self.config.imbalance_rms_threshold) * 5)
        if crest_ok:
            confidence += 25  # Low crest factor supports imbalance
        if z_peak_freq > 10 and z_peak_freq < 100:  # Typical wheel rotation frequencies
            confidence += 20
        
        # Check if both axes elevated similarly
        if z_rms > 0 and x_rms > 0:
            ratio = max(z_rms, x_rms) / min(z_rms, x_rms)
            if ratio < 1.5:  # Similar levels on both axes
                confidence += 15
        
        if confidence >= self.config.min_confidence:
            severity = self._calculate_severity(
                rms_avg, self.config.imbalance_rms_threshold
            )
            
            return DefectSignature(
                defect_type=DefectType.IMBALANCE,
                confidence_score=round(min(confidence, 100), 1),
                severity_level=severity,
                detected_frequency=z_peak_freq if z_peak_freq > 0 else None,
                amplitude=rms_avg,
                threshold_exceeded=self.config.imbalance_rms_threshold,
                supporting_metrics={
                    "rms_z": z_rms,
                    "rms_x": x_rms,
                    "crest_factor": z_crest_factor,
                    "frequency": z_peak_freq
                },
                device_id=self.device_id
            )
        return None
    
    def _detect_misalignment(self, data: Dict[str, Any]) -> Optional[DefectSignature]:
        """
        Detect shaft/axle misalignment.
        
        Characteristics:
        - Elevated axial vibration (X-axis)
        - 1x and 2x frequency components
        - Higher axial than radial
        """
        z_rms = data.get("z_rms_mm", data.get("z_rms", 0))
        x_rms = data.get("x_rms_mm", data.get("x_rms", 0))
        z_peak_freq = data.get("z_peak_freq", 0)
        
        # Misalignment: axial (X) often higher or comparable to radial (Z)
        if z_rms > 0:
            axial_ratio = x_rms / z_rms
        else:
            axial_ratio = 0
        
        axial_ok = axial_ratio > 0.8  # Axial nearly as high as radial
        both_elevated = z_rms > 2.0 and x_rms > 2.0
        
        confidence = 0.0
        if axial_ok:
            confidence += 35 + min(20, (axial_ratio - 0.8) * 25)
        if both_elevated:
            confidence += 30
        if z_peak_freq > 20:  # Higher frequency component
            confidence += 20
        
        if confidence >= self.config.min_confidence:
            severity = self._calculate_severity(
                max(z_rms, x_rms), 4.0
            )
            
            return DefectSignature(
                defect_type=DefectType.MISALIGNMENT,
                confidence_score=round(min(confidence, 100), 1),
                severity_level=severity,
                amplitude=max(z_rms, x_rms),
                threshold_exceeded=4.0,
                supporting_metrics={
                    "rms_z": z_rms,
                    "rms_x": x_rms,
                    "axial_ratio": round(axial_ratio, 2),
                    "frequency": z_peak_freq
                },
                device_id=self.device_id
            )
        return None
    
    def _detect_looseness(self, data: Dict[str, Any]) -> Optional[DefectSignature]:
        """
        Detect mechanical looseness.
        
        Characteristics:
        - Non-linear vibration response
        - Sub-harmonic components (0.5x)
        - Random vibration patterns
        """
        z_rms = data.get("z_rms_mm", data.get("z_rms", 0))
        z_kurtosis = data.get("z_kurtosis", 0)
        z_crest_factor = data.get("z_crest_factor", 0)
        
        # Looseness often shows high variability
        confidence = 0.0
        
        if len(self._rms_history) >= 10:
            recent_rms = list(self._rms_history)[-10:]
            variation = np.std(recent_rms) / (np.mean(recent_rms) + 0.001)
            
            if variation > 0.3:  # High variability
                confidence += 40
            
            # Check for non-monotonic behavior
            diffs = np.diff(recent_rms)
            sign_changes = np.sum(diffs[:-1] * diffs[1:] < 0)
            if sign_changes > 3:  # Erratic behavior
                confidence += 25
        
        if z_kurtosis > 3.0:
            confidence += 20
        if z_crest_factor > 5:
            confidence += 15
        
        if confidence >= self.config.min_confidence:
            severity = self._calculate_severity(z_rms, 5.0)
            
            return DefectSignature(
                defect_type=DefectType.LOOSENESS,
                confidence_score=round(min(confidence, 100), 1),
                severity_level=severity,
                amplitude=z_rms,
                threshold_exceeded=5.0,
                supporting_metrics={
                    "rms": z_rms,
                    "kurtosis": z_kurtosis,
                    "crest_factor": z_crest_factor
                },
                device_id=self.device_id
            )
        return None
    
    def _calculate_periodicity(self, data: deque) -> float:
        """Calculate periodicity score (0-1) from data series"""
        if len(data) < 20:
            return 0.0
        
        arr = np.array(list(data))
        
        # Simple autocorrelation-based periodicity
        if np.std(arr) < 0.01:
            return 0.0
        
        # Normalize
        arr = (arr - np.mean(arr)) / (np.std(arr) + 0.001)
        
        # Autocorrelation
        autocorr = np.correlate(arr, arr, mode='full')
        autocorr = autocorr[len(autocorr)//2:]
        
        if len(autocorr) < 2:
            return 0.0
        
        # Find peaks in autocorrelation (excluding lag 0)
        autocorr = autocorr[1:min(len(autocorr), len(arr)//2)]
        if len(autocorr) == 0:
            return 0.0
        
        peak = np.max(autocorr)
        periodicity = peak / (autocorr[0] + 0.001) if len(autocorr) > 0 else 0
        
        return float(np.clip(periodicity, 0, 1))
    
    def _calculate_severity(self, *threshold_comparisons) -> int:
        """
        Calculate severity level (1-5) based on how much thresholds are exceeded.
        
        Args:
            *threshold_comparisons: Alternating (value, threshold) pairs
        
        Returns:
            Severity level 1-5
        """
        max_ratio = 0
        
        for i in range(0, len(threshold_comparisons), 2):
            if i + 1 < len(threshold_comparisons):
                value = threshold_comparisons[i]
                threshold = threshold_comparisons[i + 1]
                if threshold > 0:
                    ratio = value / threshold
                    max_ratio = max(max_ratio, ratio)
        
        if max_ratio < 1.0:
            return 1
        elif max_ratio < 1.5:
            return 2
        elif max_ratio < 2.0:
            return 3
        elif max_ratio < 3.0:
            return 4
        else:
            return 5
    
    def get_detection_stats(self) -> Dict[str, Any]:
        """Get detection statistics"""
        return {
            "detection_counts": {k.value: v for k, v in self._detection_count.items()},
            "last_detections": {
                k.value: v.isoformat() if v else None 
                for k, v in self._last_detection.items()
            },
            "history_samples": len(self._rms_history),
            "config": {
                "min_confidence": self.config.min_confidence,
                "wheel_flat_threshold": self.config.wheel_flat_threshold,
                "bearing_hf_threshold": self.config.bearing_hf_threshold,
                "imbalance_rms_threshold": self.config.imbalance_rms_threshold
            }
        }
    
    def reset_stats(self):
        """Reset detection statistics"""
        self._detection_count = {dt: 0 for dt in DefectType}
        self._last_detection = {}
        self._peak_history.clear()
        self._kurtosis_history.clear()
        self._hf_rms_history.clear()
        self._rms_history.clear()
        logger.info(f"[{self.device_id}] Detection stats reset")
