import json
import math
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

class HeadlessTest(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def run_game(self, ticks, scenario=None, frames=None, every=1, seed=12, expected=0, night=1):
        out = self.root / "run.jsonl"
        command = [sys.executable, "-m", "lantern", "headless", "--seed", str(seed),
                   "--night", str(night), "--ticks", str(ticks), "--out", str(out),
                   "--snapshot-every", str(every)]
        for name, content in (("scenario", scenario), ("inputs", {"frames": frames} if frames is not None else None)):
            if content is not None:
                path = self.root / (name + ".json")
                path.write_text(json.dumps(content), encoding="utf-8")
                command.extend(("--" + name, str(path)))
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, expected, result.stderr)
        self.assertEqual(result.stdout, "")
        if expected:
            self.assertTrue(result.stderr.strip())
            return None
        self.raw = out.read_bytes()
        return [json.loads(line) for line in self.raw.splitlines()]

    @staticmethod
    def snapshots(records):
        return [record for record in records if record["type"] == "snapshot"]

    @staticmethod
    def events(records, name):
        return [record for record in records if record.get("name") == name]

