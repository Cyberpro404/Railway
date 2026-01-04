"""
ISO 10816 Vibration Severity Classification Module

Implements ISO 10816-1 vibration severity zones for rotating machinery.
This standard classifies vibration levels into zones (A-D) based on RMS velocity.
"""

from typing import Literal, Dict
from dataclasses import dataclass


MachineClass = Literal["class_I", "class_II", "class_III", "class_IV"]
VibrationZone = Literal["good", "satisfactory", "unsatisfactory", "unacceptable"]


@dataclass
class ISO10816Limits:
    """Vibration limits for a specific machine class (mm/s RMS)."""
    zone_a_max: float  # Good
    zone_b_max: float  # Satisfactory
    zone_c_max: float  # Unsatisfactory
    # Zone D (Unacceptable) is everything above zone_c_max


# ISO 10816-1 vibration limits (mm/s RMS)
MACHINE_LIMITS: Dict[MachineClass, ISO10816Limits] = {
    # Class I: Small machines (<15 kW)
    "class_I": ISO10816Limits(
        zone_a_max=0.71,
        zone_b_max=1.8,
        zone_c_max=4.5
    ),
    
    # Class II: Medium machines (15-75 kW) on rigid foundations
    "class_II": ISO10816Limits(
        zone_a_max=1.12,
        zone_b_max=2.8,
        zone_c_max=7.1
    ),
    
    # Class III: Large machines (>75 kW) on rigid foundations
    "class_III": ISO10816Limits(
        zone_a_max=1.8,
        zone_b_max=4.5,
        zone_c_max=11.2
    ),
    
    # Class IV: Large machines (>75 kW) on flexible foundations
    "class_IV": ISO10816Limits(
        zone_a_max=2.8,
        zone_b_max=7.1,
        zone_c_max=18.0
    ),
}


class ISO10816Classifier:
    """
    ISO 10816 vibration severity classifier.
    
    Usage:
        classifier = ISO10816Classifier(machine_class="class_II")
        zone = classifier.classify(rms_velocity_mm_s=2.5)
        # Returns: "satisfactory"
    """
    
    def __init__(self, machine_class: MachineClass = "class_II"):
        """
        Initialize classifier with machine class.
        
        Args:
            machine_class: Machine classification (class_I to class_IV)
        """
        if machine_class not in MACHINE_LIMITS:
            raise ValueError(
                f"Invalid machine class: {machine_class}. "
                f"Must be one of: {list(MACHINE_LIMITS.keys())}"
            )
        self.machine_class = machine_class
        self.limits = MACHINE_LIMITS[machine_class]
    
    def classify(self, rms_mm_s: float) -> VibrationZone:
        """
        Classify vibration severity based on RMS velocity.
        
        Args:
            rms_mm_s: RMS velocity in mm/s
        
        Returns:
            Vibration zone: "good", "satisfactory", "unsatisfactory", "unacceptable"
        
        Zone Descriptions:
            - Zone A (Good): Newly commissioned machinery
            - Zone B (Satisfactory): Unrestricted long-term operation
            - Zone C (Unsatisfactory): Limited operation, corrective action needed
            - Zone D (Unacceptable): Damage severity - stop immediately
        """
        if rms_mm_s < 0:
            raise ValueError(f"RMS velocity cannot be negative: {rms_mm_s}")
        
        if rms_mm_s < self.limits.zone_a_max:
            return "good"
        elif rms_mm_s < self.limits.zone_b_max:
            return "satisfactory"
        elif rms_mm_s < self.limits.zone_c_max:
            return "unsatisfactory"
        else:
            return "unacceptable"
    
    def get_limits(self) -> Dict[str, float]:
        """
        Get vibration limits for current machine class.
        
        Returns:
            Dictionary with zone boundaries (mm/s)
        """
        return {
            "zone_a_max": self.limits.zone_a_max,
            "zone_b_max": self.limits.zone_b_max,
            "zone_c_max": self.limits.zone_c_max,
            "machine_class": self.machine_class
        }
    
    def classify_with_details(self, rms_mm_s: float) -> Dict[str, any]:
        """
        Classify vibration with detailed information.
        
        Args:
            rms_mm_s: RMS velocity in mm/s
        
        Returns:
            Dictionary with zone, severity, and recommendations
        """
        zone = self.classify(rms_mm_s)
        
        severity_map = {
            "good": "normal",
            "satisfactory": "acceptable",
            "unsatisfactory": "warning",
            "unacceptable": "critical"
        }
        
        recommendation_map = {
            "good": "Normal operation - continue monitoring",
            "satisfactory": "Acceptable for unrestricted operation",
            "unsatisfactory": "Schedule corrective maintenance",
            "unacceptable": "URGENT: Immediate inspection required - potential damage"
        }
        
        return {
            "zone": zone,
            "iso10816_zone": zone.upper()[0],  # A, B, C, or D
            "severity": severity_map[zone],
            "rms_mm_s": rms_mm_s,
            "recommendation": recommendation_map[zone],
            "machine_class": self.machine_class,
            "limits": self.get_limits()
        }


def quick_classify(rms_mm_s: float, machine_class: MachineClass = "class_II") -> VibrationZone:
    """
    Quick classification without creating classifier instance.
    
    Args:
        rms_mm_s: RMS velocity in mm/s
        machine_class: Machine classification (default: class_II)
    
    Returns:
        Vibration zone
    """
    classifier = ISO10816Classifier(machine_class)
    return classifier.classify(rms_mm_s)
