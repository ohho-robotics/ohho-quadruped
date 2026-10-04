#!/usr/bin/env bash
# setup-unitree-wsl.sh - Unitree Go2 simulation dev environment for WSL2 Ubuntu 22.04.
#
# Installs, idempotently (safe to re-run):
#   - apt build/runtime deps (incl. xvfb for headless runs)
#   - CycloneDDS C library, tag 0.10.2, built from source into $UNITREE_WS/cyclonedds/install
#   - a Python venv at $UNITREE_WS/venv with:
#       cyclonedds==0.10.2 (built against CYCLONEDDS_HOME), unitree_sdk2_python (editable, pinned),
#       mujoco + pygame (pinned), and ohho-sdk[unitree] (editable, pinned; skippable)
#   - unitree_mujoco (pinned) with simulate_python/config.py set for Go2 on domain 1 / lo, no joystick
#   - $UNITREE_WS/env.sh, which you source before working
#
# Usage:
#   bash scripts/dev/setup-unitree-wsl.sh
# Environment overrides:
#   UNITREE_WS=~/unitree     where everything lives (default: $HOME/unitree)
#   SKIP_OHHO_SDK=1          do not install ohho-sdk[unitree]
#   OHHO_SDK_DIR=/path       use an existing ohho-sdk checkout instead of cloning one
#
# Nothing here touches Windows, other WSL distros, or the network config of the host.

set -euo pipefail

UNITREE_WS="${UNITREE_WS:-$HOME/unitree}"

# Pinned versions. Bump deliberately and re-run the smoke test (scripts/dev/smoke-unitree-sim.sh).
CYCLONEDDS_REPO="https://github.com/eclipse-cyclonedds/cyclonedds.git"
CYCLONEDDS_REF="9995905bce6c4cf9f740d6438bbf7fcfd1c83dfd"          # tag 0.10.2 (releases/0.10.x line)
CYCLONEDDS_PY_VERSION="0.10.2"                                    # required by unitree_sdk2py
SDK2PY_REPO="https://github.com/unitreerobotics/unitree_sdk2_python.git"
SDK2PY_REF="814556d15970dd2ecf1c9984e845ca02ab07e206"
MUJOCO_SIM_REPO="https://github.com/unitreerobotics/unitree_mujoco.git"
MUJOCO_SIM_REF="1eb6642e3f3fdfb7fb13a9794fd6a2dd93ea0e7d"
OHHO_SDK_REPO="https://github.com/ohho-robotics/ohho-sdk.git"
OHHO_SDK_REF="f4a83fa4c87f50a0421048a2216e3c47767768b3"
MUJOCO_PY_VERSION="${MUJOCO_PY_VERSION:-3.3.7}"
PYGAME_VERSION="${PYGAME_VERSION:-2.6.1}"

log() { printf '\n==> %s\n' "$*"; }

if [ "$(id -u)" -eq 0 ]; then SUDO=""; else SUDO="sudo"; fi

if ! grep -qi microsoft /proc/version 2>/dev/null; then
  echo "note: this does not look like WSL; continuing anyway (native Ubuntu 22.04 also works)." >&2
fi
if [ -r /etc/os-release ]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  if [ "${VERSION_ID:-}" != "22.04" ]; then
    echo "note: tested on Ubuntu 22.04, this is ${PRETTY_NAME:-unknown}." >&2
  fi
fi

# Clone $1 into $2 (if missing) and check out commit $3. Optional $4 is a repo-relative file that
# this script edits after checkout; it is restored before moving to a new pin so a pin bump is not
# blocked by our own edit. Any other local change makes the checkout fail rather than be discarded.
clone_pinned() {
  local repo="$1" dir="$2" ref="$3" own_edit="${4:-}"
  if [ ! -d "$dir/.git" ]; then
    git clone --quiet "$repo" "$dir"
  fi
  if [ "$(git -C "$dir" rev-parse HEAD)" != "$ref" ]; then
    git -C "$dir" fetch --quiet origin
    if [ -n "$own_edit" ]; then
      git -C "$dir" checkout --quiet -- "$own_edit"
    fi
    git -C "$dir" checkout --quiet --detach "$ref"
  fi
  echo "$(basename "$dir") @ $(git -C "$dir" rev-parse --short HEAD)"
}

log "apt dependencies"
$SUDO apt-get update -qq
DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y -qq --no-install-recommends \
  build-essential cmake git ca-certificates pkg-config \
  python3 python3-dev python3-venv python3-pip \
  libgl1 libegl1 libglfw3 libglew2.2 libosmesa6 mesa-utils \
  libsdl2-2.0-0 xvfb xauth >/dev/null

mkdir -p "$UNITREE_WS"

log "CycloneDDS C library (0.10.2)"
CYCLONEDDS_SRC="$UNITREE_WS/cyclonedds"
CYCLONEDDS_HOME="$CYCLONEDDS_SRC/install"
export CYCLONEDDS_HOME
clone_pinned "$CYCLONEDDS_REPO" "$CYCLONEDDS_SRC" "$CYCLONEDDS_REF"
STAMP="$CYCLONEDDS_HOME/.ohho-built-$CYCLONEDDS_REF"
if [ ! -f "$STAMP" ]; then
  cmake -S "$CYCLONEDDS_SRC" -B "$CYCLONEDDS_SRC/build" \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$CYCLONEDDS_HOME" \
    -DBUILD_EXAMPLES=OFF -DBUILD_TESTING=OFF -DBUILD_IDLC=ON >/dev/null
  cmake --build "$CYCLONEDDS_SRC/build" --target install -j "$(nproc)" >/dev/null
  touch "$STAMP"
else
  echo "already built: $CYCLONEDDS_HOME"
fi

log "Python venv"
VENV="$UNITREE_WS/venv"
[ -x "$VENV/bin/python" ] || python3 -m venv "$VENV"
PY="$VENV/bin/python"
"$PY" -m pip install --quiet --upgrade pip setuptools wheel

log "cyclonedds Python binding ${CYCLONEDDS_PY_VERSION} (built against CYCLONEDDS_HOME)"
if [ "$("$PY" -c 'import importlib.metadata as m; print(m.version("cyclonedds"))' 2>/dev/null || true)" != "$CYCLONEDDS_PY_VERSION" ]; then
  "$PY" -m pip install --quiet --no-binary cyclonedds "cyclonedds==${CYCLONEDDS_PY_VERSION}"
else
  echo "already installed"
fi

log "unitree_sdk2_python (editable, pinned)"
clone_pinned "$SDK2PY_REPO" "$UNITREE_WS/unitree_sdk2_python" "$SDK2PY_REF"
"$PY" -m pip install --quiet -e "$UNITREE_WS/unitree_sdk2_python"

log "mujoco ${MUJOCO_PY_VERSION} + pygame ${PYGAME_VERSION}"
"$PY" -m pip install --quiet "mujoco==${MUJOCO_PY_VERSION}" "pygame==${PYGAME_VERSION}"

log "unitree_mujoco (pinned) + Go2 / domain 1 / lo / no joystick config"
clone_pinned "$MUJOCO_SIM_REPO" "$UNITREE_WS/unitree_mujoco" "$MUJOCO_SIM_REF" simulate_python/config.py
SIM_CFG="$UNITREE_WS/unitree_mujoco/simulate_python/config.py"
sed -i -E \
  -e 's/^ROBOT = "[a-z0-9]+"/ROBOT = "go2"/' \
  -e 's/^DOMAIN_ID = [0-9]+/DOMAIN_ID = 1/' \
  -e 's/^INTERFACE = "[^"]*"/INTERFACE = "lo"/' \
  -e 's/^USE_JOYSTICK = [0-9]+/USE_JOYSTICK = 0/' \
  "$SIM_CFG"
grep -E '^(ROBOT|DOMAIN_ID|INTERFACE|USE_JOYSTICK) =' "$SIM_CFG"

if [ "${SKIP_OHHO_SDK:-0}" = "1" ]; then
  log "ohho-sdk[unitree]: skipped (SKIP_OHHO_SDK=1)"
else
  log "ohho-sdk[unitree] (editable)"
  if [ -n "${OHHO_SDK_DIR:-}" ]; then
    echo "using existing checkout: $OHHO_SDK_DIR"
  else
    OHHO_SDK_DIR="$UNITREE_WS/ohho-sdk"
    clone_pinned "$OHHO_SDK_REPO" "$OHHO_SDK_DIR" "$OHHO_SDK_REF"
  fi
  # The [unitree] extra only asks for cyclonedds>=0.10, so the 0.10.2 build above satisfies it.
  if ! "$PY" -m pip install --quiet -e "${OHHO_SDK_DIR}[unitree]"; then
    echo "warning: ohho-sdk[unitree] did not install; the Unitree sim still works without it." >&2
  fi
fi

log "env.sh"
cat > "$UNITREE_WS/env.sh" <<ENVEOF
# Generated by ohho-quadruped scripts/dev/setup-unitree-wsl.sh. Source it: . $UNITREE_WS/env.sh
export UNITREE_WS="$UNITREE_WS"
export CYCLONEDDS_HOME="$CYCLONEDDS_HOME"
export LD_LIBRARY_PATH="$CYCLONEDDS_HOME/lib\${LD_LIBRARY_PATH:+:\$LD_LIBRARY_PATH}"
export PATH="$CYCLONEDDS_HOME/bin:\$PATH"
. "$VENV/bin/activate"
ENVEOF

log "versions"
"$PY" - <<'PYEOF'
import importlib.metadata as m
for name in ("cyclonedds", "unitree_sdk2py", "mujoco", "pygame", "ohho-os"):
    try:
        print(f"{name:16} {m.version(name)}")
    except m.PackageNotFoundError:
        print(f"{name:16} (not installed)")
import cyclonedds, unitree_sdk2py, mujoco  # noqa: F401  import check
print("imports ok")
PYEOF

echo
echo "Done. Next: . $UNITREE_WS/env.sh && bash scripts/dev/smoke-unitree-sim.sh"
