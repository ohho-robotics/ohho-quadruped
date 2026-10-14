"""Pinned third-party revisions for the Unitree MuJoCo sim stack."""

# Keep in sync with scripts/dev/setup-unitree-wsl.sh
UNITREE_MUJOCO_REPO = "https://github.com/unitreerobotics/unitree_mujoco.git"
UNITREE_MUJOCO_REF = "1eb6642e3f3fdfb7fb13a9794fd6a2dd93ea0e7d"

FRONT_CAMERA_NAME = "ohho_front_camera"
# Approximate Go2 head / front depth-camera pose in base_link frame (metres, radians).
FRONT_CAMERA_POS = (0.29, 0.0, 0.08)
FRONT_CAMERA_QUAT = (0.7071068, 0.0, -0.7071068, 0.0)
FRONT_CAMERA_FOVY = 58.0

SCENE_CHOICES = ("flat", "terrain", "office")
