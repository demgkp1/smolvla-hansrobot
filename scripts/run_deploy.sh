#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
unset HSA_OVERRIDE_GFX_VERSION PYTORCH_ROCM_ARCH
export HF_HUB_OFFLINE=1
exec python deploy_smolvla.py "$@"
