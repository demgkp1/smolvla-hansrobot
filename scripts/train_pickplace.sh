#!/usr/bin/env bash
# Full fine-tune of lerobot/smolvla_base on pickplace_v1 (official lerobot, no patches).
# Usage: scripts/train_pickplace.sh smoke   # 50 steps
#        scripts/train_pickplace.sh full    # full training
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
# Do not spoof the GPU arch; the torch rocm10.0 wheel supports gfx1201 natively.
unset HSA_OVERRIDE_GFX_VERSION PYTORCH_ROCM_ARCH
# online: first run fetches missing config files from the Hub

MODE=${1:-smoke}
if [ "$MODE" = smoke ]; then
  STEPS=50; OUT=checkpoints/smoke; SAVE=50; BS=${BS:-8}
else
  STEPS=${STEPS:-20000}; OUT=checkpoints/smolvla_pickplace_full; SAVE=2000; BS=${BS:-16}
fi
rm -rf "$OUT" 2>/dev/null || true

lerobot-train \
  --policy.path=lerobot/smolvla_base \
  --policy.push_to_hub=false \
  --policy.device=cuda \
  --policy.freeze_vision_encoder=true \
  --policy.train_expert_only=true \
  --policy.empty_cameras=2 \
  --dataset.repo_id=hansrobot/pickplace_v1 \
  --dataset.root=../pickplace_v1 \
  --rename_map='{"observation.images.front": "observation.images.camera1"}' \
  --batch_size="$BS" --num_workers=4 \
  --steps="$STEPS" --log_freq=10 --save_freq="$SAVE" \
  --output_dir="$OUT" --job_name=smolvla_pickplace_"$MODE" \
  --trackio.enable=false
