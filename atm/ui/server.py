"""
ATM Local HTTP Server - phục vụ giao diện web và API.
Thay thế hoàn toàn pywebview để tránh lỗi COM/WebView2.
"""
import json
import os
import mimetypes
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from atm.utils.logger import get_logger

logger = get_logger(__name__, "launcher.log")


class ATMHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler cho ATM."""
    
    api = None  # Được gán từ create_server()
    web_dir = os.path.join(os.path.dirname(__file__), 'web')

    def do_GET(self):
        if self.path.startswith('/api/'):
            self._handle_api_get()
        else:
            self._serve_static()

    def do_POST(self):
        self._handle_api_post()

    # ============ API GET ============
    def _handle_api_get(self):
        if self.path == '/api/games':
            self._json_response(self.api.get_games())
        elif self.path == '/api/languages':
            self._json_response(self.api.get_languages())
        else:
            self._json_response({"error": "Not found"}, 404)

    # ============ API POST ============
    def _handle_api_post(self):
        body = self._read_body()

        if self.path == '/api/games/add':
            result = self.api.add_game()
            self._json_response(result or {"status": "cancelled"})

        elif self.path == '/api/games/start':
            result = self.api.start_game(body.get('game_id', ''))
            self._json_response(result)

        elif self.path == '/api/games/stop':
            result = self.api.stop_game(body.get('game_id', ''))
            self._json_response(result)

        elif self.path == '/api/games/delete':
            result = self.api.delete_game(body.get('game_id', ''))
            self._json_response(result)

        elif self.path == '/api/games/update-lang':
            result = self.api.update_game_lang(
                body.get('game_id', ''),
                body.get('input_lang', 'auto'),
                body.get('output_lang', 'vi')
            )
            self._json_response(result)

        elif self.path == '/api/shutdown':
            self._json_response({"status": "shutting_down"})
            threading.Thread(target=self.server.shutdown, daemon=True).start()

        else:
            self._json_response({"error": "Not found"}, 404)

    # ============ Static File Server ============
    def _serve_static(self):
        path = self.path.split('?')[0].lstrip('/')
        if not path:
            path = 'index.html'

        filepath = os.path.join(self.web_dir, path)

        # Bảo vệ: không cho truy cập ngoài web_dir
        filepath = os.path.normpath(filepath)
        if not filepath.startswith(os.path.normpath(self.web_dir)):
            self.send_error(403)
            return

        if os.path.isfile(filepath):
            mime_type = mimetypes.guess_type(filepath)[0] or 'application/octet-stream'
            with open(filepath, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', mime_type)
            self.send_header('Content-Length', len(content))
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_error(404)

    # ============ Helpers ============
    def _json_response(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        if length > 0:
            try:
                return json.loads(self.rfile.read(length))
            except (json.JSONDecodeError, Exception):
                return {}
        return {}

    def log_message(self, format, *args):
        """Tắt log HTTP mặc định, chỉ dùng logger riêng."""
        pass


def create_server(port, api):
    """Tạo HTTP server với API backend đã khởi tạo."""
    ATMHandler.api = api
    server = ThreadingHTTPServer(('127.0.0.1', port), ATMHandler)
    server.daemon_threads = True
    return server
