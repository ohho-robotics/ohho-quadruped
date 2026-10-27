"""
Velocity locomotion policy scaffolding (OHH-122).

Planned sport-shim inference will load exported ONNX here; not wired yet.
"""

from ohho_go2.policy.spec import VelocityPolicySpec, load_spec_from_config

__all__ = ["VelocityPolicySpec", "load_spec_from_config"]
