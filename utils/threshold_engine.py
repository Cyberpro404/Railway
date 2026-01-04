"""
Deterministic threshold evaluation engine.

Evaluates static numeric limits against parameter values with full traceability.
No learning, no filtering, no adaptive logic.
"""

from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import json

from models.industrial_models import (
    ThresholdDefinition,
    ThresholdConfiguration,
    ParameterStatus,
    AuditEntry,
    QM30VT2_PARAMETER_REGISTRY,
)

logger = logging.getLogger(__name__)


@dataclass
class ThresholdEvaluationResult:
    """Result of evaluating a single parameter against its threshold."""
    parameter_name: str
    parameter_value: float
    parameter_unit: str
    threshold_enabled: bool
    threshold_status: ParameterStatus
    warning_limit: Optional[float] = None
    alarm_limit: Optional[float] = None
    exceeded_warning: bool = False
    exceeded_alarm: bool = False
    evaluation_timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class CycleEvaluationResult:
    """Result of evaluating all thresholds in a read cycle."""
    cycle_timestamp: str  # ISO8601, UTC
    total_parameters: int
    ok_count: int
    warning_count: int
    alarm_count: int
    error_count: int
    results: Dict[str, ThresholdEvaluationResult] = field(default_factory=dict)

    @property
    def overall_status(self) -> ParameterStatus:
        """Determine overall system status."""
        if self.alarm_count > 0:
            return ParameterStatus.ALARM
        elif self.warning_count > 0:
            return ParameterStatus.WARNING
        else:
            return ParameterStatus.OK


class DeterministicThresholdEngine:
    """
    Deterministic threshold evaluation engine.
    
    - Same input always produces same output
    - No state, no learning, no filtering
    - All evaluations logged with full traceability
    - Cycle-based (synchronous with sensor read cycle)
    """

    def __init__(self, threshold_config: ThresholdConfiguration):
        """Initialize engine with threshold configuration."""
        self.config = threshold_config
        self.evaluation_history: list[CycleEvaluationResult] = []
        self.logger = logger

    def evaluate_parameters(
        self,
        parameters: Dict[str, float]
    ) -> CycleEvaluationResult:
        """
        Evaluate all parameters against their thresholds.

        Args:
            parameters: Dict of {parameter_name: value}
                e.g., {"temperature_c": 25.3, "z_rms_mm_s": 1.5, ...}

        Returns:
            CycleEvaluationResult with detailed per-parameter results
        """
        cycle_ts = datetime.now(timezone.utc).isoformat()
        results: Dict[str, ThresholdEvaluationResult] = {}
        ok_count = 0
        warning_count = 0
        alarm_count = 0
        error_count = 0

        for param_name, param_value in parameters.items():
            try:
                result = self._evaluate_single_parameter(param_name, param_value)
                results[param_name] = result

                if result.threshold_status == ParameterStatus.ALARM:
                    alarm_count += 1
                elif result.threshold_status == ParameterStatus.WARNING:
                    warning_count += 1
                elif result.threshold_status == ParameterStatus.OK:
                    ok_count += 1
                else:
                    error_count += 1

                # Log threshold breaches for auditability
                if result.exceeded_alarm:
                    self.logger.warning(
                        f"ALARM: {param_name}={param_value} {result.parameter_unit} "
                        f"exceeded alarm limit {result.alarm_limit}"
                    )
                elif result.exceeded_warning:
                    self.logger.info(
                        f"WARNING: {param_name}={param_value} {result.parameter_unit} "
                        f"exceeded warning limit {result.warning_limit}"
                    )

            except Exception as e:
                self.logger.error(f"Error evaluating {param_name}: {e}")
                error_count += 1

        cycle_result = CycleEvaluationResult(
            cycle_timestamp=cycle_ts,
            total_parameters=len(parameters),
            ok_count=ok_count,
            warning_count=warning_count,
            alarm_count=alarm_count,
            error_count=error_count,
            results=results,
        )

        # Store in history for diagnostics
        self.evaluation_history.append(cycle_result)

        return cycle_result

    def _evaluate_single_parameter(
        self,
        param_name: str,
        param_value: float
    ) -> ThresholdEvaluationResult:
        """Evaluate a single parameter deterministically."""
        # Get parameter definition if available
        param_def = QM30VT2_PARAMETER_REGISTRY.get(param_name)
        unit = param_def.unit if param_def else "–"

        # Get threshold if configured
        threshold = self.config.thresholds.get(param_name)

        if not threshold or not threshold.enabled:
            return ThresholdEvaluationResult(
                parameter_name=param_name,
                parameter_value=param_value,
                parameter_unit=unit,
                threshold_enabled=False,
                threshold_status=ParameterStatus.OK,
            )

        # Deterministic evaluation
        exceeded_alarm = False
        exceeded_warning = False

        if threshold.alarm_limit is not None and param_value > threshold.alarm_limit:
            exceeded_alarm = True
            status = ParameterStatus.ALARM
        elif threshold.warning_limit is not None and param_value > threshold.warning_limit:
            exceeded_warning = True
            status = ParameterStatus.WARNING
        else:
            status = ParameterStatus.OK

        return ThresholdEvaluationResult(
            parameter_name=param_name,
            parameter_value=param_value,
            parameter_unit=unit,
            threshold_enabled=True,
            threshold_status=status,
            warning_limit=threshold.warning_limit,
            alarm_limit=threshold.alarm_limit,
            exceeded_warning=exceeded_warning,
            exceeded_alarm=exceeded_alarm,
        )

    def get_recent_evaluations(self, count: int = 10) -> list[CycleEvaluationResult]:
        """Get the most recent evaluation cycles."""
        return self.evaluation_history[-count:]

    def export_threshold_config(self) -> str:
        """Export threshold configuration as JSON."""
        config_dict = {
            "created_timestamp": self.config.created_timestamp,
            "last_modified": self.config.last_modified,
            "thresholds": {
                name: {
                    "warning_limit": t.warning_limit,
                    "alarm_limit": t.alarm_limit,
                    "enabled": t.enabled,
                    "description": t.description,
                }
                for name, t in self.config.thresholds.items()
            },
        }
        return json.dumps(config_dict, indent=2)

    def update_threshold(
        self,
        param_name: str,
        warning_limit: Optional[float] = None,
        alarm_limit: Optional[float] = None,
        description: str = "",
    ) -> Tuple[bool, str]:
        """
        Update a threshold with validation.

        Returns:
            (success, message)
        """
        # Validate parameter exists
        if param_name not in QM30VT2_PARAMETER_REGISTRY:
            return False, f"Unknown parameter: {param_name}"

        # Validate limits
        if warning_limit is not None and alarm_limit is not None:
            if warning_limit >= alarm_limit:
                return False, "Warning limit must be less than alarm limit"

        param_def = QM30VT2_PARAMETER_REGISTRY[param_name]
        if warning_limit is not None:
            if warning_limit < param_def.min_allowed or warning_limit > param_def.max_allowed:
                return False, f"Warning limit out of range [{param_def.min_allowed}, {param_def.max_allowed}]"

        if alarm_limit is not None:
            if alarm_limit < param_def.min_allowed or alarm_limit > param_def.max_allowed:
                return False, f"Alarm limit out of range [{param_def.min_allowed}, {param_def.max_allowed}]"

        # Update threshold
        threshold = ThresholdDefinition(
            parameter_name=param_name,
            warning_limit=warning_limit,
            alarm_limit=alarm_limit,
            enabled=True,
            description=description,
        )
        self.config.add_threshold(param_name, threshold)

        self.logger.info(f"Updated threshold for {param_name}: warning={warning_limit}, alarm={alarm_limit}")
        return True, f"Threshold updated for {param_name}"

    def reset_to_factory_defaults(self) -> None:
        """Reset all thresholds to factory defaults (no limits)."""
        self.config = ThresholdConfiguration()
        self.logger.warning("Thresholds reset to factory defaults")


class ThresholdPLCTagGenerator:
    """
    Generate PLC output tags based on threshold evaluation results.
    
    Maps threshold status to boolean and numeric tags for SCADA systems.
    """

    def __init__(self):
        """Initialize tag generator."""
        self.logger = logger

    def generate_plc_tags(
        self,
        cycle_result: CycleEvaluationResult
    ) -> Dict[str, any]:
        """
        Generate PLC tags from cycle evaluation results.

        Args:
            cycle_result: Result from DeterministicThresholdEngine

        Returns:
            Dict of {tag_name: value} for PLC output
                - Boolean tags: PARAM_NAME_AlarmActive, PARAM_NAME_WarningActive
                - Numeric tags: PARAM_NAME_Value, PARAM_NAME_Status (0=OK, 1=Warning, 2=Alarm)
        """
        tags = {
            "SystemOverallStatus": self._status_to_numeric(cycle_result.overall_status),
            "TotalAlarmParameters": cycle_result.alarm_count,
            "TotalWarningParameters": cycle_result.warning_count,
            "CycleTimestamp": cycle_result.cycle_timestamp,
        }

        for param_name, result in cycle_result.results.items():
            # Generate tag names (convert to SCADA-friendly format)
            tag_prefix = self._param_to_tag_prefix(param_name)

            # Value tag (raw parameter value)
            tags[f"{tag_prefix}_Value"] = result.parameter_value

            # Status numeric tag (0=OK, 1=Warning, 2=Alarm)
            tags[f"{tag_prefix}_Status"] = self._status_to_numeric(result.threshold_status)

            # Boolean tags
            tags[f"{tag_prefix}_AlarmActive"] = result.exceeded_alarm
            tags[f"{tag_prefix}_WarningActive"] = result.exceeded_warning

        return tags

    @staticmethod
    def _param_to_tag_prefix(param_name: str) -> str:
        """Convert parameter name to SCADA tag prefix."""
        # Example: "z_rms_mm_s" -> "Z_RMS_MMS"
        return param_name.upper().replace("_", "_")

    @staticmethod
    def _status_to_numeric(status: ParameterStatus) -> int:
        """Convert ParameterStatus to numeric value for PLC."""
        mapping = {
            ParameterStatus.OK: 0,
            ParameterStatus.WARNING: 1,
            ParameterStatus.ALARM: 2,
            ParameterStatus.TIMEOUT: 3,
            ParameterStatus.ERROR: 4,
        }
        return mapping.get(status, 4)


# =============================================================================
# FACTORY DEFAULTS
# =============================================================================

def create_default_threshold_config() -> ThresholdConfiguration:
    """
    Create a default threshold configuration.
    
    These are sensible defaults based on ISO 10816 for Class II machines.
    User may override any threshold.
    """
    config = ThresholdConfiguration()

    # Temperature limits
    config.add_threshold(
        "temperature_c",
        ThresholdDefinition(
            parameter_name="temperature_c",
            warning_limit=70.0,
            alarm_limit=80.0,
            enabled=True,
            description="Sensor temperature (ISO operating range)",
        ),
    )

    # Z-axis RMS velocity (ISO 10816 Class II, Zone A/B boundaries)
    config.add_threshold(
        "z_rms_mm_s",
        ThresholdDefinition(
            parameter_name="z_rms_mm_s",
            warning_limit=2.3,  # ISO Zone A/B boundary
            alarm_limit=7.1,  # ISO Zone B/C boundary
            enabled=True,
            description="Z-axis RMS velocity (ISO 10816-3 Class II)",
        ),
    )

    # X-axis RMS velocity
    config.add_threshold(
        "x_rms_mm_s",
        ThresholdDefinition(
            parameter_name="x_rms_mm_s",
            warning_limit=2.3,
            alarm_limit=7.1,
            enabled=True,
            description="X-axis RMS velocity (ISO 10816-3 Class II)",
        ),
    )

    # Kurtosis (bearing fault indicator)
    config.add_threshold(
        "z_kurtosis",
        ThresholdDefinition(
            parameter_name="z_kurtosis",
            warning_limit=4.0,  # Normal is ~3, elevated = potential bearing issues
            alarm_limit=6.0,
            enabled=False,
            description="Z-axis kurtosis (bearing impact indicator)",
        ),
    )

    config.add_threshold(
        "x_kurtosis",
        ThresholdDefinition(
            parameter_name="x_kurtosis",
            warning_limit=4.0,
            alarm_limit=6.0,
            enabled=False,
            description="X-axis kurtosis (bearing impact indicator)",
        ),
    )

    return config
