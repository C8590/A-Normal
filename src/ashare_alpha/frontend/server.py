from __future__ import annotations

import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def serve_frontend(directory: Path, host: str = "127.0.0.1", port: int = 8765) -> None:
    root = Path(directory)
    if not root.exists() or not root.is_dir():
        raise ValueError(f"frontend directory does not exist: {root}")
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(root))
    with ThreadingHTTPServer((host, port), handler) as server:
        print(f"Serving frontend from {root} at http://{host}:{port}/")
        server.serve_forever()


def host_warning(host: str) -> str | None:
    if host in {"127.0.0.1", "localhost"}:
        return None
    return f"Warning: serving frontend on non-localhost host {host}. This static server is intended for local read-only review."
