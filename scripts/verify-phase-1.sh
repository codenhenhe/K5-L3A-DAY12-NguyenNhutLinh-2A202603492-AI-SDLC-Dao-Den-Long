#!/bin/sh
set -eu

cd "$(dirname "$0")/.."
# Phase 1 evidence used v1.0 rules. Replay the exact submitted tag on later versions.
if ! grep -q '"contract_version": "1.0"' game.contract.json; then
    if ! git rev-parse --verify --quiet refs/tags/phase-1 >/dev/null; then
        echo "Fetch or check out the phase-1 tag to verify Contract v1.0." >&2
        exit 1
    fi
    output_dir=
    if [ "$#" -gt 0 ]; then
        mkdir -p "$1"
        output_dir=$(cd "$1" && pwd)
    fi
    legacy=$(mktemp -d)
    trap 'rm -rf "$legacy"' EXIT
    git archive --format=tar --output="$legacy/source.tar" refs/tags/phase-1
    tar -xf "$legacy/source.tar" -C "$legacy"
    if [ -n "$output_dir" ]; then
        sh "$legacy/scripts/verify-phase-1.sh" "$output_dir"
    else
        sh "$legacy/scripts/verify-phase-1.sh"
    fi
    exit
fi
output_dir=${1:-$(mktemp -d)}
mkdir -p "$output_dir"
python3 -m unittest discover -s tests -v

run() {
    python3 -m lantern headless --seed 12 --night 1 --ticks 1800 \
        --snapshot-every 300 "$@"
}
run --inputs docs/proof/phase-1/win.inputs.json --out "$output_dir/win.jsonl"
run --inputs docs/proof/phase-1/win.inputs.json --out "$output_dir/win-repeat.jsonl"
cmp "$output_dir/win.jsonl" "$output_dir/win-repeat.jsonl"
run --out "$output_dir/loss.jsonl"

python3 - "$output_dir" <<'PY'
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
for name, expected in (("win", "won"), ("loss", "lost")):
    rows = [json.loads(row) for row in (root / (name + ".jsonl")).read_text().splitlines()]
    end = rows[-1]
    assert (end["type"], end["state"]) == ("end", expected), end
    events = [row["name"] for row in rows if row["type"] == "event"]
    if name == "win":
        assert events.count("lantern_lit") == 5, events
    else:
        assert events.count("player_hit") == 3, events
    print(name + ": " + json.dumps(end))
print("Deterministic: the two win traces match byte for byte.")
PY
