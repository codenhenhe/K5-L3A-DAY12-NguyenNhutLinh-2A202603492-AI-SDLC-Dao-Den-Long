from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from lantern.benchmark import Scene, frame_metrics
from lantern.game import DEFAULT_INPUT, FUEL_MAX, Game
from lantern.leaderboard import entries, save
from lantern.server import Campaign
from lantern.soak import random_night


class PhaseFourTest(unittest.TestCase):
    def test_benchmark_scene_is_fixed_and_only_wanders(self):
        scene = Scene(42)
        world = scene.game
        self.assertEqual((len(world.shades), len(world.motes)), (200, 100))
        self.assertEqual(world.pos, [0, 0, 0])
        self.assertEqual([lamp.fuel_units for lamp in world.lanterns], [FUEL_MAX] * 3 + [0, 0])
        self.assertEqual(scene.game.snapshot(), Scene(42).game.snapshot())
        before = [shade.pos[:] for shade in world.shades]
        scene.advance(60)
        self.assertNotEqual([shade.pos for shade in world.shades], before)
        self.assertTrue(all(shade.state == "wander" for shade in world.shades))
        self.assertEqual((len(world.shades), len(world.motes), world.flames), (200, 100, 3))
        self.assertEqual([lamp.fuel_units for lamp in world.lanterns], [FUEL_MAX] * 3 + [0, 0])

    def test_benchmark_statistics_use_slowest_one_percent_and_nearest_rank(self):
        stats = frame_metrics([10] * 100 + [20, 100])
        self.assertEqual(stats["frames"], 102)
        self.assertAlmostEqual(stats["avg_fps"], 1000 * 102 / 1120, places=3)
        self.assertAlmostEqual(stats["p1_low_fps"], 1000 / 60, places=3)
        self.assertEqual(stats["frame_ms_p95"], 10)
        with self.assertRaises(ValueError):
            frame_metrics([])

    def test_persistent_top_ten_and_ordering(self):
        with TemporaryDirectory() as folder:
            sqlite = Path(folder) / "rank.sqlite3"
            for index in range(12):
                save(f"Test{index:02}", index // 2, index % 4, 2**63 + index, sqlite)
            table = entries(sqlite)
            self.assertEqual(len(table), 10)
            self.assertEqual([row["name"] for row in table[:4]], ["Test10", "Test11", "Test08", "Test09"])
            self.assertEqual(table[0]["seed"], 2**63 + 10)
            self.assertIsNotNone(datetime.fromisoformat(table[0]["achieved_at"]).tzinfo)
            with self.assertRaises(ValueError):
                save("x!", 100, 0, 0, sqlite)

    def test_campaign_banks_only_wins_once_and_keeps_initial_seed(self):
        campaign = Campaign(12)
        campaign.game = Game(12, {"time_left_s": 1/60, "lanterns": [
            {"id": f"L{i}", "lit": True} for i in (1, 2, 3)]})
        campaign.step(1, DEFAULT_INPUT)
        campaign.step(1, DEFAULT_INPUT)
        self.assertEqual(campaign.nights_won, 1)
        points = campaign.score
        self.assertGreater(points, 0)
        with self.assertRaises(ValueError):
            campaign.save_score("May")
        campaign.start(2)
        campaign.game.state = "lost"
        campaign.game.score = 50
        campaign.step(1, DEFAULT_INPUT)
        self.assertEqual((campaign.score, campaign.nights_won, campaign.seed), (points, 1, 12))

    def test_practice_can_start_later_and_retry_without_ranking(self):
        run = Campaign(12, practice_night=2)
        self.assertEqual(run.game.night, 2)
        run.game = Game(13, {"time_left_s": 1 / 60, "lanterns": [
            {"id": f"L{i}", "lit": True} for i in range(1, 5)]}, night=2)
        run.step(1, DEFAULT_INPUT)
        self.assertEqual(run.game.state, "won")
        self.assertGreater(run.game.score, 0)
        self.assertEqual(run.summary(), {"score": 0, "nights_won": 0})
        with self.assertRaises(ValueError):
            run.start(3)
        with self.assertRaisesRegex(ValueError, "luyện tập"):
            run.save_score("May")
        run.start(2)
        self.assertEqual((run.game.night, run.game.tick), (2, 0))
        run.game.state = "lost"
        with self.assertRaisesRegex(ValueError, "luyện tập"):
            run.save_score("May")

    def test_soak_random_input_repeats_seed_and_cli_emits_record(self):
        left = random_night(Game(7), 7)
        right = random_night(Game(7), 7)
        self.assertEqual(left, right)
        with TemporaryDirectory() as folder:
            output = Path(folder) / "soak.json"
            subprocess.run([sys.executable, "-m", "lantern", "soak", "--seed", "7",
                            "--nights", "3", "--out", str(output)], check=True)
            result = json.loads(output.read_text())
            self.assertEqual(result["nights"], len(result["results"]))
            self.assertEqual(result["crashes"], 0)
            self.assertGreater(result["mem_start_mb"], 0)
