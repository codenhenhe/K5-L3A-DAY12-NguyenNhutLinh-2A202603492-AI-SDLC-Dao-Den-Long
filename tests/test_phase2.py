import math

from lantern.game import HZ, TUNING, ticks
from lantern.maps import LAYOUTS

from test_support import HeadlessTest


NO_RANDOM = {"random_motes": False, "random_shades": False, "random_drifters": False}


class PhaseTwoContractTest(HeadlessTest):
    def test_each_night_manifest_and_layout(self):
        for night, lamps in ((1, 5), (2, 6), (3, 7)):
            with self.subTest(night=night):
                first, start, end = self.run_game(0, night=night)
                self.assertEqual(first["night"], night)
                self.assertEqual(first["motes_active"], 20)
                self.assertEqual(len(first["lanterns"]), lamps)
                expected = {tuple(round(value, 3) for value in pos) for pos in LAYOUTS[night].motes}
                actual = {tuple(m["pos"]) for m in first["motes"]}
                self.assertEqual(len(actual), 20)
                self.assertTrue(actual <= expected)
                self.assertEqual(start, {"type": "event", "tick": 0, "name": "night_start", "data": {"night": night}})
                self.assertTrue({"wind", "drifters", "charms"}.issubset(first))
                self.assertTrue({"vel", "grounded", "invuln", "charm_s", "dash_cd_s", "pulse_cd_s"}.issubset(first["player"]))
                self.assertEqual(first["time_left_s"], TUNING[f"night{night}_duration_s"])
                self.assertEqual(end["ticks"], 0)

    def test_pause_freezes_sim_tick_cooldowns_and_spawn(self):
        scenario = {"random_motes": False, "random_shades": False, "player": {"charm_ticks": 60},
                    "charms": [{"id": "C1", "available": False, "respawn_ticks": 2000}]}
        pause = [{"tick": 1, "pause": True}, {"tick": 59, "pause": False},
                 {"tick": 1202, "pause": True, "move": [1, 0]}]
        records = self.run_game(1204, scenario, pause, every=1, night=2)
        snapshots = self.snapshots(records)
        a, b = snapshots[1], snapshots[1202]
        self.assertEqual(b["state"], "paused")
        self.assertEqual(a["sim_tick"], b["sim_tick"])
        self.assertEqual(a["time_left_s"], b["time_left_s"])
        self.assertEqual(a["player"], b["player"])
        self.assertEqual(a["charms"], b["charms"])
        self.assertEqual(b["drifters"], [])
        self.assertEqual(snapshots[1204]["sim_tick"], 3)
        self.assertEqual([x["tick"] for x in self.events(records, "paused")], [2])
        self.assertEqual([x["tick"] for x in self.events(records, "resumed")], [1203])

    def test_dash_duration_speed_and_lockout(self):
        frames = [{"tick": 0, "dash": True}, {"tick": 1, "dash": False},
                  {"tick": 2, "dash": True}, {"tick": 3, "dash": False}]
        duration = ticks(TUNING["dash_duration_s"])
        records = self.run_game(duration + 2, NO_RANDOM, frames)
        snapshots = self.snapshots(records)
        self.assertEqual(self.events(records, "dash"), [{"type": "event", "tick": 1, "name": "dash", "data": {}}])
        self.assertAlmostEqual(snapshots[duration]["player"]["pos"][2],
                               duration * TUNING["dash_speed"] / HZ, places=3)
        self.assertEqual(snapshots[duration + 1]["player"]["vel"][2], 0)

    def test_charm_pick_speed_dash_and_respawn(self):
        scenario = {**NO_RANDOM, "player": {"pos": [35, 0, 0], "dash_cd_ticks": 80}}
        frames = [{"tick": 1, "move": [-1, 0]}, {"tick": 2, "dash": True},
                  {"tick": 3, "dash": False}, {"tick": 4, "dash": True},
                  {"tick": 5, "dash": False}, {"tick": 15, "dash": True}]
        records = self.run_game(17, scenario, frames, night=2)
        snapshots = self.snapshots(records)
        self.assertEqual(self.events(records, "charm_picked")[0]["data"], {"charm_id": "C1", "charm_ticks": 600})
        self.assertEqual(snapshots[1]["charms"][0], {"id": "C1", "available": False, "respawn_s": 45})
        self.assertAlmostEqual(snapshots[2]["player"]["vel"][0], -7.2, places=3)
        self.assertEqual([event["tick"] for event in self.events(records, "dash")], [3, 16])
        respawn = self.run_game(2, {**NO_RANDOM, "charms": [{"id": "C1", "available": False, "respawn_ticks": 2}]}, night=2)
        self.assertFalse(self.snapshots(respawn)[1]["charms"][0]["available"])
        self.assertTrue(self.snapshots(respawn)[2]["charms"][0]["available"])

    def test_bamboo_bridge_and_cross_island_launch(self):
        bridge = {**NO_RANDOM, "player": {"pos": [26, 0, 0]}}
        steps = math.ceil(18.1 * HZ / TUNING["player_speed"])
        walk = self.run_game(steps, bridge, [{"tick": 0, "move": [1, 0]}], every=steps, night=2)
        self.assertGreater(self.snapshots(walk)[-1]["player"]["pos"][0], 44)
        self.assertFalse(self.events(walk, "player_hit"))
        pad = {**NO_RANDOM, "player": {"pos": [20, 0, 18]}}
        # Westward input cannot overwrite the eastward launch.
        launch = self.run_game(84, pad, [{"tick": 0, "move": [-1, 0]}], night=2)
        snapshots = self.snapshots(launch)
        self.assertAlmostEqual(math.hypot(snapshots[30]["player"]["vel"][0], snapshots[30]["player"]["vel"][2]), 24, places=2)
        self.assertTrue(snapshots[-1]["player"]["grounded"])
        x, y, z = snapshots[-1]["player"]["pos"]
        self.assertLess(math.hypot(x - 70, z), 28)
        self.assertEqual(y, 0)

    def test_night_three_ramp_cliff_and_upper_launch(self):
        first = {**NO_RANDOM, "player": {"pos": [0, 0, -9]}}
        cliff = self.run_game(30, first, [{"tick": 0, "move": [0, 1]}], night=3)
        self.assertLessEqual(self.snapshots(cliff)[-1]["player"]["pos"][2], -8)
        ramp_x, ramp_z = math.cos(math.pi / 6), .5
        ramp = {**NO_RANDOM, "player": {"pos": [31 * ramp_x, 0, 31 * ramp_z]}}
        steps = math.ceil(9 * HZ / TUNING["player_speed"])
        climb = self.run_game(steps, ramp, [{"tick": 0, "move": [-ramp_x, -ramp_z]}], night=3)
        self.assertEqual(self.snapshots(climb)[-1]["player"]["pos"][1], 3)
        pad = {**NO_RANDOM, "player": {"pos": [0, 3, 13]}}
        launch = self.run_game(65, pad, night=3)
        self.assertEqual(self.snapshots(launch)[-1]["player"]["pos"][1], 6)
        self.assertTrue(self.snapshots(launch)[-1]["player"]["grounded"])
        tower = self.run_game(75, {**NO_RANDOM, "player": {"pos": [0, 6, 6]}},
                              [{"tick": 0, "move": [0, -1]}], night=3)
        self.assertGreaterEqual(self.snapshots(tower)[-1]["player"]["pos"][2], 2)

    def test_drifter_steals_before_shade_and_returns_motes_when_pulsed(self):
        scenario = {**NO_RANDOM, "player": {"carried": 8}, "drifters": [{"id": "D4", "pos": [0, 0, 0]}],
                    "shades": [{"id": "S10", "pos": [0, 0, 0]}, {"id": "S2", "pos": [0, 0, 0]}]}
        records = self.run_game(3, scenario, [{"tick": 1, "pulse": True}], night=2)
        steal = self.events(records, "drifter_steal")[0]
        hit = self.events(records, "player_hit")[0]
        self.assertLess(records.index(steal), records.index(hit))
        self.assertEqual(steal["data"], {"drifter_id": "D4", "amount": 3, "carried": 5})
        self.assertEqual(hit["data"]["id"], "S2")
        self.assertEqual(self.events(records, "drifter_drop")[0]["data"], {"drifter_id": "D4", "amount": 3})
        self.assertGreater(len([m for m in self.snapshots(records)[2]["motes"] if m["kind"] == "dropped"]), 0)
        self.assertEqual(self.snapshots(records)[2]["drifters"][0]["stolen"], 0)

    def test_drifter_is_not_blocked_by_safety_or_invulnerability(self):
        setup = {**NO_RANDOM, "player": {"carried": 5, "invuln_ticks": 100},
                 "lanterns": [{"id": "L1", "pos": [0, 0, 0], "lit": True}],
                 "drifters": [{"pos": [0, 0, 0]}]}
        results = self.run_game(1, setup, night=2)
        self.assertEqual(self.events(results, "drifter_steal")[0]["data"]["carried"], 2)
        self.assertFalse(self.events(results, "player_hit"))
        setup["drifters"][0]["state"] = "chase"
        fled = self.run_game(1, setup, [{"tick": 0, "pulse": True}], night=2)
        self.assertEqual(self.snapshots(fled)[-1]["drifters"][0]["state"], "flee")
        self.assertFalse(self.events(fled, "drifter_steal"))

    def test_spawn_ticks_and_pause_do_not_change_sim_schedule(self):
        n1 = self.run_game(300, {"random_motes": False}, every=300)
        self.assertEqual([event["tick"] for event in self.events(n1, "shade_spawned")], [300, 300])
        self.assertTrue(all(s["state"] == "spawning" for s in self.snapshots(n1)[-1]["shades"]))
        scenario = {"random_shades": False, "random_motes": False}
        n2 = self.run_game(2400, scenario, every=1200, night=2)
        self.assertEqual([len(s["drifters"]) for s in self.snapshots(n2)], [0, 1, 2])
        self.assertEqual([d["id"] for d in self.snapshots(n2)[-1]["drifters"]], ["D1", "D2"])

    def test_wind_uses_gameplay_ticks_and_adds_two_m_per_second(self):
        scenario = {**NO_RANDOM, "player": {"pos": [0, 0, -30]}}
        records = self.run_game(1801, scenario, every=1800, night=3)
        state = self.snapshots(records)[-1]
        self.assertEqual(state["sim_tick"], 1800)
        self.assertTrue(state["wind"]["active"])
        vx, _, vz = state["player"]["vel"]
        self.assertAlmostEqual(math.hypot(vx, vz), 2, places=2)
        draft = self.run_game(1801, {**scenario, "wind_enabled": False}, every=1800, night=3)
        self.assertFalse(self.snapshots(draft)[-1]["wind"]["active"])

    def test_v11_validation_and_unknown_lantern_for_night(self):
        for setup in ({"player": {"charm_ticks": -1}}, {"drifters": [{"pos": [0, 0, 0], "state": "wrong"}]},
                      {"lanterns": [{"id": "L7"}]}, {"wind_enabled": 1}):
            self.run_game(1, setup, expected=2, night=2)
        self.run_game(1, NO_RANDOM, [{"tick": 0, "pause": 1}], expected=2)
        self.run_game(1, {"lanterns": [{"id": "L7", "lit": True}]}, night=3)

    def test_each_night_can_finish_and_scores_only_deposited_motes(self):
        for night, layout in LAYOUTS.items():
            with self.subTest(night=night):
                cost = TUNING["lantern_cost"]
                pos = list(layout.lanterns[0])
                scenario = {**NO_RANDOM, "time_left_s": 20,
                            "player": {"pos": pos, "carried": cost - 1}, "motes": [pos],
                            "lanterns": [{"id": "L" + str(i), "lit": True}
                                         for i in range(2, len(layout.lanterns) + 1)]}
                records = self.run_game(60, scenario, [{"tick": 0, "interact": True}], night=night)
                score = cost * 10 + 100 + 19 * 2 + TUNING["flames"] * 50
                self.assertEqual(records[-1], {"type": "end", "ticks": 1, "state": "won", "score": score})

    def test_air_dash_holds_height_for_twelve_ticks_and_sets_90_tick_cooldown(self):
        frames = [{"tick": 0, "jump": True}, {"tick": 6, "dash": True}]
        states = self.snapshots(self.run_game(19, NO_RANDOM, frames))
        height = states[6]["player"]["pos"][1]
        self.assertEqual(states[7]["player"]["dash_cd_s"], 1.5)
        self.assertTrue(all(state["player"]["pos"][1] == height for state in states[7:19]))
        self.assertEqual(states[18]["player"]["pos"][2], 2.8)
        self.assertGreater(states[19]["player"]["pos"][1], height)
        self.assertFalse(states[7]["player"]["invuln"])

    def test_motes_spawn_one_at_tick_240_and_stop_at_thirty(self):
        records = self.run_game(2640, {"random_shades": False, "wind_enabled": False}, every=240, night=3)
        counts = [state["motes_active"] for state in self.snapshots(records)]
        self.assertEqual(counts, list(range(20, 31)) + [30])

    def test_pulse_uses_3d_center_and_refreshes_existing_stun(self):
        scenario = {**NO_RANDOM, "player": {"carried": 3},
                    "shades": [{"id": "S1", "pos": [0, 6, 0]}, {"id": "S2", "pos": [0, 0.8, 0],
                               "state": "stunned", "state_ticks_left": 2}]}
        records = self.run_game(120, scenario, [{"tick": 0, "pulse": True}])
        states = self.snapshots(records)
        self.assertEqual([e["data"]["id"] for e in self.events(records, "shade_stunned")], ["S2"])
        self.assertEqual(states[15]["shades"][1]["pos"], [4, .8, 0])
        self.assertEqual(states[120]["shades"][1]["state"], "stunned")
        self.assertEqual(states[1]["player"]["pulse_cd_s"], 3)
        self.assertEqual(records[-1]["score"], 5)

    def test_hit_drops_half_in_ring_with_ttl_and_applies_recoil(self):
        scenario = {**NO_RANDOM, "player": {"carried": 7}, "shades": [{"pos": [0, .8, 0]}]}
        records = self.run_game(61, scenario)
        states = self.snapshots(records)
        self.assertEqual(states[1]["player"]["carried"], 4)
        self.assertEqual(len(states[1]["motes"]), 3)
        for mote in states[1]["motes"]:
            self.assertEqual((mote["kind"], mote["ttl_s"]), ("dropped", 8))
            self.assertGreaterEqual(math.hypot(mote["pos"][0], mote["pos"][2]), 1.5)
            self.assertLessEqual(math.hypot(mote["pos"][0], mote["pos"][2]), 2.5)
        self.assertEqual(states[61]["shades"][0]["pos"], [2, .8, 0])
        self.assertEqual(states[60]["shades"][0]["state"], "recoil")
        self.assertEqual(states[61]["shades"][0]["state"], "wander")
        self.assertTrue(states[61]["player"]["invuln"])

    def test_timeout_priority_favours_surviving_win_and_no_flames_over_win(self):
        lamps = [{"id": "L" + str(index), "lit": True} for index in range(1, 6)]
        win = self.run_game(1, {**NO_RANDOM, "time_left_s": 1 / HZ, "lanterns": lamps})
        self.assertEqual(win[-1]["state"], "won")
        no_flames = self.run_game(1, {**NO_RANDOM, "time_left_s": 1 / HZ, "lanterns": lamps, "player": {"flames": 0}})
        self.assertEqual(self.events(no_flames, "game_lost")[0]["data"]["reason"], "no_flames")
        dawn = self.run_game(1, {**NO_RANDOM, "time_left_s": 1 / HZ})
        self.assertEqual(self.events(dawn, "game_lost")[0]["data"]["reason"], "dawn")

    def test_shade_detection_hysteresis_and_night_three_speed(self):
        scenario = {**NO_RANDOM, "player": {"pos": [0, 0, -20]}, "shades": [
            {"id": "near", "pos": [11, .8, -20], "state": "wander"},
            {"id": "middle", "pos": [15, .8, -20], "state": "chase"},
            {"id": "far", "pos": [19, .8, -20], "state": "chase"}]}
        records = self.run_game(1, scenario, night=3)
        end = self.snapshots(records)[-1]["shades"]
        self.assertEqual([s["state"] for s in end], ["chase", "chase", "wander"])
        self.assertAlmostEqual(end[0]["pos"][0], 11 - 4.5 / HZ, places=3)
