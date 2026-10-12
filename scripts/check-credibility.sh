#!/usr/bin/env bash
# Credibility check v2 entry point.
# Calls check_credibility.py (stdlib only, testable).
# Set OHHO_CRED_OFFLINE=1 to skip ONLY the network git ls-remote call.
# CI must NOT set OHHO_CRED_OFFLINE.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
exec python "$root/scripts/check_credibility.py" "$@"
