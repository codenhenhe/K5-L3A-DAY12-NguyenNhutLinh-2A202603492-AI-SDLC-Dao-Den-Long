"""Loopback server for the browser renderer."""
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from contextlib import suppress
from dataclasses import dataclass, field
import json
import secrets
import sqlite3
from threading import Lock, Timer
import webbrowser

from .contract import integer, validate_controls
from .game import DEFAULT_INPUT, Game, ROOT, TUNING
from . import leaderboard


@dataclass
class Campaign:
    seed: int
    practice_night: int | None = None
    game: Game = field(init=False)
    score: int = 0
    nights_won: int = 0
    saved: bool = False

    def __post_init__(self):
        night = self.practice_night or 1
        self.game = Game(self.seed + night - 1, night=night)

    def start(self, night):
        current = self.game.night
        practice = self.practice_night is not None
        retry = night == current and (practice or self.game.state != "won")
        advance = not practice and night == current + 1 and self.game.state == "won"
        if not (retry or advance):
            raise ValueError("Hãy bắt đầu lại hoặc chơi Đêm kế tiếp.")
        self.game = Game(self.seed + night - 1, night=night)
        self.saved = False

    def step(self, ticks, controls):
        events = []
        for _ in range(ticks):
            events.extend(self.game.step(controls))
            if self.game.state in ("won", "lost"):
                if (self.practice_night is None and self.game.state == "won"
                        and self.nights_won < self.game.night):
                    self.nights_won += 1
                    self.score += self.game.score
                break
        return events

    def save_score(self, name):
        if self.practice_night is not None:
            raise ValueError("Chế độ luyện tập không lưu điểm xếp hạng.")
        eligible = self.game.state == "lost" or (self.game.state == "won" and self.nights_won == 3)
        if not eligible or self.saved:
            raise ValueError("Điểm chỉ lưu được một lần khi ván đã kết thúc.")
        result = leaderboard.save(name, self.score, self.nights_won, self.seed)
        self.saved = True
        return result

    def summary(self):
        return {"score": self.score, "nights_won": self.nights_won}


class Handler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    disable_nagle_algorithm = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT / "web", **kwargs)

    def log_request(self, code="-", size="-"):
        if self.command != "POST" or str(code) != "200":
            super().log_request(code, size)

    def send_json(self, value, status=HTTPStatus.OK):
        body = json.dumps(value, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        with suppress(BrokenPipeError, ConnectionResetError):
            self.end_headers()
            self.wfile.write(body)

    def game_view(self, game):
        return dict(snapshot=game.snapshot(), wind_warning=game.wind_warning,
                    low_fuel=[lamp.id for lamp in game.lanterns if lamp.weak],
                    receiving_lanterns=[lamp.id for lamp in game.lanterns if lamp.can_receive],
                    required_lights=game.required_lights)

    def do_GET(self):
        if self.path != "/api/leaderboard":
            return super().do_GET()
        try:
            self.send_json({"entries": leaderboard.entries()})
        except (OSError, sqlite3.Error):
            self.send_json({"error": "Không đọc được bảng xếp hạng."}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_POST(self):
        if self.path not in ("/api/start", "/api/step", "/api/leaderboard"):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if self.headers.get_content_type() != "application/json":
            self.send_error(HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 1 <= size <= 4096:
                raise ValueError("Kích thước yêu cầu không hợp lệ")
            request = json.loads(self.rfile.read(size))
            if not isinstance(request, dict):
                raise ValueError("Yêu cầu phải là một JSON object")
            with self.server.game_lock:
                session = request.get("session")
                run = self.server.games.get(session) if isinstance(session, str) else None
                if self.path == "/api/start":
                    night = request.get("night", 1)
                    practice = request.get("practice", False)
                    if not integer(night, 1, 3):
                        raise ValueError("Đêm phải là 1, 2 hoặc 3")
                    if not isinstance(practice, bool):
                        raise ValueError("Chế độ luyện tập phải là giá trị đúng hoặc sai.")
                    if run is None:
                        if not practice and night != 1:
                            raise ValueError("Ván mới bắt đầu ở Đêm 1.")
                        seed = self.server.seed if self.server.seed is not None else secrets.randbits(32)
                        session = secrets.token_urlsafe(18)
                        run = self.server.games[session] = Campaign(seed, practice_night=night if practice else None)
                        if len(self.server.games) > 32:
                            del self.server.games[next(iter(self.server.games))]
                    else:
                        if practice != (run.practice_night is not None):
                            raise ValueError("Hãy bắt đầu ván mới để đổi chế độ.")
                        run.start(night)
                    result = dict(session=session, tuning=TUNING, layout=run.game.layout.view(),
                                  campaign=run.summary(), **self.game_view(run.game))
                else:
                    if run is None:
                        self.send_json({"error": "Phiên chơi đã hết hạn"}, HTTPStatus.NOT_FOUND)
                        return
                    if self.path == "/api/leaderboard":
                        result = {"entries": run.save_score(request.get("name"))}
                    else:
                        ticks = request.get("ticks")
                        controls = request.get("controls")
                        if not integer(ticks, 1, 12) or not isinstance(controls, dict):
                            raise ValueError("Input không hợp lệ")
                        validate_controls(controls)
                        controls = {key: controls.get(key, default) for key, default in DEFAULT_INPUT.items()}
                        events = run.step(ticks, controls)
                        result = dict(events=events, campaign=run.summary(), **self.game_view(run.game))
        except (ValueError, OverflowError) as error:
            self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
            return
        except (OSError, sqlite3.Error):
            self.send_json({"error": "Không lưu được bảng xếp hạng."}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        self.send_json(result)


def play(port, no_browser, seed):
    try:
        with ThreadingHTTPServer(("127.0.0.1", port), Handler) as server:
            server.game_lock = Lock()
            server.games = {}
            server.seed = seed
            url = f"http://127.0.0.1:{server.server_port}"
            print(f"Đảo Đèn Lồng · {url} · Ctrl+C để thoát", flush=True)
            if not no_browser:
                timer = Timer(0.15, webbrowser.open, args=(url,))
                timer.daemon = True
                timer.start()
            server.serve_forever()
    except KeyboardInterrupt:
        return 0
    except OSError as error:
        import sys
        print(error, file=sys.stderr)
        return 1
    return 0
