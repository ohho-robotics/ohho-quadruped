"""Run unitree_mujoco physics + DDS bridge for OhhO Go2 scenes."""

from __future__ import annotations

import os
import sys
import threading
import time
import types
from pathlib import Path
from threading import Thread

import mujoco

from sim.dds_guard import validate_dds_endpoint
from sim.mjcf import load_model_and_data
from sim.pins import FRONT_CAMERA_NAME
from sim.unitree_paths import (
    assert_pinned_ref,
    go2_robot_dir,
    resolve_unitree_mujoco_root,
    simulate_python_dir,
)


def configure_headless_gl() -> None:
    if "MUJOCO_GL" not in os.environ:
        os.environ["MUJOCO_GL"] = "egl"


def install_unitree_config(
    *,
    robot_scene: str,
    domain_id: int,
    interface: str,
    use_joystick: bool,
) -> None:
    cfg = types.ModuleType("config")
    cfg.ROBOT = "go2"
    cfg.ROBOT_SCENE = robot_scene
    cfg.DOMAIN_ID = domain_id
    cfg.INTERFACE = interface
    cfg.USE_JOYSTICK = 1 if use_joystick else 0
    cfg.JOYSTICK_TYPE = "xbox"
    cfg.JOYSTICK_DEVICE = 0
    cfg.PRINT_SCENE_INFORMATION = False
    cfg.ENABLE_ELASTIC_BAND = False
    cfg.SIMULATE_DT = 0.005
    cfg.VIEWER_DT = 0.02
    sys.modules["config"] = cfg


def _import_unitree_bridge(sim_py_dir: Path):
    path_str = str(sim_py_dir)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
    from unitree_sdk2py_bridge import UnitreeSdk2Bridge  # noqa: WPS433

    return UnitreeSdk2Bridge


def run_simulation(
    *,
    scene: str,
    headless: bool,
    domain_id: int,
    interface: str,
    use_joystick: bool,
    render_front_camera: bool,
    duration_s: float | None,
) -> None:
    validate_dds_endpoint(domain_id, interface)
    unitree_root = resolve_unitree_mujoco_root()
    assert_pinned_ref(unitree_root)
    sim_py = simulate_python_dir(unitree_root)
    if not sim_py.is_dir():
        raise FileNotFoundError(f"missing simulate_python at {sim_py}")

    model, data = load_model_and_data(scene, unitree_root)
    scene_path = go2_robot_dir(unitree_root) / f"ohho_scene_{scene}.xml"
    install_unitree_config(
        robot_scene=str(scene_path),
        domain_id=domain_id,
        interface=interface,
        use_joystick=use_joystick,
    )

    if headless:
        configure_headless_gl()
        _run_headless(
            model,
            data,
            sim_py,
            use_joystick=use_joystick,
            render_front_camera=render_front_camera,
            duration_s=duration_s,
            domain_id=domain_id,
            interface=interface,
        )
    else:
        _run_with_viewer(
            model,
            data,
            sim_py,
            use_joystick=use_joystick,
            duration_s=duration_s,
            domain_id=domain_id,
            interface=interface,
        )


def _run_headless(
    mj_model: mujoco.MjModel,
    mj_data: mujoco.MjData,
    sim_py: Path,
    *,
    use_joystick: bool,
    render_front_camera: bool,
    duration_s: float | None,
    domain_id: int,
    interface: str,
) -> None:
    from unitree_sdk2py.core.channel import ChannelFactoryInitialize

    UnitreeSdk2Bridge = _import_unitree_bridge(sim_py)
    locker = threading.Lock()
    renderer = None
    if render_front_camera:
        renderer = mujoco.Renderer(mj_model, height=480, width=640)

    stop = threading.Event()

    def sim_loop() -> None:
        ChannelFactoryInitialize(domain_id, interface)
        unitree = UnitreeSdk2Bridge(mj_model, mj_data)
        if use_joystick:
            unitree.SetupJoystick(device_id=0, js_type="xbox")
        deadline = None
        if duration_s is not None:
            deadline = time.perf_counter() + duration_s
        while not stop.is_set():
            if deadline is not None and time.perf_counter() >= deadline:
                stop.set()
                break
            step_start = time.perf_counter()
            locker.acquire()
            mujoco.mj_step(mj_model, mj_data)
            if renderer is not None:
                renderer.update_scene(mj_data, camera=FRONT_CAMERA_NAME)
            locker.release()
            dt = mj_model.opt.timestep - (time.perf_counter() - step_start)
            if dt > 0:
                time.sleep(dt)

    thread = Thread(target=sim_loop, name="ohho-sim", daemon=True)
    thread.start()
    try:
        while thread.is_alive() and not stop.is_set():
            thread.join(timeout=0.2)
    except KeyboardInterrupt:
        stop.set()
        thread.join(timeout=2.0)


def _run_with_viewer(
    mj_model: mujoco.MjModel,
    mj_data: mujoco.MjData,
    sim_py: Path,
    *,
    use_joystick: bool,
    duration_s: float | None,
    domain_id: int,
    interface: str,
) -> None:
    import mujoco.viewer
    from unitree_sdk2py.core.channel import ChannelFactoryInitialize

    UnitreeSdk2Bridge = _import_unitree_bridge(sim_py)
    locker = threading.Lock()
    viewer = mujoco.viewer.launch_passive(mj_model, mj_data)
    mj_model.opt.timestep = 0.005
    stop = threading.Event()

    def sim_loop() -> None:
        ChannelFactoryInitialize(domain_id, interface)
        unitree = UnitreeSdk2Bridge(mj_model, mj_data)
        if use_joystick:
            unitree.SetupJoystick(device_id=0, js_type="xbox")
        deadline = None
        if duration_s is not None:
            deadline = time.perf_counter() + duration_s
        while viewer.is_running() and not stop.is_set():
            if deadline is not None and time.perf_counter() >= deadline:
                stop.set()
                viewer.close()
                break
            step_start = time.perf_counter()
            locker.acquire()
            mujoco.mj_step(mj_model, mj_data)
            locker.release()
            dt = mj_model.opt.timestep - (time.perf_counter() - step_start)
            if dt > 0:
                time.sleep(dt)

    def viewer_loop() -> None:
        while viewer.is_running() and not stop.is_set():
            locker.acquire()
            viewer.sync()
            locker.release()
            time.sleep(0.02)

    sim_thread = Thread(target=sim_loop, name="ohho-sim", daemon=True)
    view_thread = Thread(target=viewer_loop, name="ohho-viewer", daemon=True)
    sim_thread.start()
    view_thread.start()
    try:
        while viewer.is_running() and sim_thread.is_alive():
            sim_thread.join(timeout=0.2)
    except KeyboardInterrupt:
        stop.set()
        viewer.close()
    sim_thread.join(timeout=2.0)
    view_thread.join(timeout=2.0)
