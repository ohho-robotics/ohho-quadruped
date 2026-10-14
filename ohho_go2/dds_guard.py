"""Fail-closed DDS domain / interface guard for sim-only sport shim."""

from __future__ import annotations

SIM_DDS_DOMAIN = 1
SIM_DDS_INTERFACE = "lo"


class SimDdsRefusalError(RuntimeError):
    """Raised when sport shim would use domain 0 or a non-loopback interface."""

    def __init__(self, domain: int, interface: str) -> None:
        self.domain = domain
        self.interface = interface
        super().__init__(
            "Sport shim refuses DDS domain "
            f"{domain} on interface '{interface}': "
            f"only domain {SIM_DDS_DOMAIN} and interface '{SIM_DDS_INTERFACE}' are allowed "
            "in sim (no hardware arming from non-TTY sessions)."
        )


def assert_sim_dds_only(domain: int, interface: str) -> None:
    """Refuse domain 0 or any interface other than loopback ``lo``."""
    iface = (interface or "").strip().lower()
    if domain != SIM_DDS_DOMAIN or iface != SIM_DDS_INTERFACE:
        raise SimDdsRefusalError(domain, interface)
