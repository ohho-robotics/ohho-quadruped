"""Known poses for labelled OhhO scene objects (perception / nav fixtures)."""

from __future__ import annotations

from typing import TypedDict


class SceneObject(TypedDict):
    name: str
    kind: str
    pos: tuple[float, float, float]
    size: tuple[float, ...]


# Positions match named geoms in sim/scenes/*_env.xml (world frame, metres).
SCENE_OBJECTS: dict[str, list[SceneObject]] = {
    "flat": [
        {
            "name": "red_box",
            "kind": "box",
            "pos": (1.5, 0.0, 0.1),
            "size": (0.1, 0.1, 0.1),
        },
        {
            "name": "blue_cone",
            "kind": "cylinder",
            "pos": (1.5, 0.5, 0.05),
            "size": (0.05, 0.1),
        },
        {
            "name": "green_box",
            "kind": "box",
            "pos": (2.0, -0.5, 0.08),
            "size": (0.08, 0.08, 0.08),
        },
    ],
    "terrain": [
        {
            "name": "red_box",
            "kind": "box",
            "pos": (1.2, 0.3, 0.12),
            "size": (0.1, 0.1, 0.1),
        },
        {
            "name": "blue_cone",
            "kind": "cylinder",
            "pos": (1.8, -0.4, 0.06),
            "size": (0.05, 0.12),
        },
        {
            "name": "yellow_box",
            "kind": "box",
            "pos": (2.4, 0.2, 0.15),
            "size": (0.12, 0.12, 0.12),
        },
    ],
    "office": [
        {
            "name": "red_box",
            "kind": "box",
            "pos": (2.5, 0.0, 0.45),
            "size": (0.1, 0.1, 0.1),
        },
        {
            "name": "blue_cone",
            "kind": "cylinder",
            "pos": (2.2, 0.6, 0.43),
            "size": (0.05, 0.1),
        },
        {
            "name": "green_box",
            "kind": "box",
            "pos": (3.0, -0.4, 0.42),
            "size": (0.08, 0.08, 0.08),
        },
    ],
}
