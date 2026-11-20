"""Loopback server for the browser renderer."""
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import secrets
from threading import Lock, Timer
import webbrowser

from .contract import integer, validate_controls
from .game import DEFAULT_INPUT, Game, ROOT, TUNING


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
        self.end_headers()
        self.wfile.write(body)

    def game_view(self, game):
        return dict(snapshot=game.snapshot(), wind_warning=game.wind_warning)

    def do_POST(self):
        if self.path not in ("/api/start", "/api/step"):
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
                if self.path == "/api/start":
                    night = request.get("night", 1)
                    if not integer(night, 1, 3):
                        raise ValueError("Đêm phải là 1, 2 hoặc 3")
                    seed = self.server.seed if self.server.seed is not None else secrets.randbits(32)
                    session = request.get("session")
                    if not isinstance(session, str) or session not in self.server.games:
                        session = secrets.token_urlsafe(18)
                    game = self.server.games[session] = Game(seed, night=night)
                    if len(self.server.games) > 32:
                        del self.server.games[next(iter(self.server.games))]
                    result = dict(session=session, tuning=TUNING, layout=game.layout.view(), **self.game_view(game))
                else:
                    session = request.get("session")
                    if not isinstance(session, str) or session not in self.server.games:
                        self.send_json({"error": "Phiên chơi đã hết hạn"}, HTTPStatus.NOT_FOUND)
                        return
                    game = self.server.games[session]
                    ticks = request.get("ticks")
                    controls = request.get("controls")
                    if not integer(ticks, 1, 12) or not isinstance(controls, dict):
                        raise ValueError("Input không hợp lệ")
                    validate_controls(controls)
                    controls = {key: controls.get(key, default) for key, default in DEFAULT_INPUT.items()}
                    events = []
                    for _ in range(ticks):
                        events.extend(game.step(controls))
                    result = dict(events=events, **self.game_view(game))
        except (ValueError, OverflowError) as error:
            self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
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
