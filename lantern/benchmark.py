"""Launch the real Canvas renderer in an isolated Chromium app window."""
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
import platform
from pathlib import Path
from queue import Empty, Queue
import random
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Lock, Thread
from time import perf_counter

from .game import FUEL_MAX, Game, HZ, Mote, ROOT, Shade, TUNING, position


def frame_metrics(samples):
    if not samples or any(type(x) not in (int, float) or not math.isfinite(x) or x <= 0 for x in samples):
        raise ValueError("Benchmark collected no valid frame intervals.")
    count = len(samples)
    ordered = sorted(samples)
    slow = ordered[-max(1, math.ceil(count * .01)):]
    return {
        "avg_fps": round(1000 * count / sum(samples), 3),
        "p1_low_fps": round(1000 * len(slow) / sum(slow), 3),
        "frame_ms_p95": round(ordered[math.ceil(count * .95) - 1], 3),
        "frames": count,
    }


def browser_path():
    candidates = [os.environ.get("LANTERN_BROWSER"), "google-chrome", "chromium", "chromium-browser",
                  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                  "/Applications/Chromium.app/Contents/MacOS/Chromium"]
    return next((path for name in candidates if name and (path := shutil.which(name))), None)


class Scene:
    def __init__(self, seed):
        self.game = Game(seed, {"random_motes": False, "random_shades": False, "wind_enabled": False})
        rng = random.Random(seed)
        for lamp in self.game.lanterns[:3]:
            lamp.lit, lamp.ever_lit = True, True
            lamp.fuel_units = FUEL_MAX
            lamp.deposited = TUNING["lantern_cost"]

        def spread(i, count, height):
            # Equal-area radial bands and golden-angle spacing avoid clumps.
            radius = 39 * math.sqrt((i + .15 + .7 * rng.random()) / count)
            angle = i * math.pi * (3 - math.sqrt(5)) + rng.uniform(-.045, .045)
            return [radius * math.cos(angle), height, radius * math.sin(angle)]

        for i in range(200):
            angle = rng.random() * math.tau
            self.game.shades.append(Shade(f"S{i + 1}", spread(i, 200, .8),
                                          heading=(math.cos(angle), math.sin(angle))))
        for i in range(100):
            self.game.motes.append(Mote(f"M{i + 1}", spread(i, 100, 0)))
        self.ticks = 0

    def advance(self, target):
        for _ in range(target - self.ticks):
            self.game.clear_zones()
            for shade in self.game.shades:
                if shade.evicting:
                    self.game.evict_shade(shade)
                else:
                    self.game.wander_shade(shade, TUNING["shade_speed"])
        self.ticks = target


class BenchmarkHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    disable_nagle_algorithm = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT / "web", **kwargs)

    def log_message(self, *_):
        pass

    def send_json(self, value):
        body = json.dumps(value, separators=(",", ":")).encode()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        server = self.server
        if self.path == "/api/bench-scene":
            game = server.scene.game
            self.send_json({"snapshot": game.snapshot(), "layout": game.layout.view(),
                            "tuning": TUNING, "duration": server.duration})
        elif self.path == "/api/bench-motion":
            with server.lock:
                clock = server.first_frame
                elapsed = min(server.duration + 3, perf_counter() - clock) if clock else 0
                server.scene.advance(int(elapsed * HZ))
                self.send_json([position(shade.pos) for shade in server.scene.game.shades])
        else:
            super().do_GET()

    def do_POST(self):
        if self.path not in ("/api/bench-frame", "/api/bench-result"):
            return self.send_error(HTTPStatus.NOT_FOUND)
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 8 * 1024 * 1024 or self.headers.get_content_type() != "application/json":
                raise ValueError("Invalid benchmark report.")
            data = json.loads(self.rfile.read(size))
            if self.path == "/api/bench-frame":
                if self.server.first_frame is None:
                    self.server.first_frame = perf_counter()
                self.send_json({})
            else:
                if self.server.first_frame is None:
                    raise ValueError("Missing first frame.")
                stats = frame_metrics(data["samples"])
                self.send_json({})
                self.server.results.put_nowait(stats)
        except (ValueError, TypeError, KeyError):
            self.send_error(HTTPStatus.BAD_REQUEST)


def benchmark(seed, duration, out):
    started = perf_counter()
    chrome = browser_path()
    if not chrome:
        print("Benchmark cần Google Chrome hoặc Chromium. Có thể đặt LANTERN_BROWSER.", file=sys.stderr)
        return 1
    try:
        with TemporaryDirectory(prefix="lantern-bench-") as profile, ThreadingHTTPServer(
                ("127.0.0.1", 0), BenchmarkHandler) as server:
            server.scene = Scene(seed)
            server.lock = Lock()
            server.results = Queue(maxsize=1)
            server.first_frame = None
            server.duration = duration
            Thread(target=server.serve_forever, daemon=True).start()
            browser = None
            diagnostics = Path(profile) / "browser.log"
            try:
                url = f"http://127.0.0.1:{server.server_port}/?bench-run=1"
                version = subprocess.check_output([chrome, "--version"], text=True).strip()
                with diagnostics.open("wb") as log:
                    browser = subprocess.Popen([
                        chrome, f"--app={url}", f"--user-data-dir={profile}", "--no-first-run",
                        "--window-size=1280,720", "--force-device-scale-factor=1",
                        "--disable-gpu-vsync", "--disable-frame-rate-limit",
                        "--disable-background-timer-throttling", "--disable-renderer-backgrounding",
                    ], stdout=subprocess.DEVNULL, stderr=log)
                deadline = started + duration + 25
                while True:
                    if browser.poll() is not None:
                        tail = diagnostics.read_text(errors="replace").splitlines()[-5:]
                        detail = "\n" + "\n".join(tail) if tail else ""
                        raise ValueError(f"Chromium thoát trước khi gửi số đo (mã {browser.returncode}).{detail}")
                    if perf_counter() >= deadline:
                        raise ValueError("Hết thời gian chờ số đo. Giữ cửa sổ benchmark ở phía trước.")
                    try:
                        measured = server.results.get(timeout=.25)
                        break
                    except Empty:
                        continue
                result = {"contract_version": "1.3", **measured,
                          "load_ms": round((server.first_frame - started) * 1000),
                          "peak_mem_mb": None, "vsync_off": True,
                          "renderer": f"Đảo Đèn Lồng Canvas 2D / {version}",
                          "os": platform.platform()}
                Path(out).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                print(json.dumps(result, ensure_ascii=False))
                return 0
            finally:
                if browser and browser.poll() is None:
                    browser.terminate()
                    try:
                        browser.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        browser.kill()
                        browser.wait()
                server.shutdown()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(error, file=sys.stderr)
        return 1
