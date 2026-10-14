"""CI smoke contract for MuJoCo + DDS (OHH-124). Mock-tested until sport shim lands (OHH-123)."""

from ohho_go2.smoke.contract import (
    DEFAULT_MAX_LINEAR_M_S,
    SimDdsConfig,
    SmokeScenarios,
    clamp_linear_speed,
    refuse_hardware_connect,
    validate_sim_dds,
)
from ohho_go2.smoke.metrics import SmokeReport, write_report

__all__ = [
    "DEFAULT_MAX_LINEAR_M_S",
    "SimDdsConfig",
    "SmokeReport",
    "SmokeScenarios",
    "clamp_linear_speed",
    "refuse_hardware_connect",
    "validate_sim_dds",
    "write_report",
]
