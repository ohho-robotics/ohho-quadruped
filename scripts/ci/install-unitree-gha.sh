#!/usr/bin/env bash
# install-unitree-gha.sh — Ubuntu 22.04 stack for MuJoCo + DDS smoke on GitHub Actions.
# Simulation only: DOMAIN_ID=1, INTERFACE=lo. Never use domain 0 or a non-loopback NIC here.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
. "$SCRIPT_DIR/pins.sh"

UNITREE_WS="${UNITREE_WS:-$HOME/unitree}"
export UNITREE_WS

log() { printf '\n==> %s\n' "$*"; }

# BEGIN clone_pinned
# clone_pinned REPO DIR REF [EDITED_FILE]
# Reuse DIR when it is already a git checkout at REF. Otherwise remove it and
# clone REF. actions/cache restores cyclonedds/install before this runs, so the
# parent can exist with no .git and git clone refuses it. That install prefix
# is put back after the clone; a git checkout at the wrong commit is removed
# entirely. EDITED_FILE is reapplied by the caller after this returns.
clone_pinned() {
  local repo="$1" dir="$2" ref="$3"
  local head="" scratch="" rc=0

  if [ -d "$dir/.git" ]; then
    head="$(git -C "$dir" rev-parse HEAD 2>/dev/null || true)"
    if [ "$head" = "$ref" ]; then
      echo "$(basename "$dir") @ $(git -C "$dir" rev-parse --short HEAD)"
      return 0
    fi
  fi

  if [ -e "$dir" ]; then
    if [ -z "${UNITREE_WS:-}" ] || [ "$dir" = "$UNITREE_WS" ]; then
      echo "refusing to remove $dir" >&2
      return 1
    fi
    case "$dir" in
      "$UNITREE_WS"/*) ;;
      *)
        echo "refusing to remove $dir" >&2
        return 1
        ;;
    esac
  fi

  if [ -d "$dir/install" ] && [ ! -d "$dir/.git" ]; then
    scratch="$(mktemp -d "${TMPDIR:-/tmp}/ohho-clone-install.XXXXXX")"
    mv "$dir/install" "$scratch/install"
  fi
  if [ -e "$dir" ]; then
    rm -rf "$dir"
  fi

  if ! git clone --quiet "$repo" "$dir"; then
    rc=1
  elif [ "$(git -C "$dir" rev-parse HEAD)" != "$ref" ]; then
    if ! git -C "$dir" fetch --quiet origin; then
      rc=1
    elif ! git -C "$dir" checkout --quiet --detach "$ref"; then
      rc=1
    fi
  fi

  if [ -n "$scratch" ] && [ -d "$scratch/install" ]; then
    mkdir -p "$dir"
    rm -rf "$dir/install"
    mv "$scratch/install" "$dir/install"
  fi
  if [ -n "$scratch" ]; then
    rm -rf "$scratch"
  fi
  if [ "$rc" -ne 0 ]; then
    return "$rc"
  fi
  echo "$(basename "$dir") @ $(git -C "$dir" rev-parse --short HEAD)"
}
# END clone_pinned

log "apt dependencies"
sudo apt-get update -qq
DEBIAN_FRONTEND=noninteractive sudo apt-get install -y -qq --no-install-recommends \
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

log "cyclonedds Python binding ${CYCLONEDDS_PY_VERSION}"
if [ "$("$PY" -c 'import importlib.metadata as m; print(m.version("cyclonedds"))' 2>/dev/null || true)" != "$CYCLONEDDS_PY_VERSION" ]; then
  "$PY" -m pip install --quiet --no-binary cyclonedds "cyclonedds==${CYCLONEDDS_PY_VERSION}"
fi

log "unitree_sdk2_python (editable, pinned)"
clone_pinned "$SDK2PY_REPO" "$UNITREE_WS/unitree_sdk2_python" "$SDK2PY_REF"
"$PY" -m pip install --quiet -e "$UNITREE_WS/unitree_sdk2_python"

log "mujoco ${MUJOCO_PY_VERSION} + pygame ${PYGAME_VERSION}"
"$PY" -m pip install --quiet "mujoco==${MUJOCO_PY_VERSION}" "pygame==${PYGAME_VERSION}"

log "unitree_mujoco (pinned) + Go2 / domain 1 / lo"
clone_pinned "$MUJOCO_SIM_REPO" "$UNITREE_WS/unitree_mujoco" "$MUJOCO_SIM_REF" simulate_python/config.py
SIM_CFG="$UNITREE_WS/unitree_mujoco/simulate_python/config.py"
sed -i -E \
  -e 's/^ROBOT = "[a-z0-9]+"/ROBOT = "go2"/' \
  -e 's/^DOMAIN_ID = [0-9]+/DOMAIN_ID = 1/' \
  -e 's/^INTERFACE = "[^"]*"/INTERFACE = "lo"/' \
  -e 's/^USE_JOYSTICK = [0-9]+/USE_JOYSTICK = 0/' \
  "$SIM_CFG"

install_ohho_sdk() {
  # Missing pin or missing [unitree] extra must not fail the sim stack.
  # Sport-mode behaviour under test lives in ohho_go2 (PR #8 / OHH-123), not ohho-sdk.
  if [ "${SKIP_OHHO_SDK:-0}" = "1" ]; then
    log "ohho-sdk[unitree]: skipped"
    return 0
  fi
  log "ohho-sdk (editable, pinned ${OHHO_SDK_REF})"
  OHHO_SDK_DIR="${OHHO_SDK_DIR:-$UNITREE_WS/ohho-sdk}"
  if ! clone_pinned "$OHHO_SDK_REPO" "$OHHO_SDK_DIR" "$OHHO_SDK_REF"; then
    echo "warning: ohho-sdk pin ${OHHO_SDK_REF} is not available; continuing without it." >&2
    return 0
  fi
  if [ ! -f "$OHHO_SDK_DIR/pyproject.toml" ] && [ ! -f "$OHHO_SDK_DIR/setup.py" ] && [ ! -f "$OHHO_SDK_DIR/setup.cfg" ]; then
    echo "warning: ohho-sdk @ ${OHHO_SDK_REF} has no Python project; [unitree] extra skipped." >&2
    return 0
  fi
  if ! "$PY" -m pip install --quiet -e "${OHHO_SDK_DIR}[unitree]"; then
    echo "warning: ohho-sdk[unitree] install failed; mock smoke tests still run." >&2
  fi
}

install_ohho_sdk

DOWNLOAD_SCRIPT="$SCRIPT_DIR/download-policy-checkpoint.sh"
if [ -f "$DOWNLOAD_SCRIPT" ]; then
  log "policy checkpoint (download script)"
  bash "$DOWNLOAD_SCRIPT"
else
  log "policy checkpoint: no scripts/ci/download-policy-checkpoint.sh (skipped)"
fi

log "env.sh"
cat > "$UNITREE_WS/env.sh" <<ENVEOF
# Generated by ohho-quadruped scripts/ci/install-unitree-gha.sh
export UNITREE_WS="$UNITREE_WS"
export CYCLONEDDS_HOME="$CYCLONEDDS_HOME"
export LD_LIBRARY_PATH="$CYCLONEDDS_HOME/lib\${LD_LIBRARY_PATH:+:\$LD_LIBRARY_PATH}"
export PATH="$CYCLONEDDS_HOME/bin:\$PATH"
. "$VENV/bin/activate"
ENVEOF

echo "$UNITREE_WS/env.sh"
