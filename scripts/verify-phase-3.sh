#!/bin/sh
set -eu

cd "$(dirname "$0")/.."
output_dir=${1:-$(mktemp -d)}
mkdir -p "$output_dir"
python3 -m compileall -q lantern
python3 -m unittest discover -s tests -v

python3 - "$output_dir" <<'PY'
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter

out = Path(sys.argv[1])
proof = Path("docs/proof/phase-3")

def run(night, ticks, output, cadence, scenario, inputs=None):
    command = [sys.executable, "-m", "lantern", "headless", "--seed", "42",
               "--night", str(night), "--ticks", str(ticks), "--out", str(output),
               "--snapshot-every", str(cadence), "--scenario", str(scenario)]
    if inputs is not None:
        command.extend(("--inputs", str(inputs)))
    subprocess.run(command, check=True)
    return [json.loads(line) for line in output.read_text().splitlines()]

scenario = proof / "dawn.scenario.json"
inputs = proof / "dawn.inputs.json"
win_path, repeat_path = out / "dawn-win.jsonl", out / "dawn-repeat.jsonl"
win = run(1, 180, win_path, 30, scenario, inputs)
run(1, 180, repeat_path, 30, scenario, inputs)
assert win_path.read_bytes() == repeat_path.read_bytes()
loss = run(1, 180, out / "dawn-loss.jsonl", 30, scenario)
assert [row["name"] for row in win if row["type"] == "event"] == [
    "night_start", "lantern_out", "lantern_deposited", "lantern_lit", "refuel", "fuel_drain",
    "fuel_drain", "game_over",
]
def reason(rows):
    return next(row["data"]["reason"] for row in rows if row.get("name") == "game_over")

assert reason(win) == "dawn_survived" and win[-1]["ticks"] == 120 and win[-1]["score"] == 533
assert reason(loss) == "dawn" and loss[-1]["ticks"] == 120
print("Phase 3 evidence: deterministic win (533 points) and loss at tick 120.")

timed = out / "timed.scenario.json"
timed.write_text(json.dumps({"player": {"invuln_ticks": 21601}}))
for night, expected_ticks in ((1, 14400), (2, 16200), (3, 18000)):
    start = perf_counter()
    rows = run(night, 21600, out / f"night{night}.jsonl", 1200, timed)
    duration = perf_counter() - start
    assert rows[-1]["ticks"] == expected_ticks, rows[-1]
    assert duration < 30, (night, duration)
    print(f"night={night}, ticks={rows[-1]['ticks']}, wall_s={duration:.3f}")
PY
