#!/usr/bin/env bash
# Placeholder: download a licence-checked Go2 velocity checkpoint (OHH-122).
# Not executed in CI. Human fills URL and verifies manifest fields after download.
set -euo pipefail

CHECKPOINT_URL="${OHHO_VELOCITY_CHECKPOINT_URL:-}"
OUT_DIR="${OHHO_VELOCITY_CHECKPOINT_DIR:-artifacts/velocity_policy}"

echo "OHH-122 velocity checkpoint download (placeholder)."
echo "Set OHHO_VELOCITY_CHECKPOINT_URL to a licence-approved artifact."
echo "Output directory: ${OUT_DIR}"
echo ""
echo "Required manifest fields after download:"
echo "  - licence   (SPDX or URL)"
echo "  - seed      (training seed integer)"
echo "  - reward_curve (path or JSON summary)"
echo ""

if [[ -z "${CHECKPOINT_URL}" ]]; then
  echo "No URL set; nothing downloaded."
  exit 0
fi

mkdir -p "${OUT_DIR}"
echo "Would download from: ${CHECKPOINT_URL}"
echo "Human TODO: implement curl/wget + checksum verify before use in sport shim."
