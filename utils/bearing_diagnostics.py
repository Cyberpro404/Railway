"""
Bearing Diagnostics Module

Implements advanced bearing fault detection algorithms using:
- Crest Factor Analysis (impact detection)
- Kurtosis Analysis (early bearing fault detection)
- High-Frequency RMS Trending (lubrication and early defect detection)

These algorithms detect bearing faults before they become critical failures.
"""

from typing import Dict, Optional, Literal
from dataclasses import dataclass
import time


Severity = Literal["normal", "acceptable", "warning", "critical"]


@dataclass
class BearingHealthStatus:
    """Bearing health status result."""
    status: Severity
    alert: bool
    message: str
    details: Dict[str, any]


class CrestFactorAnalyzer:
    """
    Crest Factor (CF) = Peak Amplitude / RMS Amplitude
    
    Normal bearing: CF = 2.5 to 4.0
    Rising CF (>5.0): Early bearing wear - spalling initiation
    High CF (>8.0): Advanced bearing defect - localized faults
    
    Crest factor increases when impulsive events (impacts from bearing defects)
    occur against a background of relatively steady vibration.
    """
    
    # Thresholds
    NORMAL_MAX = 4.0
    WARNING_MIN = 5.0
    CRITICAL_MIN = 8.0
    
    @classmethod
    def analyze(cls, cf_z: float, cf_x: float) -> BearingHealthStatus:
        """
        Analyze crest factor for both axes.
        
        Args:
            cf_z: Z-axis crest factor
            cf_x: X-axis crest factor
        
        Returns:
            BearingHealthStatus with diagnosis
        """
        # Determine worst-case severity
        max_cf = max(cf_z, cf_x)
        
        if max_cf >= cls.CRITICAL_MIN:
            severity = "critical"
            alert = True
            message = "CRITICAL: High crest factor - inspect bearing immediately"
        elif max_cf >= cls.WARNING_MIN:
            severity = "warning"
            alert = True
            message = "WARNING: Elevated crest factor - early bearing wear suspected"
        elif max_cf <= cls.NORMAL_MAX:
            severity = "normal"
            alert = False
            message = "Crest factor within normal range"
        else:
            severity = "acceptable"
            alert = False
            message = "Crest factor slightly elevated but acceptable"
        
        # Per-axis classification
        def classify_axis(cf: float) -> str:
            if cf >= cls.CRITICAL_MIN:
                return "critical"
            elif cf >= cls.WARNING_MIN:
                return "warning"
            elif cf <= cls.NORMAL_MAX:
                return "normal"
            else:
                return "acceptable"
        
        return BearingHealthStatus(
            status=severity,
            alert=alert,
            message=message,
            details={
                "z_axis_cf": cf_z,
                "x_axis_cf": cf_x,
                "z_axis_status": classify_axis(cf_z),
                "x_axis_status": classify_axis(cf_x),
                "normal_range": [2.5, cls.NORMAL_MAX],
                "warning_threshold": cls.WARNING_MIN,
                "critical_threshold": cls.CRITICAL_MIN
            }
        )


class KurtosisAnalyzer:
    """
    Kurtosis measures "peakedness" or impulsiveness of vibration signal.
    
    Normal (Gaussian): 2.8 to 3.2
    Low (<2.0): Rounded/worn surfaces, uniform wear
    High (>4.0): Impulsive events - bearing spalls, cracks
    Very High (>8.0): Severe localized defect
    
    Kurtosis is sensitive to early bearing defects before they show up
    in traditional velocity/acceleration spectra.
    """
    
    # Thresholds
    NORMAL_MIN = 2.8
    NORMAL_MAX = 3.2
    WARNING_MIN = 4.0
    CRITICAL_MIN = 8.0
    LOW_THRESHOLD = 2.0
    
    @classmethod
    def analyze(cls, kurt_z: float, kurt_x: float) -> BearingHealthStatus:
        """
        Analyze kurtosis for both axes.
        
        Args:
            kurt_z: Z-axis kurtosis
            kurt_x: X-axis kurtosis
        
        Returns:
            BearingHealthStatus with diagnosis
        """
        # Determine worst-case severity
        max_kurt = max(kurt_z, kurt_x)
        min_kurt = min(kurt_z, kurt_x)
        
        if max_kurt >= cls.CRITICAL_MIN:
            severity = "critical"
            alert = True
            message = "CRITICAL: Extremely high kurtosis - severe bearing defect"
        elif max_kurt >= cls.WARNING_MIN:
            severity = "warning"
            alert = True
            message = "WARNING: Elevated kurtosis - inspect for bearing faults"
        elif min_kurt < cls.LOW_THRESHOLD:
            severity = "warning"
            alert = True
            message = "WARNING: Low kurtosis - possible uniform bearing wear"
        elif cls.NORMAL_MIN <= kurt_z <= cls.NORMAL_MAX and cls.NORMAL_MIN <= kurt_x <= cls.NORMAL_MAX:
            severity = "normal"
            alert = False
            message = "Kurtosis within normal Gaussian distribution"
        else:
            severity = "acceptable"
            alert = False
            message = "Kurtosis outside ideal range but acceptable"
        
        # Per-axis classification
        def classify_axis(k: float) -> str:
            if k >= cls.CRITICAL_MIN:
                return "critical"
            elif k >= cls.WARNING_MIN:
                return "warning"
            elif k < cls.LOW_THRESHOLD:
                return "low_wear"
            elif cls.NORMAL_MIN <= k <= cls.NORMAL_MAX:
                return "normal"
            else:
                return "acceptable"
        
        return BearingHealthStatus(
            status=severity,
            alert=alert,
            message=message,
            details={
                "z_axis_kurtosis": kurt_z,
                "x_axis_kurtosis": kurt_x,
                "z_axis_status": classify_axis(kurt_z),
                "x_axis_status": classify_axis(kurt_x),
                "normal_range": [cls.NORMAL_MIN, cls.NORMAL_MAX],
                "warning_threshold": cls.WARNING_MIN,
                "critical_threshold": cls.CRITICAL_MIN
            }
        )


class HFRMSTrendAnalyzer:
    """
    High-Frequency RMS (1-4 kHz) Trend Analysis
    
    HF RMS detects early bearing defects before they appear in velocity spectrum.
    Lubrication issues and micro-cracks generate high-frequency energy.
    
    Requires baseline establishment during healthy operation.
    """
    
    # Trend thresholds (percentage increase from baseline)
    WARNING_INCREASE = 50.0   # 50% increase
    CRITICAL_INCREASE = 100.0  # 100% increase (doubled)
    
    def __init__(self):
        """Initialize with no baseline."""
        self.baseline: Optional[Dict[str, float]] = None
        self.baseline_timestamp: Optional[float] = None
    
    def set_baseline(self, hf_z: float, hf_x: float):
        """
        Set baseline HF RMS values.
        
        Args:
            hf_z: Z-axis HF RMS (g)
            hf_x: X-axis HF RMS (g)
        """
        self.baseline = {
            "hf_z": hf_z,
            "hf_x": hf_x
        }
        self.baseline_timestamp = time.time()
    
    def analyze(self, hf_z: float, hf_x: float) -> BearingHealthStatus:
        """
        Analyze HF RMS trend against baseline.
        
        Args:
            hf_z: Current Z-axis HF RMS (g)
            hf_x: Current X-axis HF RMS (g)
        
        Returns:
            BearingHealthStatus with trend analysis
        """
        if self.baseline is None:
            # No baseline - set current as baseline
            self.set_baseline(hf_z, hf_x)
            return BearingHealthStatus(
                status="normal",
                alert=False,
                message="HF RMS baseline established",
                details={
                    "baseline_set": True,
                    "hf_z": hf_z,
                    "hf_x": hf_x
                }
            )
        
        # Calculate percentage increase
        z_increase = ((hf_z - self.baseline["hf_z"]) / self.baseline["hf_z"]) * 100 if self.baseline["hf_z"] > 0 else 0
        x_increase = ((hf_x - self.baseline["hf_x"]) / self.baseline["hf_x"]) * 100 if self.baseline["hf_x"] > 0 else 0
        
        max_increase = max(z_increase, x_increase)
        
        if max_increase >= self.CRITICAL_INCREASE:
            severity = "critical"
            alert = True
            message = f"CRITICAL: HF RMS doubled - Z={z_increase:.1f}%, X={x_increase:.1f}%"
        elif max_increase >= self.WARNING_INCREASE:
            severity = "warning"
            alert = True
            message = f"WARNING: HF RMS increase - Z={z_increase:.1f}%, X={x_increase:.1f}%"
        elif max_increase < -self.WARNING_INCREASE:
            severity = "acceptable"
            alert = False
            message = f"NOTE: HF RMS decreased significantly (may indicate sensor issue)"
        else:
            severity = "normal"
            alert = False
            message = "HF RMS stable within normal variation"
        
        return BearingHealthStatus(
            status=severity,
            alert=alert,
            message=message,
            details={
                "z_axis_hf": hf_z,
                "x_axis_hf": hf_x,
                "z_baseline": self.baseline["hf_z"],
                "x_baseline": self.baseline["hf_x"],
                "z_increase_pct": z_increase,
                "x_increase_pct": x_increase,
                "baseline_age_hours": (time.time() - self.baseline_timestamp) / 3600 if self.baseline_timestamp else 0
            }
        )


class BearingDiagnosticsSuite:
    """
    Complete bearing diagnostics suite combining all analysis methods.
    """
    
    def __init__(self):
        """Initialize diagnostics suite."""
        self.hf_trend_analyzer = HFRMSTrendAnalyzer()
    
    def analyze_full(
        self,
        cf_z: float,
        cf_x: float,
        kurt_z: float,
        kurt_x: float,
        hf_z: Optional[float] = None,
        hf_x: Optional[float] = None
    ) -> Dict[str, any]:
        """
        Perform complete bearing diagnostics analysis.
        
        Args:
            cf_z: Z-axis crest factor
            cf_x: X-axis crest factor
            kurt_z: Z-axis kurtosis
            kurt_x: X-axis kurtosis
            hf_z: Z-axis HF RMS (optional)
            hf_x: X-axis HF RMS (optional)
        
        Returns:
            Complete diagnostic report
        """
        # Crest factor analysis
        cf_result = CrestFactorAnalyzer.analyze(cf_z, cf_x)
        
        # Kurtosis analysis
        kurt_result = KurtosisAnalyzer.analyze(kurt_z, kurt_x)
        
        # HF trend analysis (if available)
        hf_result = None
        if hf_z is not None and hf_x is not None:
            hf_result = self.hf_trend_analyzer.analyze(hf_z, hf_x)
        
        # Determine overall status (worst-case)
        statuses = [cf_result.status, kurt_result.status]
        if hf_result:
            statuses.append(hf_result.status)
        
        # Priority: critical > warning > acceptable > normal
        if "critical" in statuses:
            overall_status = "critical"
        elif "warning" in statuses:
            overall_status = "warning"
        elif "acceptable" in statuses:
            overall_status = "acceptable"
        else:
            overall_status = "normal"
        
        # Aggregate alerts
        alerts = []
        if cf_result.alert:
            alerts.append(cf_result.message)
        if kurt_result.alert:
            alerts.append(kurt_result.message)
        if hf_result and hf_result.alert:
            alerts.append(hf_result.message)
        
        return {
            "overall_status": overall_status,
            "alerts": alerts,
            "alert_count": len(alerts),
            "crest_factor": {
                "status": cf_result.status,
                "alert": cf_result.alert,
                "message": cf_result.message,
                "details": cf_result.details
            },
            "kurtosis": {
                "status": kurt_result.status,
                "alert": kurt_result.alert,
                "message": kurt_result.message,
                "details": kurt_result.details
            },
            "hf_trend": {
                "status": hf_result.status if hf_result else "not_available",
                "alert": hf_result.alert if hf_result else False,
                "message": hf_result.message if hf_result else "HF RMS data not available",
                "details": hf_result.details if hf_result else {}
            } if hf_result else None
        }
