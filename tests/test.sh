#!/bin/sh
set -u

reward_dir="${REWARD_DIR:-/logs/verifier}"
mkdir -p "$reward_dir"

if python3 /tests/verifier.py; then
    printf '1.0\n' > "$reward_dir/reward.txt"
    exit 0
else
    printf '0.0\n' > "$reward_dir/reward.txt"
    exit 0
fi
