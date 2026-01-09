"""
ISO10816 Severity Calculator
Classifies vibration severity according to ISO 10816 standard
"""
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class ISOCalculator:
    """ISO10816 vibration severity calculator"""
    
    # ISO10816 Class II thresholds (mm/s RMS) for general machinery
    # Class II: Medium-sized machines (15-75 kW), rigid mounting
    THRESHOLDS = {
        "class_ii": {
            "good": 0.71,      # < 0.71 mm/s - Good condition
            "satisfactory": 1.8,  # 0.71 - 1.8 mm/s - Satisfactory
            "unsatisfactory": 4.5,  # 1.8 - 4.5 mm/s - Unsatisfactory
            "unacceptable": float('inf')  # > 4.5 mm/s - Unacceptable
        }
    }
    
    def __init__(self, iso_class: str = "class_ii"):
        self.iso_class = iso_class
        self.thresholds = self.THRESHOLDS.get(iso_class, self.THRESHOLDS["class_ii"])
    
    def calculate_severity(self, rms_velocity: float) -> Dict[str, any]:
        """
        Calculate ISO10816 severity classification
        
        Args:
            rms_velocity: RMS velocity in mm/s
            
        Returns:
            Dict with severity level, class, color, and description
        """
        if rms_velocity < self.thresholds["good"]:
            level = "good"
            class_name = "Class I"
            color = "green"
            description = "Good - Normal operation"
        elif rms_velocity < self.thresholds["satisfactory"]:
            level = "satisfactory"
            class_name = "Class II"
            color = "green"
            description = "Satisfactory - Acceptable for long-term operation"
        elif rms_velocity < self.thresholds["unsatisfactory"]:
            level = "unsatisfactory"
            class_name = "Class III"
            color = "yellow"
            description = "Unsatisfactory - Condition monitoring required"
        else:
            level = "unacceptable"
            class_name = "Class IV"
            color = "red"
            description = "Unacceptable - Immediate attention required"
        
        return {
            "level": level,
            "class": class_name,
            "color": color,
            "description": description,
            "rms_velocity": rms_velocity,
            "iso_class": self.iso_class
        }
    
    def get_color_code(self, rms_velocity: float) -> str:
        """Get color code for severity"""
        severity = self.calculate_severity(rms_velocity)
        return severity["color"]

