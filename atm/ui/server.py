"""
ATM Local HTTP Server - phục vụ giao diện web và API.
Thay thế hoàn toàn pywebview để tránh lỗi COM/WebView2.
"""
import json
import os
import mimetypes
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from atm.utils.logger import get_logger
from atm.core.lifecycle import ApplicationLifecycle

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
        elif self.path == '/api/settings':
            self._json_response(self.api.get_settings())
        elif self.path.startswith('/api/ping'):
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            client_id = query.get('client_id', ['unknown'])[0]
            ApplicationLifecycle().update_heartbeat(client_id)
            self._json_response({"status": "alive"})
        elif self.path.startswith('/api/games/translation-status'):
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            game_id = query.get('game_id', [''])[0]
            self._json_response(self.api.get_translation_status(game_id))
        elif self.path == '/api/cache/get':
            self._json_response(self.api.get_cache_entries())
        elif self.path.startswith('/api/translation-memory/suggest'):
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            self._json_response(self.api.get_translation_memory_suggestions(
                query.get('game_id', [''])[0],
                query.get('text', [''])[0],
                query.get('category', ['unknown'])[0],
            ))
        elif self.path == '/api/data/stats':
            self._json_response(self.api.get_data_stats())
        elif self.path == '/api/games/play':
            self._parse_post_data()
            game_id = self.post_data.get("game_id", "")
            self._json_response(self.api.play_game(game_id))
        else:
            self._json_response({"error": "Not found"}, 404)

    # ============ API POST ============
    def _handle_api_post(self):
        if ApplicationLifecycle().is_shutting_down():
            self._json_response({"error": "System is shutting down"}, 503)
            return

        body = self._read_body()

        if self.path == '/api/shutdown':
            # Send the response directly here to ensure it's flushed before shutdown
            data = {"status": "shutting_down", "message": "System is shutting down."}
            body = json.dumps(data, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', len(body))
            self.end_headers()
            self.wfile.write(body)
            self.wfile.flush()
            
            # Start a background timer to shut down the server
            import threading
            threading.Timer(0.1, ApplicationLifecycle().request_shutdown).start()
            return

        elif self.path == '/api/games/add':
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
            
        elif self.path == '/api/cache/update':
            result = self.api.update_cache_entry(
                body.get('game_id', ''),
                body.get('key', ''),
                body.get('value', '')
            )
            self._json_response(result)

        elif self.path == '/api/translation-memory/confirm':
            result = self.api.confirm_translation_memory_suggestion(
                body.get('game_id', ''),
                body.get('source_text', ''),
                body.get('translated_text', ''),
                body.get('category', 'unknown'),
            )
            self._json_response(result)

        elif self.path == '/api/settings':
            result = self.api.update_settings(**body)
            self._json_response(result)

        elif self.path == '/api/games/update-settings':
            result = self.api.update_game_settings(
                body.get('game_id', ''),
                body.get('input_lang', None),
                body.get('output_lang', None),
                body.get('translator', None),
                body.get('glossary', None)
            )
            self._json_response(result)

        elif self.path == '/api/shutdown':
            self._json_response({"status": "shutting_down"})
            threading.Thread(target=self.server.shutdown, daemon=True).start()

        elif self.path == '/api/data/clear':
            clear_type = body.get('type')
            if clear_type == 'cache':
                keep_count = body.get('keep', 5000)
                result = self.api.clear_global_cache(keep_count)
            elif clear_type == 'tm':
                result = self.api.clear_global_memory()
            else:
                result = {"status": "error", "message": "Invalid type"}
            self._json_response(result)

        elif self.path == '/api/data/open_folder':
            result = self.api.open_data_folder()
            self._json_response(result)

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
            if filepath.endswith('.css'):
                mime_type = 'text/css'
            elif filepath.endswith('.js'):
                mime_type = 'application/javascript'
            elif filepath.endswith('.html'):
                mime_type = 'text/html'
            else:
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
