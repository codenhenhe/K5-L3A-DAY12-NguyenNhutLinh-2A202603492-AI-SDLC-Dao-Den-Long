"""CLI entry point for the game and the grader."""
import argparse
import json
import sys

from .contract import read_inputs, read_scenario
from .game import DEFAULT_INPUT, Game


def headless(args):
    try:
        scenario = read_scenario(args.scenario, args.night) if args.scenario else None
        frames = iter(read_inputs(args.inputs) if args.inputs else ())
    except (OSError, ValueError, OverflowError) as error:
        print(error, file=sys.stderr)
        return 2
    try:
        game = Game(args.seed, scenario, args.night)
        controls = DEFAULT_INPUT.copy()
        frame = next(frames, None)
        with open(args.out, "w", encoding="utf-8", newline="\n") as output:
            def emit(data):
                print(json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False),
                      file=output)

            emit(game.snapshot())
            emit(dict(type="event", tick=0, name="night_start", data={"night": args.night}))
            for tick in range(args.ticks):
                if frame and frame["tick"] == tick:
                    controls.update((key, frame[key]) for key in DEFAULT_INPUT if key in frame)
                    frame = next(frames, None)
                for event in game.step(controls):
                    emit(event)
                if game.tick % args.snapshot_every == 0:
                    emit(game.snapshot())
                if game.state in ("won", "lost"):
                    break
            emit(game.end())
    except (OSError, ValueError, OverflowError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


def main():
    cli = argparse.ArgumentParser(prog="python3 -m lantern")
    commands = cli.add_subparsers(dest="command", required=True)
    cli_headless = commands.add_parser("headless")
    cli_headless.add_argument("--seed", type=int, required=True)
    cli_headless.add_argument("--night", type=int, required=True, choices=(1, 2, 3))
    cli_headless.add_argument("--scenario")
    cli_headless.add_argument("--inputs")
    cli_headless.add_argument("--ticks", type=int, required=True)
    cli_headless.add_argument("--out", required=True)
    cli_headless.add_argument("--snapshot-every", type=int, default=10)
    cli_play = commands.add_parser("play")
    cli_play.add_argument("--port", type=int, default=8765)
    cli_play.add_argument("--no-browser", action="store_true")
    cli_play.add_argument("--seed", type=int)
    args = cli.parse_args()
    if args.command == "play":
        from .server import play
        return play(args.port, args.no_browser, args.seed)
    if args.ticks < 0 or args.snapshot_every <= 0:
        cli_headless.error("expected --ticks >= 0 and --snapshot-every > 0")
    return headless(args)


if __name__ == "__main__":
    raise SystemExit(main())
