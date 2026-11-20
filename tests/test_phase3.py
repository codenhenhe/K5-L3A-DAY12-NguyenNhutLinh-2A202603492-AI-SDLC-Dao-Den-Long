from lantern.game import Game, HZ

from test_support import HeadlessTest

NO_RANDOM = dict(random_motes=False, random_shades=False, random_drifters=False, wind_enabled=False)


def lantern(number, fuel=None, **values):
    override = {"id": f"L{number}", **values}
    if fuel is not None:
        override.update(lit=True, fuel=fuel)
    return override


def drainer(name, pos, target="L1"):
    return {"id": name, "state": "drain", "pos": pos, "target_lantern_id": target}


class PhaseThreeContractTest(HeadlessTest):
    def test_fuel_defaults_and_decays_exactly_to_extinction(self):
        setup = {**NO_RANDOM, "time_left_s": 110, "lanterns": [lantern(1, lit=True), lantern(2, 1)]}
        records = self.run_game(6000, setup, every=60)
        frames = self.snapshots(records)
        self.assertEqual(frames[0]["lanterns"][0]["fuel"], 100.0)
        self.assertEqual(frames[0]["player"]["capacity"], 10)
        self.assertEqual(frames[1]["lanterns"][0]["fuel"], 99.0)
        self.assertEqual(frames[1]["lanterns"][1]["fuel"], 0.0)
        self.assertEqual(frames[-1]["lanterns"][0]["deposited"], 0)
        self.assertTrue(frames[-1]["lanterns"][0]["ever_lit"])
        self.assertEqual([(e["tick"], e["data"]) for e in self.events(records, "lantern_out")],
                         [(60, {"lantern_id": "L2"}), (6000, {"lantern_id": "L1"})])

    def test_refuel_ceil_tie_break_and_clamp(self):
        setup = {**NO_RANDOM, "player": {"carried": 3},
                 "lanterns": [lantern(1, 80, pos=[-1, 0, 0]), lantern(2, pos=[1, 0, 0])]}
        records = self.run_game(1, setup, [{"tick": 0, "interact": True}])
        self.assertEqual(self.events(records, "refuel")[0]["data"],
                         {"lantern_id": "L1", "amount": 3, "fuel": 100.0})
        self.assertEqual(records[-1]["score"], 15)
        self.assertEqual(self.snapshots(records)[-1]["player"]["carried"], 0)
        self.assertFalse(self.events(records, "lantern_lit"))

    def test_preset_empty_lit_lamp_emits_out_on_first_gameplay_tick(self):
        records = self.run_game(1, {**NO_RANDOM, "lanterns": [lantern(1, 0)]})
        start, after = self.snapshots(records)
        self.assertTrue(start["lanterns"][0]["lit"])
        self.assertFalse(after["lanterns"][0]["lit"])
        self.assertTrue(after["lanterns"][0]["ever_lit"])
        self.assertEqual(self.events(records, "lantern_out"),
                         [{"type": "event", "tick": 1, "name": "lantern_out", "data": {"lantern_id": "L1"}}])

    def test_full_lamp_at_selection_is_skipped(self):
        # After ordinary tick decay a full lamp has space. Exercise the
        # selection rule with exactly full fuel at the interaction stage.
        game = Game(12, {**NO_RANDOM, "player": {"carried": 1},
                         "lanterns": [lantern(1, 100, pos=[0, 0, 0]), lantern(2, pos=[1, 0, 0])]})
        game.deposit()
        self.assertEqual(game.lanterns[0].fuel, 100.0)
        self.assertEqual(game.lanterns[1].deposited, 1)
        self.assertEqual([event["name"] for event in game.events], ["lantern_deposited"])

    def test_expire_then_relight_on_same_tick_and_increase_capacity(self):
        setup = {**NO_RANDOM, "player": {"carried": 5, "successful_lights": 4},
                 "lanterns": [lantern(1, 1 / HZ, pos=[0, 0, 0]), lantern(2, lit=True)]}
        records = self.run_game(1, setup, [{"tick": 0, "interact": True}])
        before, after = self.snapshots(records)
        self.assertEqual((before["player"]["capacity"], after["player"]["capacity"]), (18, 20))
        lamp = after["lanterns"][0]
        self.assertEqual((lamp["fuel"], lamp["relit_count"], lamp["ever_lit"], lamp["deposited"]), (100.0, 1, True, 5))
        self.assertEqual([e["name"] for e in records if e["type"] == "event"],
                         ["night_start", "lantern_out", "lantern_deposited", "lantern_lit"])
        self.assertEqual(self.events(records, "lantern_lit")[0]["data"], {"id": "L1", "relight": True})
        self.assertEqual(records[-1]["score"], 65)

    def test_capacity_caps_and_allows_pickup_above_initial_ten(self):
        setup = {**NO_RANDOM, "player": {"successful_lights": 100, "carried": 19},
                 "motes": [[0, 0, 0], [0, 0, 0]]}
        snapshots = self.snapshots(self.run_game(1, setup))
        self.assertEqual(snapshots[0]["player"]["capacity"], 20)
        self.assertEqual(snapshots[1]["player"]["carried"], 20)
        self.assertEqual(snapshots[1]["motes_active"], 1)

    def test_drain_stacks_and_emits_at_sixty_active_ticks(self):
        setup = {**NO_RANDOM, "lanterns": [lantern(1, 29, pos=[12, 0, 0])],
                 "shades": [drainer("S1", [12, .8, 0]), drainer("S2", [13, .8, 0])]}
        frames = [{"tick": 30, "pause": True}, {"tick": 31, "pause": False}, {"tick": 36, "pause": True}]
        records = self.run_game(66, setup, frames)
        snapshots = self.snapshots(records)
        self.assertEqual(snapshots[30]["lanterns"][0]["fuel"], 23.5)
        self.assertEqual(snapshots[36]["lanterns"][0]["fuel"], 23.5)
        self.assertEqual(snapshots[36]["sim_tick"], 30)
        self.assertEqual(snapshots[-1]["lanterns"][0]["fuel"], 18.0)
        self.assertEqual([(e["tick"], e["data"]) for e in self.events(records, "fuel_drain")],
                         [(66, {"lantern_id": "L1", "shade_id": "S1", "fuel": 18.0}),
                          (66, {"lantern_id": "L1", "shade_id": "S2", "fuel": 18.0})])
        self.assertEqual(snapshots[-1]["shades"][0]["pos"], [12, .8, 0])

    def test_wander_chooses_nearest_weak_on_tie_and_chase_does_not_switch(self):
        setup = {**NO_RANDOM, "player": {"pos": [0, 0, -12]},
                 "lanterns": [lantern(1, lit=True), lantern(2, 25, pos=[2, 0, 0]),
                              lantern(3, 25, pos=[-2, 0, 0])],
                 "shades": [{"id": "S1", "state": "wander", "pos": [0, .8, 0]},
                            {"id": "S2", "state": "chase", "pos": [0, .8, 0]}]}
        states = self.snapshots(self.run_game(2, setup))
        self.assertEqual(states[1]["shades"][0]["state"], "drain")
        self.assertEqual(states[1]["shades"][1]["state"], "chase")
        self.assertEqual(states[2]["lanterns"][1]["fuel"], 24.9)
        self.assertEqual(states[2]["lanterns"][2]["fuel"], 25.0)

    def test_drain_leaves_for_player_within_six_or_invalid_target(self):
        for player_x, shade_x, fuel, expected in ((6, 12, 20, "chase"), (0, 15, 20, "wander"),
                                                  (0, 12, 0.1, "wander")):
            with self.subTest(player_x=player_x, shade_x=shade_x, fuel=fuel):
                setup = {**NO_RANDOM, "player": {"pos": [player_x, 0, 0]},
                         "lanterns": [lantern(1, fuel, pos=[12, 0, 0])],
                         "shades": [drainer("S1", [shade_x, .8, 0])]}
                last = self.snapshots(self.run_game(1, setup))[-1]
                self.assertEqual(last["shades"][0]["state"], expected)

    def test_at_thirty_zone_is_safe_and_refuel_repel_takes_at_most_thirty_ticks(self):
        setup = {**NO_RANDOM, "player": {"carried": 1},
                 "lanterns": [lantern(1, 25, pos=[0, 0, 0])],
                 "shades": [drainer("S1", [0, .8, 0])]}
        records = self.run_game(30, setup, [{"tick": 0, "interact": True}])
        snapshots = self.snapshots(records)
        self.assertEqual(snapshots[1]["shades"][0]["state"], "wander")
        self.assertLess(snapshots[1]["shades"][0]["pos"][0], 6)
        self.assertGreater(snapshots[-1]["shades"][0]["pos"][0], 6)
        self.assertFalse(self.events(records, "player_hit"))

        initial = {**NO_RANDOM, "lanterns": [lantern(1, 30 + 1 / HZ, pos=[0, 0, 0])],
                   "shades": [{"pos": [0, .8, 0]}]}
        records = self.run_game(1, initial)
        self.assertEqual(self.snapshots(records)[1]["lanterns"][0]["fuel"], 30.0)
        self.assertFalse(self.events(records, "player_hit"))

    def test_pulse_scoring_clears_drain_without_reducing_its_bonus(self):
        setup = {**NO_RANDOM, "player": {"pos": [0, 0, 0], "carried": 3},
                 "lanterns": [lantern(1, 25, pos=[3, 0, 0])],
                 "shades": [drainer("S1", [3, .8, 0]),
                            {"id": "S2", "pos": [0, .8, 4], "state": "stunned", "state_ticks_left": 5}]}
        records = self.run_game(61, setup, [{"tick": 0, "pulse": True}])
        self.assertEqual(records[-1]["score"], 20)
        self.assertEqual(len(self.events(records, "shade_stunned")), 2)
        self.assertFalse(self.events(records, "fuel_drain"))
        self.assertEqual(self.snapshots(records)[-1]["lanterns"][0]["fuel"], 23.9)

    def test_dawn_requires_exact_threshold_and_uses_unrounded_fuel_for_score(self):
        for night, required in ((1, 3), (2, 4), (3, 5)):
            for count in (required - 1, required):
                with self.subTest(night=night, count=count):
                    setup = {**NO_RANDOM, "time_left_s": 1 / HZ,
                             "lanterns": [lantern(i, 5) for i in range(1, count + 1)]}
                    records = self.run_game(1, setup, night=night)
                    won = count >= required
                    event = self.events(records, "game_over")[0]
                    self.assertEqual(event["data"]["reason"], "dawn_survived" if won else "dawn")
                    self.assertEqual(records[-1]["score"], required * 54 + 150 if won else 0)

    def test_final_tick_extinction_and_fatal_hit_take_effect_before_win(self):
        lamps = [lantern(1, 1 / HZ), lantern(2, 100), lantern(3, 100)]
        setup = {**NO_RANDOM, "time_left_s": 1 / HZ, "lanterns": lamps}
        records = self.run_game(1, setup)
        self.assertEqual(self.events(records, "lantern_out")[0]["tick"], 1)
        self.assertEqual(self.events(records, "game_over")[0]["data"]["reason"], "dawn")
        lamps[0]["fuel"] = 100
        setup.update(player={"flames": 1}, shades=[{"pos": [0, .8, 0]}])
        fatal = self.run_game(1, setup)
        self.assertEqual(self.events(fatal, "player_hit")[0]["tick"], 1)
        self.assertEqual(self.events(fatal, "game_over")[0]["data"]["reason"], "no_flames")

    def test_v12_invalid_scenario_fields(self):
        for scenario in ({"player": {"successful_lights": -1}}, {"player": {"carried": 11}},
                         {"lanterns": [lantern(1, 101)]}, {"lanterns": [lantern(1, ever_lit=1)]},
                         {"shades": [drainer("S1", [0, .8, 0], "L9")]}):
            with self.subTest(scenario=scenario):
                self.run_game(1, scenario, expected=2)
