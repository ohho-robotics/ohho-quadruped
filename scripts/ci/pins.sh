# Pinned third-party refs for Unitree sim CI (keep in sync with scripts/dev/setup-unitree-wsl.sh).
CYCLONEDDS_REPO="https://github.com/eclipse-cyclonedds/cyclonedds.git"
CYCLONEDDS_REF="9995905bce6c4cf9f740d6438bbf7fcfd1c83dfd"
CYCLONEDDS_PY_VERSION="0.10.2"
SDK2PY_REPO="https://github.com/unitreerobotics/unitree_sdk2_python.git"
SDK2PY_REF="814556d15970dd2ecf1c9984e845ca02ab07e206"
MUJOCO_SIM_REPO="https://github.com/unitreerobotics/unitree_mujoco.git"
MUJOCO_SIM_REF="1eb6642e3f3fdfb7fb13a9794fd6a2dd93ea0e7d"
OHHO_SDK_REPO="https://github.com/ohho-robotics/ohho-sdk.git"
# main as of 2026-10-14. f4a83fa is not in ohho-sdk (checkout exits 128).
# This tree has no Python [unitree] extra; install scripts warn and continue.
OHHO_SDK_REF="493378937fe4eb60ae24dedcb62124288c246d04"
MUJOCO_PY_VERSION="${MUJOCO_PY_VERSION:-3.3.7}"
PYGAME_VERSION="${PYGAME_VERSION:-2.6.1}"
