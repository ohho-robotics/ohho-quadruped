"""Build a static Go2 URDF posed standing or lying.

Sim only, no gait controller. Leg joints are baked into fixed origins so
Gazebo Harmonic can show the mesh without holding torque.
"""

from __future__ import annotations

import argparse
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import NamedTuple

GROUND_CLEARANCE = 0.02

LEG_PREFIXES = ("FL", "FR", "RL", "RR")

# Radians, inside the vendored URDF limits. Hip 0 is no abduction.
POSE_ANGLES = {
    "standing": {"hip": 0.0, "thigh": 0.9, "calf": -1.8},
    "lying": {"hip": 0.0, "thigh": 1.4, "calf": -2.5},
}

# Model orientation passed to ros_gz_sim create. Lying is on the robot's side.
POSE_RPY = {
    "standing": (0.0, 0.0, 0.0),
    "lying": (math.pi / 2.0, 0.0, 0.0),
}


class SpawnSpec(NamedTuple):
    """URDF text plus the root pose for ros_gz_sim create."""

    urdf: str
    x: float
    y: float
    z: float
    roll: float
    pitch: float
    yaw: float


def build_spawn(
    urdf_text: str,
    pose: str,
    package_root: Path | None = None,
) -> SpawnSpec:
    """Return a static URDF and a grounded root pose for ``pose``."""
    if pose not in POSE_ANGLES:
        allowed = ", ".join(sorted(POSE_ANGLES))
        raise ValueError(f"pose must be one of: {allowed}")

    robot = ET.fromstring(urdf_text)
    if robot.tag != "robot":
        raise ValueError("URDF root element must be robot")

    _bake_leg_joints(robot, pose)
    _append_static_gazebo(robot)

    roll, pitch, yaw = POSE_RPY[pose]
    lowest = _rotated_sample_z(robot, roll, pitch, yaw)
    spawn_z = GROUND_CLEARANCE - lowest
    urdf = _serialize(robot)
    if package_root is not None:
        root = package_root.as_posix().rstrip("/")
        urdf = urdf.replace("package://go2_description/", f"{root}/")

    return SpawnSpec(
        urdf=urdf,
        x=0.0,
        y=0.0,
        z=spawn_z,
        roll=roll,
        pitch=pitch,
        yaw=yaw,
    )


def lowest_sample_z(
    urdf_text: str,
    roll: float,
    pitch: float,
    yaw: float,
    z: float,
) -> float:
    """Lowest sampled point after the spawn root pose, in world Z."""
    robot = ET.fromstring(urdf_text)
    return _rotated_sample_z(robot, roll, pitch, yaw) + z


def _bake_leg_joints(robot: ET.Element, pose: str) -> None:
    angles = _joint_angles(pose)
    found: set[str] = set()
    for joint in robot.findall("joint"):
        name = joint.get("name") or ""
        if name not in angles:
            continue
        if joint.get("type") != "revolute":
            raise ValueError(f"{name} is not revolute")
        _require_in_limits(joint, name, angles[name])
        xyz, rpy = _origin_values(joint)
        axis = _axis_values(joint)
        baked = _matrix_to_rpy(_mat_mul(_rpy_matrix(*rpy), _axis_matrix(axis, angles[name])))
        origin = joint.find("origin")
        if origin is None:
            origin = ET.SubElement(joint, "origin")
        origin.set("xyz", _fmt_vec(xyz))
        origin.set("rpy", _fmt_vec(baked))
        joint.set("type", "fixed")
        for tag in ("axis", "limit", "dynamics"):
            for child in list(joint.findall(tag)):
                joint.remove(child)
        found.add(name)
    missing = sorted(set(angles) - found)
    if missing:
        raise ValueError(f"URDF is missing leg joints: {', '.join(missing)}")


def _joint_angles(pose: str) -> dict[str, float]:
    angles: dict[str, float] = {}
    for prefix in LEG_PREFIXES:
        for part, angle in POSE_ANGLES[pose].items():
            angles[f"{prefix}_{part}_joint"] = angle
    return angles


def _require_in_limits(joint: ET.Element, name: str, angle: float) -> None:
    limit = joint.find("limit")
    if limit is None:
        return
    lower = float(limit.get("lower", "-inf"))
    upper = float(limit.get("upper", "inf"))
    if angle < lower - 1e-6 or angle > upper + 1e-6:
        raise ValueError(f"{name} angle {angle} is outside [{lower}, {upper}]")


def _append_static_gazebo(robot: ET.Element) -> None:
    gazebo = ET.SubElement(robot, "gazebo")
    static = ET.SubElement(gazebo, "static")
    static.text = "true"


def _origin_values(
    joint: ET.Element,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    origin = joint.find("origin")
    xyz = (0.0, 0.0, 0.0)
    rpy = (0.0, 0.0, 0.0)
    if origin is not None:
        if origin.get("xyz"):
            xyz = _parse_vec(origin.get("xyz", ""))
        if origin.get("rpy"):
            rpy = _parse_vec(origin.get("rpy", ""))
    return xyz, rpy


def _axis_values(joint: ET.Element) -> tuple[float, float, float]:
    axis = joint.find("axis")
    if axis is None or not axis.get("xyz"):
        raise ValueError(f"{joint.get('name')} has no axis")
    return _parse_vec(axis.get("xyz", ""))


def _parse_vec(text: str) -> tuple[float, float, float]:
    parts = [float(item) for item in text.split()]
    if len(parts) != 3:
        raise ValueError(f"expected 3 values, got {text!r}")
    return parts[0], parts[1], parts[2]


def _fmt_vec(values: tuple[float, float, float]) -> str:
    return " ".join(f"{value:.8f}" for value in values)


def _parent_map(
    robot: ET.Element,
) -> dict[str, tuple[str, tuple[float, float, float], tuple[float, float, float]]]:
    parents = {}
    for joint in robot.findall("joint"):
        parent_el = joint.find("parent")
        child_el = joint.find("child")
        if parent_el is None or child_el is None:
            continue
        parent = parent_el.get("link") or ""
        child = child_el.get("link") or ""
        xyz, rpy = _origin_values(joint)
        parents[child] = (parent, xyz, rpy)
    return parents


def _link_pose(
    parents: dict[str, tuple[str, tuple[float, float, float], tuple[float, float, float]]],
    link: str,
) -> tuple[tuple[tuple[float, float, float], ...], tuple[float, float, float]]:
    identity = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    if link == "base_link":
        return identity, (0.0, 0.0, 0.0)
    chain: list[tuple[tuple[float, float, float], tuple[float, float, float]]] = []
    current = link
    for _ in range(100):
        if current == "base_link":
            break
        if current not in parents:
            raise ValueError(f"link {link} is not connected to base_link")
        parent, xyz, rpy = parents[current]
        chain.append((xyz, rpy))
        current = parent
    else:
        raise ValueError(f"joint cycle while placing {link}")
    chain.reverse()
    rotation = identity
    translation = (0.0, 0.0, 0.0)
    for xyz, rpy in chain:
        local = _rpy_matrix(*rpy)
        translation = _add(translation, _mat_vec(rotation, xyz))
        rotation = _mat_mul(rotation, local)
    return rotation, translation


def _sample_points(robot: ET.Element) -> list[tuple[float, float, float]]:
    parents = _parent_map(robot)
    points: list[tuple[float, float, float]] = []
    for prefix in LEG_PREFIXES:
        _rotation, translation = _link_pose(parents, f"{prefix}_foot")
        points.append(translation)
    base_rotation, base_translation = _link_pose(parents, "base")
    for corner in _base_box_corners(robot):
        points.append(_add(base_translation, _mat_vec(base_rotation, corner)))
    if not points:
        raise ValueError("no sample points for the spawn height")
    return points


def _base_box_corners(robot: ET.Element) -> list[tuple[float, float, float]]:
    link = next((item for item in robot.findall("link") if item.get("name") == "base"), None)
    if link is None:
        return []
    box = link.find("collision/geometry/box")
    if box is None or not box.get("size"):
        return []
    sx, sy, sz = _parse_vec(box.get("size", ""))
    origin = link.find("collision/origin")
    center = (0.0, 0.0, 0.0)
    if origin is not None and origin.get("xyz"):
        center = _parse_vec(origin.get("xyz", ""))
    hx, hy, hz = sx / 2.0, sy / 2.0, sz / 2.0
    corners = []
    for x in (-hx, hx):
        for y in (-hy, hy):
            for z in (-hz, hz):
                corners.append(_add(center, (x, y, z)))
    return corners


def _rotated_sample_z(robot: ET.Element, roll: float, pitch: float, yaw: float) -> float:
    rotation = _rpy_matrix(roll, pitch, yaw)
    rotated = [_mat_vec(rotation, point)[2] for point in _sample_points(robot)]
    return min(rotated)


def _serialize(robot: ET.Element) -> str:
    body = ET.tostring(robot, encoding="unicode")
    return '<?xml version="1.0"?>\n' + body + "\n"


def _rpy_matrix(
    roll: float, pitch: float, yaw: float
) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
    """URDF fixed-axis RPY: R = Rz(yaw) Ry(pitch) Rx(roll)."""
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    return (
        (cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr),
        (sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr),
        (-sp, cp * sr, cp * cr),
    )


def _axis_matrix(
    axis: tuple[float, float, float], angle: float
) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
    norm = math.sqrt(axis[0] ** 2 + axis[1] ** 2 + axis[2] ** 2)
    if norm == 0.0:
        raise ValueError("joint axis has zero length")
    x, y, z = axis[0] / norm, axis[1] / norm, axis[2] / norm
    c, s = math.cos(angle), math.sin(angle)
    v = 1.0 - c
    return (
        (c + x * x * v, x * y * v - z * s, x * z * v + y * s),
        (y * x * v + z * s, c + y * y * v, y * z * v - x * s),
        (z * x * v - y * s, z * y * v + x * s, c + z * z * v),
    )


def _matrix_to_rpy(
    rotation: tuple[
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
    ],
) -> tuple[float, float, float]:
    pitch = math.asin(max(-1.0, min(1.0, -rotation[2][0])))
    if abs(rotation[0][0]) + abs(rotation[1][0]) > 1e-8:
        roll = math.atan2(rotation[2][1], rotation[2][2])
        yaw = math.atan2(rotation[1][0], rotation[0][0])
    else:
        roll = math.atan2(-rotation[0][1], rotation[1][1])
        yaw = 0.0
    return roll, pitch, yaw


def _mat_mul(
    left: tuple[tuple[float, float, float], ...],
    right: tuple[tuple[float, float, float], ...],
) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
    return tuple(
        tuple(sum(left[row][k] * right[k][col] for k in range(3)) for col in range(3))
        for row in range(3)
    )


def _mat_vec(
    rotation: tuple[tuple[float, float, float], ...],
    vector: tuple[float, float, float],
) -> tuple[float, float, float]:
    return tuple(sum(rotation[row][k] * vector[k] for k in range(3)) for row in range(3))


def _add(
    left: tuple[float, float, float], right: tuple[float, float, float]
) -> tuple[float, float, float]:
    return left[0] + right[0], left[1] + right[1], left[2] + right[2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write a static standing or lying Go2 URDF.")
    parser.add_argument("--pose", required=True, choices=sorted(POSE_ANGLES))
    parser.add_argument("--urdf", type=Path, required=True)
    parser.add_argument("--out", type=Path, help="Output path. Default is stdout.")
    parser.add_argument(
        "--package-root",
        type=Path,
        help="Rewrite package://go2_description/ to this directory.",
    )
    args = parser.parse_args(argv)
    spec = build_spawn(
        args.urdf.read_text(encoding="utf-8"),
        args.pose,
        package_root=args.package_root,
    )
    if args.out is None:
        sys.stdout.write(spec.urdf)
    else:
        args.out.write_text(spec.urdf, encoding="utf-8")
    print(
        f"spawn {args.pose} xyz {spec.x:.4f} {spec.y:.4f} {spec.z:.4f} "
        f"rpy {spec.roll:.4f} {spec.pitch:.4f} {spec.yaw:.4f}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
