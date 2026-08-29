"""
ATM Local HTTP Server - phục vụ giao diện web và API.
Thay thế hoàn toàn pywebview để tránh lỗi COM/WebView2.
"""
import json
import os
import mimetypes

# Fix Windows registry MIME type issues
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('text/html', '.html')

import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from atm.utils.logger import get_logger
from atm.core.lifecycle import ApplicationLifecycle

logger = get_logger(__name__, "launcher.log")


class ATMHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler cho ATM."""
    
    api = None  # Được gán từ create_server()
    # Thư mục gốc chứa UI
    web_dir = os.path.join(os.path.dirname(__file__), 'web')

    def do_GET(self):
        if self.path.startswith('/api/'):
            self._handle_api_get()
        else:
            self._serve_static()

    def do_POST(self):
        self._handle_api_post()

    def do_DELETE(self):
        if self.path.startswith('/api/jobs/'):
            job_id = self.path.split('/')[-1]
            if job_id and job_id != 'jobs':
                self._json_response(self.api.cancel_job(job_id))
            else:
                self._json_response({"error": "Invalid job ID"}, 400)
        else:
            self._json_response({"error": "Method not allowed"}, 405)

    # ============ API GET ============
    def _handle_api_get(self):
        parsed_path = urllib.parse.urlparse(self.path).path
        if parsed_path == '/api/games':
            self._json_response(self.api.get_games())
        elif parsed_path == '/api/languages':
            self._json_response(self.api.get_languages())
        elif parsed_path == '/api/settings':
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
            
        elif self.path.startswith('/api/jobs/'):
            job_id = self.path.split('?')[0].split('/')[-1]
            if job_id and job_id != 'jobs':
                self._json_response(self.api.get_job_status(job_id))
            else:
                self._json_response({"error": "Invalid job ID"}, 400)
        elif parsed_path == '/api/cache/get':
            self._json_response(self.api.get_cache_entries())
        elif self.path.startswith('/api/translation-memory/suggest'):
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            self._json_response(self.api.get_translation_memory_suggestions(
                query.get('game_id', [''])[0],
                query.get('text', [''])[0],
                query.get('category', ['unknown'])[0],
            ))
        elif parsed_path == '/api/data/stats':
            self._json_response(self.api.get_data_stats())
        elif self.path.startswith('/api/cache/search'):
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            q = query.get('q', [''])[0]
            page = int(query.get('page', ['1'])[0])
            limit = int(query.get('limit', ['50'])[0])
            self._json_response(self.api.search_cache(q, page, limit))
        elif self.path.startswith('/api/engines/coverage'):
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            game_id = query.get('game_id', [''])[0]
            self._json_response(self.api.get_coverage(game_id))
        elif self.path.startswith('/api/glossary/export'):
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            game_id = query.get('game_id', [''])[0]
            format_type = query.get('format', ['csv'])[0]
            self._json_response(self.api.export_glossary(game_id, format_type))
        else:
            self._json_response({"error": "Not found"}, 404)

    # ============ API POST ============
    def _handle_api_post(self):
        try:
            self._handle_api_post_inner()
        except ValueError as e:
            self._json_response({"error": str(e)}, 413)
        except (ConnectionAbortedError, ConnectionResetError):
            pass
        except Exception as e:
            import traceback
            traceback.print_exc()
            try:
                self._json_response({"error": str(e)}, 500)
            except Exception:
                pass

    def _handle_api_post_inner(self):
        if ApplicationLifecycle().is_shutting_down():
            self._json_response({"error": "System is shutting down"}, 503)
            return

        body = self._read_body()

        if self.path.startswith('/api/ping/disconnect'):
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            client_id = query.get('client_id', ['unknown'])[0]
            ApplicationLifecycle().disconnect_client(client_id)
            self._json_response({"status": "disconnected"})
            return

        if self.path == '/api/games/add':
            result = self.api.add_game()
            self._json_response(result or {"status": "cancelled"})

        elif self.path == '/api/games/start':
            result = self.api.start_game(body.get('game_id', ''))
            self._json_response(result)

        elif self.path == '/api/games/stop':
            result = self.api.stop_game(body.get('game_id', ''))
            self._json_response(result)
            
        elif self.path == '/api/games/sync':
            result = self.api.sync_game(body.get('game_id', ''))
            self._json_response(result)

        elif self.path == '/api/games/delete':
            result = self.api.delete_game(body.get('game_id', ''))
            self._json_response(result)

        elif self.path == '/api/games/play':
            result = self.api.play_game(body.get('game_id', ''))
            self._json_response(result)

        elif self.path == '/api/cache/qa-review':
            result = self.api.review_qa(body.get('entries', []))
            self._json_response(result)

        elif self.path == '/api/glossary/preview':
            result = self.api.preview_glossary_import(
                body.get('game_id', ''),
                body.get('content', ''),
                body.get('format', 'csv')
            )
            self._json_response(result)

        elif self.path == '/api/glossary/apply':
            result = self.api.apply_glossary_import(
                body.get('game_id', ''),
                body.get('parsed_data', []),
                body.get('strategy', 'merge')
            )
            self._json_response(result)

        elif self.path == '/api/glossary/delete':
            result = self.api.delete_glossary_term(
                body.get('game_id', ''),
                body.get('term', '')
            )
            self._json_response(result)

        elif self.path == '/api/tm/update':
            result = self.api.update_cache_entry(
                body.get('game_id', ''),
                body.get('key', ''),
                body.get('value', '')
            )
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

        elif self.path in ('/api/jobs/extract', '/api/engines/extract'):
            self._json_response(self.api.extract_offline(body.get('game_id', '')))

        elif self.path in ('/api/jobs/patch', '/api/engines/patch'):
            self._json_response(self.api.patch_offline(body.get('game_id', '')))

        else:
            self._json_response({"error": "Not found"}, 404)

    # ============ Static File Server ============
    def _serve_static(self):
        path = self.path.split('?')[0].lstrip('/')
        if not path:
            path = 'index.html'

        filepath = os.path.join(self.web_dir, path)

        # Bảo vệ: không cho truy cập ngoài web_dir
        filepath = os.path.abspath(filepath)
        web_dir_abs = os.path.abspath(self.web_dir)
        try:
            common = os.path.commonpath([web_dir_abs, filepath])
            if common != web_dir_abs:
                self.send_error(403)
                return
        except ValueError:
            self.send_error(403)
            return
        
        # Bỏ qua các tập hệ thống, favicon và .well-known
        if self.path == '/favicon.ico' or self.path.startswith('/.well-known'):
            self.send_response(204)
            self.end_headers()
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
                
            if filepath.endswith('index.html'):
                import re, time
                html_str = content.decode('utf-8')
                html_str = re.sub(r'\?v=\d+', f'?v={int(time.time())}', html_str)
                content = html_str.encode('utf-8')
                
            self.send_response(200)
            self.send_header('Content-Type', mime_type)
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        else:
            if not self.path.endswith('favicon.ico') and '.well-known' not in self.path:
                logger.error(f"[HTTP] 404 Not Found: {filepath} (Original path: {self.path})")
            self.send_error(404)

    # ============ Helpers ============
    def _json_response(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        if length > 10 * 1024 * 1024:
            raise ValueError("Payload too large. Maximum allowed is 10MB.")
        if length > 0:
            try:
                return json.loads(self.rfile.read(length))
            except (json.JSONDecodeError, Exception):
                return {}
        return {}

    def log_message(self, format, *args):
        msg = format % args
        if "/api/ping" in msg or "/api/games/translation-status" in msg or "/api/data/stats" in msg:
            return
        if "favicon.ico" in msg or ".well-known" in msg:
            return
        logger.info(f"[HTTP] {self.client_address[0]} - {msg}")

    def log_error(self, format, *args):
        msg = format % args
        if "favicon.ico" in self.path or ".well-known" in self.path:
            return
        logger.error(f"[HTTP] {msg} (Path: {self.path})")


import sys

class ATMServer(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        err_type = sys.exc_info()[0]
        if err_type is ConnectionAbortedError or err_type is ConnectionResetError:
            pass  # Suppress harmless TCP disconnections (WinError 10053/10054)
        else:
            super().handle_error(request, client_address)

def create_server(port, api):
    """Tạo HTTP server với API backend đã khởi tạo."""
    ATMHandler.api = api
    server = ATMServer(('127.0.0.1', port), ATMHandler)
    server.daemon_threads = True
    return server
