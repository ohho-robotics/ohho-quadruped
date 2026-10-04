# Dev setup: Unitree Go2 simulation on Windows (WSL2 Ubuntu 22.04)

Tracking issue: OHH-114.

Unitree's software stack (CycloneDDS 0.10.2, `unitree_sdk2_python`, `unitree_mujoco`,
`unitree_ros2`) is built for Ubuntu. On a Windows PC, the supported dev environment
for this repo is a WSL2 distro running Ubuntu 22.04. This page covers the
**simulation phase only**. Nothing here has been run against a physical robot.

What you end up with:

| Component | Version / pin | Where |
|---|---|---|
| Ubuntu | 22.04 LTS (WSL2) | `wsl -d Ubuntu-22.04` |
| CycloneDDS C library | tag `0.10.2` (`9995905`), built from source | `$UNITREE_WS/cyclonedds/install` (`CYCLONEDDS_HOME`) |
| `cyclonedds` Python binding | `0.10.2`, built against `CYCLONEDDS_HOME` | `$UNITREE_WS/venv` |
| `unitree_sdk2_python` | commit `814556d`, editable install | `$UNITREE_WS/unitree_sdk2_python` |
| `mujoco` / `pygame` | `3.3.7` / `2.6.1` | `$UNITREE_WS/venv` |
| `unitree_mujoco` | commit `1eb6642` | `$UNITREE_WS/unitree_mujoco` |
| `ohho-sdk[unitree]` (`ohho-os`) | commit `f4a83fa`, editable install | `$UNITREE_WS/ohho-sdk` |

`UNITREE_WS` defaults to `~/unitree`. The pins live at the top of
[`scripts/dev/setup-unitree-wsl.sh`](../scripts/dev/setup-unitree-wsl.sh); bump them
on purpose and re-run the smoke test.

## 1. Install WSL2 and Ubuntu 22.04

Requirements: Windows 10 22H2+ or Windows 11, CPU virtualization enabled in firmware.
Check from PowerShell:

```powershell
wsl --status
wsl -l -v
(Get-CimInstance Win32_Processor).VirtualizationFirmwareEnabled
```

- **WSL not installed yet:** `wsl --install` from an *elevated* PowerShell, then reboot.
  This is the only step that may need admin rights and a restart.
- **WSL already present** (for example because Docker Desktop installed it): installing a
  distro needs neither admin rights nor a reboot:

```powershell
wsl --install -d Ubuntu-22.04 --no-launch --web-download
wsl -d Ubuntu-22.04
```

The first interactive launch asks you to create a Linux user. Other distros (such as
`docker-desktop`) are left alone, and the default distro does not change unless you run
`wsl --set-default Ubuntu-22.04`.

Keep the workspace on the Linux filesystem (`~/unitree`), not under `/mnt/c`; builds and
Python imports are much slower across the Windows mount.

## 2. Run the setup script

From a clone of this repo inside WSL (or via `/mnt/c/...` if the clone lives on Windows):

```bash
bash scripts/dev/setup-unitree-wsl.sh
```

It is idempotent: re-running it skips work that is already done, re-checks the pins, and
re-applies the sim config. It:

1. installs apt deps (compiler, CMake, Python venv, GL/GLFW/OSMesa libraries, Xvfb);
2. builds CycloneDDS `0.10.2` (the `releases/0.10.x` line) into
   `$UNITREE_WS/cyclonedds/install` and exports `CYCLONEDDS_HOME`;
3. creates `$UNITREE_WS/venv` and installs `cyclonedds==0.10.2` from source against that
   build (`--no-binary cyclonedds`), so the Python binding and the C library match;
4. clones `unitree_sdk2_python` at the pinned commit and runs `pip install -e`;
5. installs pinned `mujoco` and `pygame`;
6. clones `unitree_mujoco` at the pinned commit and sets
   `simulate_python/config.py` to `ROBOT = "go2"`, `DOMAIN_ID = 1`, `INTERFACE = "lo"`,
   `USE_JOYSTICK = 0`;
7. clones `ohho-sdk` at the pinned commit and runs `pip install -e ohho-sdk[unitree]`
   (skip with `SKIP_OHHO_SDK=1`, or point `OHHO_SDK_DIR` at an existing checkout);
8. writes `$UNITREE_WS/env.sh`.

Before working in a new shell:

```bash
. ~/unitree/env.sh
```

Overrides: `UNITREE_WS=/some/path`, `SKIP_OHHO_SDK=1`, `OHHO_SDK_DIR=/path/to/ohho-sdk`,
`MUJOCO_PY_VERSION`, `PYGAME_VERSION`.

## 3. Smoke test (sim only)

```bash
bash scripts/dev/smoke-unitree-sim.sh
```

[`scripts/dev/smoke-unitree-sim.sh`](../scripts/dev/smoke-unitree-sim.sh):

1. starts `unitree_mujoco/simulate_python/unitree_mujoco.py` (Go2, `DOMAIN_ID=1`,
   `INTERFACE=lo`, `USE_JOYSTICK=0`) headless under Xvfb;
2. runs `simulate_python/test/test_unitree_sdk2.py`, which subscribes to `rt/lowstate`
   (`LowState_`) and `rt/sportmodestate` (`SportModeState_`) on DDS domain 1 over `lo`;
3. prints the first LowState IMU sample and SportModeState positions, and exits 0 only if
   both arrived.

`test_unitree_sdk2.py` also publishes `rt/lowcmd` (1 Nm per joint) to the sim. It is a
sim-only test. Do not run it with a real robot's interface.

Set `HEADLESS=0` to open the MuJoCo viewer window instead (see WSLg below).

## 4. MuJoCo viewer through WSLg

WSL 2 on Windows 11 ships WSLg, which provides an X11/Wayland display (`DISPLAY=:0`,
`WAYLAND_DISPLAY=wayland-0`) inside the distro. Check with `wsl --version` (look for a
`WSLg version` line) and `echo $DISPLAY` inside Ubuntu. With WSLg:

```bash
. ~/unitree/env.sh
cd ~/unitree/unitree_mujoco/simulate_python
python unitree_mujoco.py
```

opens the viewer as a normal Windows window. Without a display (SSH, CI, scripts), wrap it
in `xvfb-run -a` as the smoke script does. `mujoco.viewer.launch_passive` needs some
display, so `MUJOCO_GL=egl` alone is not enough for `unitree_mujoco.py`.

If the viewer is slow, check `glxinfo -B` (from `mesa-utils`): WSLg uses the `D3D12` Mesa
driver for GPU-accelerated OpenGL; `llvmpipe` means software rendering. On a PC with both an
integrated and a discrete GPU, WSLg may pick the integrated one. On Varun's PC it reported
`D3D12 (AMD Radeon(TM) Graphics)`. To render on the NVIDIA card instead:

```bash
export MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA
glxinfo -B | grep 'OpenGL renderer'
```

The headless smoke test runs under Xvfb with Mesa's software renderer, so its result does not
depend on which GPU WSLg picks.

## 5. GPU passthrough (for the optional Isaac Lab step)

WSL2 exposes the Windows NVIDIA driver to Linux; install **no** NVIDIA driver inside
Ubuntu. `nvidia-smi` inside WSL should show the same GPU as on Windows. CUDA user-space
toolkits can be installed inside WSL with NVIDIA's `wsl-ubuntu` CUDA repo, which ships
without a driver.

Recorded on Varun's PC (4 Oct 2026):

| Item | Value |
|---|---|
| GPU | NVIDIA GeForce RTX 5060 Ti (Blackwell) |
| VRAM | 16 GB (16311 MiB reported by `nvidia-smi`) |
| Windows driver | 591.86, CUDA 13.1 |
| Visible inside WSL2 | yes, `nvidia-smi` in Ubuntu-22.04 reports the same card |
| CPU / RAM | AMD Ryzen 7 9700X (8C/16T) / 32 GB (WSL2 gets 16 GB by default) |

Isaac Lab notes (not set up by this repo yet; checked against the Isaac Sim requirements
page on 4 Oct 2026):

- **Isaac Sim is not supported inside WSL2.** NVIDIA's forum staff confirm the RTX rendering
  features Isaac Sim needs do not work there, and the Isaac Sim container is Linux-only.
  WSL2 GPU passthrough is fine for plain CUDA/PyTorch work, but for Isaac Lab training use
  Isaac Sim installed natively on Windows 11, native Ubuntu, or a cloud GPU.
- Isaac Sim's listed minimum GPU is a GeForce RTX 4080 with 16 GB VRAM. The RTX 5060 Ti meets
  the 16 GB VRAM minimum but is a lower class of card, so expect fewer parallel environments
  and slower training than the reference spec. Isaac Lab training needs extra VRAM on top.
- Isaac Sim lists Windows driver 595.97 as tested; this PC has 591.86, so update the NVIDIA
  driver before the Isaac Lab step. RTX 50-series (Blackwell) also needs CUDA 12.8+ builds of
  PyTorch.
- WSL2 caps memory at half of host RAM by default. If you run heavy CUDA work in WSL anyway,
  raise it with `%UserProfile%\.wslconfig` (`[wsl2]` / `memory=24GB`), then `wsl --shutdown`
  (this stops all distros, including Docker Desktop's).

References: https://docs.isaacsim.omniverse.nvidia.com/latest/installation/requirements.html
and https://forums.developer.nvidia.com/t/is-it-possible-to-run-isaac-sim-in-wsl2/349609

## 6. CycloneDDS on loopback

`unitree_sdk2py.core.channel.ChannelFactoryInitialize(1, "lo")` generates its own
CycloneDDS config that binds to the named interface, so the sim and the SDK find each other
on `lo` without extra setup. For other DDS tools (for example the `ddsperf` binary in
`$CYCLONEDDS_HOME/bin`, or `unitree_ros2` later), use an explicit loopback config:

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<CycloneDDS xmlns="https://cdds.io/config">
  <Domain Id="any">
    <General>
      <Interfaces>
        <NetworkInterface name="lo" priority="default" multicast="default" />
      </Interfaces>
      <AllowMulticast>spdp</AllowMulticast>
    </General>
  </Domain>
</CycloneDDS>
```

Save it as `~/unitree/cyclonedds-lo.xml` and export
`CYCLONEDDS_URI=file://$HOME/unitree/cyclonedds-lo.xml`. Keep using `DOMAIN_ID=1` for sim so
that it never shares a domain with a robot (the Go2 uses domain 0).

## 7. Hardware phase: not in WSL2

Do **not** use WSL2 to talk to a real Go2. WSL2 sits behind a NAT'd virtual NIC (or
mirrored networking, which still has caveats), so DDS discovery multicast to the robot's
Ethernet interface is unreliable, and the robot's `192.168.123.x` network is not directly
on a Linux interface. For the hardware phase, use native Ubuntu 22.04 on a laptop wired
to the robot, or the Go2's onboard Jetson. The sim setup above stays useful for developing
and testing before that.

## Troubleshooting

- `Could not locate cyclonedds` while installing the Python binding: `CYCLONEDDS_HOME` is not
  set or not built. Re-run the setup script, or `. ~/unitree/env.sh` before `pip install`.
- Smoke test fails with no messages: make sure nothing else is using domain 1, and look at
  the logs printed at the end (`/tmp/ohho-smoke.*`).
- `wsl --install` asks for a reboot: WSL itself (the Windows feature) was not installed.
  Run it from an elevated PowerShell and reboot once, then install the distro as above.

## Verification log

Run on Varun's PC, Sunday 4 Oct 2026, 11:00 to 11:05 BST (Windows 11 Pro build 26200,
WSL 2.6.3.0, WSLg 1.0.71, AMD Ryzen 7 9700X, 32 GB RAM). Before this, WSL2 was present
(from Docker Desktop) with only the `docker-desktop` distro, which was left untouched.

1. `wsl --install -d Ubuntu-22.04 --no-launch --web-download` finished in 13 s with no
   reboot and no UAC prompt.
2. On that fresh distro, `bash scripts/dev/setup-unitree-wsl.sh` exited 0 in 1 min 21 s.
   It ran as root with `UNITREE_WS=/opt/unitree`, because no Linux user had been created yet
   (Ubuntu asks for one on the first interactive launch).
3. Re-running the setup exited 0 in 6 s (idempotent: CycloneDDS was not rebuilt and the
   binding was not reinstalled). Then the smoke test ran:

```text
### 2026-10-04T11:05:16+01:00 OHH-114 verification on varunvaidhiya, WSL distro: Ubuntu-22.04
OS: Ubuntu 22.04.5 LTS, kernel 6.6.87.2-microsoft-standard-WSL2
setup re-run exit=0 in 6s
cyclonedds       0.10.2
unitree_sdk2py   1.0.1
mujoco           3.3.7
pygame           2.6.1
ohho-os          1.1.3
imports ok
cyclonedds 9995905bce6c4cf9f740d6438bbf7fcfd1c83dfd 0.10.2
unitree_sdk2_python 814556d15970dd2ecf1c9984e845ca02ab07e206
unitree_mujoco 1eb6642e3f3fdfb7fb13a9794fd6a2dd93ea0e7d
ohho-sdk f4a83fa4c87f50a0421048a2216e3c47767768b3
libddsc.so.0 => /opt/unitree/cyclonedds/install/lib/libddsc.so.0
NVIDIA GeForce RTX 5060 Ti, 16311 MiB, 591.86
== 2026-10-04T11:05:22+01:00 smoke test
ROBOT = "go2"
DOMAIN_ID = 1
INTERFACE = "lo"
USE_JOYSTICK = 0
== starting unitree_mujoco headless (Xvfb)
python: selected interface "lo" is not multicast-capable: disabling multicast
== running test/test_unitree_sdk2.py for 5s
== LowState (rt/lowstate) messages: 973
IMU state:  IMUState_(quaternion=[0.9986482858657837, 7.437350177497137e-06, -0.05197732895612717, -1.9341981897014193e-05], gyroscope=[-1.7787581327866064e-06, -1.7197514807776315e-06, -5.35751993879785e-08], accelerometer=[1.0184167623519897, 0.0001653706858633086, 9.756994247436523], rpy=[0.0, 0.0, 0.0], temperature=0)
== SportModeState (rt/sportmodestate) messages: 973
Position:  [-0.08040215075016022, 4.250716301612556e-06, 0.1165463775396347]
Position:  [-0.08040215820074081, 4.251578047842486e-06, 0.1165463775396347]
Position:  [-0.08040215820074081, 4.252437520335661e-06, 0.1165463775396347]
PASS: Go2 LowState and SportModeState received over DDS domain 1 on lo
smoke exit=0
```

(Lightly trimmed: the sim's link/joint table and repeated lines are cut. The
"not multicast-capable" line is expected on `lo`; CycloneDDS falls back to unicast
discovery.) This is simulation only. No physical robot was involved.
