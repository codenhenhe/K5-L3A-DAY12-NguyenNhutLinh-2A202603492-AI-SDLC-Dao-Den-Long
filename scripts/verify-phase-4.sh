#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
output=${1:-$(mktemp -d)}
mkdir -p "$output"
output=$(cd "$output" && pwd)
python3 -m compileall -q lantern
python3 -m unittest discover -s tests -v
sh scripts/verify-phase-3.sh "$output/phase-3"
cmp docs/proof/phase-3/dawn-win.jsonl "$output/phase-3/dawn-win.jsonl"
cmp docs/proof/phase-3/dawn-loss.jsonl "$output/phase-3/dawn-loss.jsonl"
python3 -m lantern headless --seed 42 --night 1 --ticks 180 --snapshot-every 30 \
    --scenario docs/proof/phase-3/dawn.scenario.json --inputs docs/proof/phase-3/dawn.inputs.json \
    --out "$output/current-replay.jsonl"
cmp docs/proof/phase-3/dawn-win.jsonl "$output/current-replay.jsonl"
printf '%s\n' "v1.3 headless replay matches v1.2 evidence byte for byte."
python3 -m lantern soak --seed 7 --nights 10 --out "$output/soak.json"
python3 - "$output/soak.json" <<'PY'
import json
from pathlib import Path
import sys

soak = json.loads(Path(sys.argv[1]).read_text())
assert len(soak["results"]) == soak["nights"] == 10
assert soak["crashes"] == 0
assert soak["mem_end_mb"] <= 1.2 * soak["mem_start_mb"], soak
print("Soak: 10 nights, no crashes, current RSS within 120%.")
PY
python3 scripts/build_release.py
python3 dist/dao-den-long-v1.0.0.pyz headless --seed 42 --night 1 --ticks 10 --out "$output/package.jsonl"
python3 -m lantern headless --seed 42 --night 1 --ticks 10 --out "$output/source.jsonl"
cmp "$output/package.jsonl" "$output/source.jsonl"
LANTERN_DATA_DIR="$output/data" python3 dist/dao-den-long-v1.0.0.pyz play --export-leaderboard "$output/leaderboard.json"
printf '%s\n' "Evidence: $output"
