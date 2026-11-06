import socketserver
from http.server import SimpleHTTPRequestHandler

class RobustHandler(SimpleHTTPRequestHandler):
    def handle_one_request(self):
        try:
            super().handle_one_request()
        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
            pass

    def log_message(self, format, *args):
        pass

class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

if __name__ == "__main__":
    server = ThreadedHTTPServer(("127.0.0.1", 8000), RobustHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
