#!/bin/sh
set -eu

cd "$(dirname "$0")/.."
# Phase 2 evidence used v1.1 rules. Replay the exact submitted tag on later versions.
if ! grep -q '"contract_version": "1.1"' game.contract.json; then
    if ! git rev-parse --verify --quiet refs/tags/phase-2 >/dev/null; then
        echo "Fetch or check out the phase-2 tag to verify Contract v1.1." >&2
        exit 1
    fi
    output_dir=
    if [ "$#" -gt 0 ]; then
        mkdir -p "$1"
        output_dir=$(cd "$1" && pwd)
    fi
    legacy=$(mktemp -d)
    trap 'rm -rf "$legacy"' EXIT
    git archive --format=tar --output="$legacy/source.tar" refs/tags/phase-2
    tar -xf "$legacy/source.tar" -C "$legacy"
    if [ -n "$output_dir" ]; then
        sh "$legacy/scripts/verify-phase-2.sh" "$output_dir"
    else
        sh "$legacy/scripts/verify-phase-2.sh"
    fi
    exit
fi
output_dir=${1:-$(mktemp -d)}
mkdir -p "$output_dir"
python3 -m compileall -q lantern
python3 -m unittest discover -s tests -v

python3 - "$output_dir" <<'PY'
import json
import math
from pathlib import Path
import subprocess
import sys
from time import perf_counter

output = Path(sys.argv[1])
fixtures = Path("docs/proof/phase-2")
tuning = json.loads(Path("game.contract.json").read_text())["tuning"]

def run(night, ticks, out, *args):
    subprocess.run([
        sys.executable, "-m", "lantern", "headless", "--seed", "42", "--night", str(night),
        "--ticks", str(ticks), "--out", str(out), *args,
    ], check=True)

with output.joinpath("timed.scenario.json").open("w") as file:
    # Allow a complete night of idle play with real spawns and weather.
    json.dump({"player": {"invuln_ticks": 21601}}, file)

for night in (1, 2, 3):
    start = perf_counter()
    trace = output / f"night{night}.jsonl"
    run(night, 21600, trace, "--scenario", str(output / "timed.scenario.json"),
        "--snapshot-every", "1200")
    elapsed = perf_counter() - start
    end = json.loads(trace.read_text().splitlines()[-1])
    assert end["type"] == "end" and end["ticks"] == min(21600, math.ceil(tuning[f"night{night}_duration_s"] * 60)), end
    assert elapsed <= 30, (night, elapsed)
    print(f"night={night}, ticks={end['ticks']}, state={end['state']}, wall_s={elapsed:.3f}")

options = ("--scenario", str(fixtures / "mechanics.scenario.json"),
           "--inputs", str(fixtures / "mechanics.inputs.json"), "--snapshot-every", "2")
trace = output / "mechanics.jsonl"
repeat = output / "mechanics-repeat.jsonl"
run(2, 12, trace, *options)
run(2, 12, repeat, *options)
assert trace.read_bytes() == repeat.read_bytes()
events = [row.get("name") for line in trace.read_text().splitlines() if (row := json.loads(line))["type"] == "event"]
required = {"night_start", "charm_picked", "drifter_steal", "player_hit", "drifter_drop", "paused", "resumed", "dash"}
assert required <= set(events), required - set(events)
print("Deterministic mechanics trace:", trace)
PY
