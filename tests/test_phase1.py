import json
import math
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from lantern.game import TUNING


BASE = {"random_motes": False, "random_shades": False}
SCORE = TUNING["score"]


class ContractTest(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def run_game(self, ticks, scenario=None, frames=None, every=1, seed=12, expected=0):
        out = self.root / "run.jsonl"
        command = [sys.executable, "-m", "lantern", "headless", "--seed", str(seed),
                   "--night", "1", "--ticks", str(ticks), "--out", str(out),
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

    def test_movement_yaw_normalization_held_input_and_ticks(self):
        records = self.run_game(60, BASE, [
            {"tick": 0, "move": [1, 1], "cam_yaw_deg": 90},
            {"tick": 30, "cam_yaw_deg": 0},
        ], every=30)
        start, middle, end = self.snapshots(records)
        self.assertEqual(start["player"]["pos"], [0, 0, 0])
        self.assertEqual([s["tick"] for s in (start, middle, end)], [0, 30, 60])
        self.assertEqual(end["sim_tick"], 60)
        half = round(TUNING["player_speed"] / (2 * math.sqrt(2)), 3)
        self.assertEqual(middle["player"]["pos"], [half, 0, -half])
        self.assertEqual(end["player"]["pos"], [round(TUNING["player_speed"] / math.sqrt(2), 3), 0, 0])
        self.assertEqual(end["time_left_s"], TUNING["night1_duration_s"] - 1)
        self.assertEqual(records[-1], {"type": "end", "ticks": 60, "state": "playing", "score": 0})

    def test_jump_one_edge_then_lands(self):
        records = self.run_game(85, BASE, [{"tick": 0, "jump": True}])
        snapshots = self.snapshots(records)
        self.assertGreater(snapshots[1]["player"]["pos"][1], 0)
        self.assertEqual(snapshots[-1]["player"]["pos"][1], 0)
        self.assertEqual([e["tick"] for e in self.events(records, "jumped")], [1])

    def test_partial_deposit_and_last_lantern_win(self):
        cost = TUNING["lantern_cost"]
        scenario = {**BASE, "time_left_s": 20, "player": {"carried": cost - 2},
                    "motes": [[2.6, 0, 0], [2.6, 0, 0]],
                    "lanterns": [{"id": f"L{i}", "lit": True} for i in range(2, 6)]
                    + [{"id": "L1", "pos": [0, 0, 0]}]}
        frames = [{"tick": 0, "interact": True}, {"tick": 1, "move": [1, 0]},
                  {"tick": 13, "move": [0, 0]},
                  {"tick": 20, "interact": False}, {"tick": 21, "interact": True}]
        records = self.run_game(60, scenario, frames)
        snapshots = self.snapshots(records)
        self.assertEqual(snapshots[0]["score"], 0)
        self.assertEqual(snapshots[1]["lanterns"][0]["deposited"], cost - 2)
        self.assertEqual(snapshots[20]["lanterns"][0]["deposited"], cost - 2)
        self.assertEqual([e["tick"] for e in self.events(records, "lantern_deposited")], [1, 22])
        self.assertTrue(snapshots[-1]["lanterns"][0]["lit"])
        self.assertEqual(records[-1], {"type": "end", "ticks": 22, "state": "won",
                                       "score": 2 * SCORE["per_mote"] + SCORE["per_lantern"]
                                       + 19 * SCORE["per_second_left"]
                                       + TUNING["flames"] * SCORE["per_flame_left"]})

    def test_pickup_capacity_radius_and_shade_ids(self):
        count = TUNING["carry_capacity"]
        records = self.run_game(1, {**BASE, "player": {"carried": count - 1},
                                     "motes": [[TUNING["pickup_radius"], 0, 0], [0, 0, 0]],
                                     "shades": [{"pos": [10, 0, 0]}, {"id": "S1", "pos": [11, 0, 0]}]})
        first, last = self.snapshots(records)
        self.assertEqual(first["motes_active"], 2)
        self.assertEqual(last["motes_active"], 1)
        self.assertEqual(last["player"]["carried"], count)
        self.assertEqual(self.events(records, "mote_picked")[0]["data"]["id"], "M1")
        self.assertEqual([shade["id"] for shade in first["shades"]], ["S2", "S1"])

    def test_pulse_spends_pushes_stuns_then_cooldown_and_recovers(self):
        cost = TUNING["pulse_cost"]
        reach = TUNING["pulse_radius"]
        records = self.run_game(155, {**BASE, "player": {"carried": cost * 2},
                                      "shades": [{"pos": [reach, 0, 0]}, {"pos": [0, 0, reach + 1]}]},
                                [{"tick": 0, "pulse": True}, {"tick": 1, "pulse": False},
                                 {"tick": 2, "pulse": True}])
        states = self.snapshots(records)
        self.assertEqual(states[1]["player"]["carried"], cost)
        self.assertEqual(states[1]["shades"][0]["state"], "stunned")
        self.assertEqual(states[1]["shades"][0]["pos"][0], reach + TUNING["pulse_push_m"])
        self.assertEqual(states[1]["shades"][1]["state"], "chase")
        self.assertEqual([event["tick"] for event in self.events(records, "pulse")], [1])
        self.assertEqual(states[150]["shades"][0]["state"], "stunned")
        self.assertEqual(states[151]["shades"][0]["state"], "chase")
        self.assertEqual(records[-1]["score"], SCORE["per_stun"])

    def test_damage_invulnerability_and_early_loss(self):
        records = self.run_game(500, {**BASE, "player": {"flames": 2, "carried": 4},
                                      "shades": [{"pos": [0, 0, 0]}, {"pos": [0, 0, 0]}]})
        hits = self.events(records, "player_hit")
        delay = math.ceil(TUNING["invuln_s"] * 60)
        self.assertEqual([hit["tick"] for hit in hits], [1, delay + 1])
        self.assertEqual(hits[0]["data"]["carried"], 4)
        self.assertEqual(records[-1], {"type": "end", "ticks": delay + 1, "state": "lost", "score": 0})

    def test_safe_radius_and_timer(self):
        radius = TUNING["safe_radius"]
        records = self.run_game(500, {**BASE, "time_left_s": 2,
                                      "lanterns": [{"id": "L1", "pos": [0, 0, 0], "lit": True}],
                                      "shades": [{"pos": [radius + 1, 0, 0]}]})
        end = self.snapshots(records)[-1]
        self.assertEqual(end["player"]["flames"], TUNING["flames"])
        self.assertGreater(end["shades"][0]["pos"][0], radius)
        self.assertEqual(end["time_left_s"], 0)
        self.assertEqual(records[-1], {"type": "end", "ticks": 120, "state": "lost", "score": 0})

    def test_pulse_cannot_push_through_a_lit_lantern_zone(self):
        radius = TUNING["safe_radius"]
        push = TUNING["pulse_push_m"]
        for x, z in ((-radius - push / 2, 0), (-push / 2, radius - 0.05)):
            with self.subTest(x=x, z=z):
                scenario = {
                    **BASE,
                    "player": {"pos": [x - 2, 0, z], "carried": TUNING["pulse_cost"]},
                    "lanterns": [{"id": "L1", "pos": [0, 0, 0], "lit": True}],
                    "shades": [{"pos": [x, 0, z]}],
                }
                records = self.run_game(2, scenario, [{"tick": 0, "pulse": True}])
                _, *snapshots = self.snapshots(records)
                for snapshot in snapshots:
                    shade = snapshot["shades"][0]
                    after_x, _, after_z = shade["pos"]
                    self.assertEqual(shade["state"], "stunned")
                    self.assertGreater(math.hypot(after_x, after_z), radius)
                    self.assertLess(after_x, 0)
                self.assertEqual(len(self.events(records, "shade_stunned")), 1)

    def test_lighting_a_lantern_repels_a_stunned_shade_past_overlapping_zones(self):
        radius = TUNING["safe_radius"]
        scenario = {
            **BASE,
            "player": {"pos": [-0.4, 0, 0], "carried": TUNING["pulse_cost"] + TUNING["lantern_cost"]},
            "lanterns": [{"id": "L1", "pos": [0, 0, 0]}, {"id": "L2", "pos": [6, 0, 0], "lit": True}],
            "shades": [{"pos": [0.2, 0, 0]}],
        }
        records = self.run_game(2, scenario, [{"tick": 0, "pulse": True}, {"tick": 1, "interact": True}])
        _, before_lighting, after_lighting = self.snapshots(records)
        self.assertLess(abs(before_lighting["shades"][0]["pos"][0]), radius)
        self.assertTrue(after_lighting["lanterns"][0]["lit"])
        self.assertEqual(after_lighting["shades"][0]["state"], "stunned")
        self.assertGreater(after_lighting["shades"][0]["pos"][0], 6 + radius)

    def test_empty_scenario_preserves_default_shore(self):
        frames = [{"tick": 0, "move": [1, 0]}]
        self.run_game(400, frames=frames, every=100)
        default_trace = self.raw
        self.run_game(400, scenario={}, frames=frames, every=100)
        self.assertEqual(self.raw, default_trace)

    def test_player_placed_beyond_shore_stays_put_until_input(self):
        records = self.run_game(2, {**BASE, "player": {"pos": [48, 0, 0]}},
                                [{"tick": 1, "move": [-1, 0]}])
        start, idle, moving = self.snapshots(records)
        self.assertEqual(start["player"]["pos"], [48, 0, 0])
        self.assertEqual(idle["player"]["pos"], start["player"]["pos"])
        self.assertAlmostEqual(moving["player"]["pos"][0], 48 - TUNING["player_speed"] / 60, places=3)

    def test_default_world_is_repeatable_and_seed_changes_spawn(self):
        first = self.run_game(480, every=10)
        expected_bytes = self.raw
        second = self.run_game(480, every=10)
        self.assertEqual(self.raw, expected_bytes)
        self.assertEqual(first, second)
        self.assertNotEqual(first[0]["shades"], self.run_game(480, every=10, seed=123)[0]["shades"])
        self.assertEqual(len(first[0]["lanterns"]), 5)

    def test_cli_rejects_invalid_files(self):
        for frames in ([{"tick": 0}, {"tick": 0}], [{"tick": 0, "move": [2, 0]}],
                       [{"tick": 0, "interact": 1}], [{"tick": 10}, {"tick": 9}]):
            with self.subTest(frames=frames):
                self.run_game(1, frames=frames, expected=2)
        self.run_game(1, {"shades": [{"pos": [0, 0]}]}, expected=2)
        self.run_game(1, {"lanterns": [{"id": "L9"}]}, expected=2)

    def test_cli_rejects_non_json_constants_even_in_extra_fields(self):
        for constant in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(constant=constant):
                self.run_game(1, frames=[{"tick": 0, "note": constant}], expected=2)
                self.run_game(1, scenario={"note": constant}, expected=2)

    def test_zero_ticks_only_initial_and_end(self):
        records = self.run_game(0, BASE, [{"tick": 0, "jump": True}])
        self.assertEqual([r["type"] for r in records], ["snapshot", "end"])
        self.assertEqual(records[-1]["ticks"], 0)


if __name__ == "__main__":
    unittest.main()
