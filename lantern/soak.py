"""Run consecutive headless nights in one process and report current RSS."""
import gc
import json
import math
import os
from pathlib import Path
import platform
import random
import subprocess
import sys
from time import perf_counter

from .game import DEFAULT_INPUT, Game, HZ


def rss_mb():
    if platform.system() == "Linux":
        resident_pages = int(Path("/proc/self/statm").read_text().split()[1])
        return resident_pages * os.sysconf("SC_PAGE_SIZE") / (1024 * 1024)
    # ps reports current resident KiB on macOS.
    return int(subprocess.check_output(["ps", "-o", "rss=", "-p", str(os.getpid())], text=True)) / 1024


def random_night(game, seed):
    rng = random.Random(seed)
    controls = DEFAULT_INPUT.copy()
    for tick in range(math.ceil(game.duration * HZ)):
        if tick % 30 == 0:
            angle = rng.random() * math.tau
            controls["move"] = (math.cos(angle), math.sin(angle))
        controls["jump"] = rng.random() < .05
        controls["dash"] = rng.random() < .03
        controls["pulse"] = rng.random() < .02
        controls["interact"] = rng.random() < .10
        game.step(controls)
        if game.state in ("won", "lost"):
            return game.state
    return game.state


def soak(seed, nights, out):
    started = perf_counter()
    results = []
    crashes = 0
    initial_rss = None
    for index in range(nights):
        try:
            game = Game(seed + index, night=index % 3 + 1)
            if index == 0:
                initial_rss = rss_mb()
            results.append(random_night(game, seed + index))
        except Exception as error:
            print(f"Soak night {index + 1}: {error}", file=sys.stderr)
            crashes += 1
            results.append("crashed")
        finally:
            game = None
    gc.collect()
    final_rss = rss_mb()
    result = {"nights": nights, "crashes": crashes, "results": results,
              "mem_start_mb": initial_rss if initial_rss is not None else final_rss,
              "mem_end_mb": final_rss, "duration_s": round(perf_counter() - started, 3)}
    Path(out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 1 if crashes else 0
