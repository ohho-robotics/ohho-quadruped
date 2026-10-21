"""Build OhhO Go2 MuJoCo scenes (robot + labelled props + front camera)."""

from __future__ import annotations

from pathlib import Path

import mujoco

from sim.pins import (
    FRONT_CAMERA_FOVY,
    FRONT_CAMERA_NAME,
    FRONT_CAMERA_POS,
    FRONT_CAMERA_QUAT,
    SCENE_CHOICES,
)
from sim.unitree_paths import go2_robot_dir, repo_root


def scene_env_fragment(scene: str) -> Path:
    if scene not in SCENE_CHOICES:
        raise ValueError(f"unknown scene {scene!r}, expected one of {SCENE_CHOICES}")
    path = repo_root() / "sim" / "scenes" / f"{scene}_env.xml"
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def compose_scene_xml(scene: str) -> str:
    env_body = scene_env_fragment(scene).read_text(encoding="utf-8")
    return (
        f'<mujoco model="ohho go2 {scene}">\n'
        f'  <include file="go2.xml"/>\n'
        f"{env_body}"
        f"</mujoco>\n"
    )


def write_scene_file(scene: str, go2_dir: Path) -> Path:
    # Must live next to go2.xml so <include file="go2.xml"/> resolves mesh assets.
    out = go2_dir / f"ohho_scene_{scene}.xml"
    out.write_text(compose_scene_xml(scene), encoding="utf-8")
    return out


def attach_front_camera(spec: mujoco.MjSpec) -> None:
    body = spec.body("base_link")
    cam = body.add_camera()
    cam.name = FRONT_CAMERA_NAME
    cam.pos = list(FRONT_CAMERA_POS)
    cam.quat = list(FRONT_CAMERA_QUAT)
    cam.fovy = FRONT_CAMERA_FOVY


def load_model_and_data(
    scene: str, unitree_mujoco_root: Path
) -> tuple[mujoco.MjModel, mujoco.MjData]:
    go2_dir = go2_robot_dir(unitree_mujoco_root)
    scene_path = write_scene_file(scene, go2_dir)
    spec = mujoco.MjSpec.from_file(str(scene_path))
    attach_front_camera(spec)
    model = spec.compile()
    data = mujoco.MjData(model)
    return model, data


def geom_names_in_scene(scene: str, unitree_mujoco_root: Path) -> set[str]:
    model, _ = load_model_and_data(scene, unitree_mujoco_root)
    names: set[str] = set()
    for gid in range(model.ngeom):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, gid)
        if name:
            names.add(name)
    return names
