import pytest
import os
from unittest.mock import MagicMock
from atm.ui.server import ATMHandler

class MockRequest:
    def makefile(self, *args, **kwargs):
        import io
        return io.BytesIO(b"")

def test_server_path_traversal():
    handler = ATMHandler(MockRequest(), ('127.0.0.1', 8080), None)
    handler.send_error = MagicMock()
    handler.path = "/../../../Windows/System32/cmd.exe"
    handler._serve_static()
    handler.send_error.assert_called_with(403)

def test_server_payload_too_large():
    handler = ATMHandler(MockRequest(), ('127.0.0.1', 8080), None)
    handler.headers = {'Content-Length': str(11 * 1024 * 1024)} # 11MB
    with pytest.raises(ValueError, match="Payload too large"):
        handler._read_body()

def test_server_payload_ok():
    handler = ATMHandler(MockRequest(), ('127.0.0.1', 8080), None)
    handler.headers = {'Content-Length': str(5 * 1024 * 1024)} # 5MB
    handler.rfile = MagicMock()
    handler.rfile.read.return_value = b"{}"
    body = handler._read_body()
    assert body == {}
