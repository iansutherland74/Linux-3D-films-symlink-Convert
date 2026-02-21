#!/usr/bin/env python3
from __future__ import annotations

import json
import mimetypes
import os
from dataclasses import asdict, dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

HOST = os.getenv("FILE_BROWSER_HOST", "0.0.0.0")
PORT = int(os.getenv("FILE_BROWSER_PORT", "8080"))
ROOT = Path(os.getenv("FILE_BROWSER_ROOT", "/DATA")).expanduser()


HTML = """<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Casaco File Browser</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 1100px; margin: 1.5rem auto; padding: 0 1rem; }
    table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
    th, td { text-align: left; border-bottom: 1px solid #ddd; padding: .45rem; }
    code { background: #f5f5f5; padding: 0 .3rem; border-radius: 4px; }
    .muted { color: #555; }
    .row-actions a { margin-right: .5rem; }
  </style>
</head>
<body>
  <h1>Casaco File Browser</h1>
  <p class="muted">Browsing root: <code id="root"></code></p>
  <p class="muted">Current path: <code id="cwd"></code></p>

  <form id="navForm">
    <label>Go to path (inside root):
      <input id="pathInput" name="path" placeholder="." style="min-width: 320px" />
    </label>
    <button type="submit">Open</button>
  </form>

  <table>
    <thead>
      <tr><th>Name</th><th>Type</th><th>Size</th><th>Actions</th></tr>
    </thead>
    <tbody id="rows"></tbody>
  </table>

<script>
async function load(path='.') {
  const q = new URLSearchParams({path}).toString();
  const res = await fetch('/api/list?' + q);
  const data = await res.json();
  if (!res.ok) { alert(data.error || 'Failed'); return; }

  document.getElementById('root').textContent = data.root;
  document.getElementById('cwd').textContent = data.path;
  document.getElementById('pathInput').value = data.path;

  const rows = document.getElementById('rows');
  rows.innerHTML = '';

  for (const item of data.items) {
    const tr = document.createElement('tr');
    const openHref = `#${item.path}`;
    const view = item.type === 'dir'
      ? `<a href="${openHref}" data-open="${item.path}">Open</a>`
      : `<a href="/api/download?path=${encodeURIComponent(item.path)}">Download</a>`;
    tr.innerHTML = `
      <td>${item.name}</td>
      <td>${item.type}</td>
      <td>${item.size}</td>
      <td class="row-actions">${view}</td>
    `;

    const link = tr.querySelector('[data-open]');
    if (link) {
      link.addEventListener('click', async (e) => {
        e.preventDefault();
        await load(link.dataset.open);
      });
    }
    rows.appendChild(tr);
  }
}

document.getElementById('navForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const p = document.getElementById('pathInput').value || '.';
  await load(p);
});

load('.');
</script>
</body>
</html>
"""


@dataclass
class Item:
    name: str
    path: str
    type: str
    size: int


class RequestError(Exception):
    pass


def safe_path(raw_path: str) -> Path:
    ROOT.mkdir(parents=True, exist_ok=True)
    part = (raw_path or ".").strip() or "."
    p = Path(part)
    if p.is_absolute():
        raise RequestError("path must be relative to FILE_BROWSER_ROOT")
    full = (ROOT / p).resolve(strict=False)
    root = ROOT.resolve(strict=False)
    try:
        full.relative_to(root)
    except ValueError as exc:
        raise RequestError("path escapes FILE_BROWSER_ROOT") from exc
    return full


def list_dir(current: Path) -> list[Item]:
    if not current.exists() or not current.is_dir():
        raise RequestError("path is not a directory")

    root = ROOT.resolve(strict=False)
    items: list[Item] = []

    if current != root:
        parent_rel = str(current.parent.relative_to(root))
        items.append(Item(name="..", path=parent_rel if parent_rel else ".", type="dir", size=0))

    for entry in sorted(current.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        item_type = "dir" if entry.is_dir() else "file"
        size = 0 if entry.is_dir() else entry.stat().st_size
        items.append(
            Item(
                name=entry.name,
                path=str(entry.relative_to(root)),
                type=item_type,
                size=size,
            )
        )
    return items


class App(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._html()
            return
        if parsed.path == "/api/list":
            self._list(parsed)
            return
        if parsed.path == "/api/download":
            self._download(parsed)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def _list(self, parsed) -> None:
        try:
            q = parse_qs(parsed.query)
            raw = q.get("path", ["."])[0]
            current = safe_path(unquote(raw))
            root = ROOT.resolve(strict=False)
            rel = str(current.relative_to(root)) if current != root else "."
            payload = {
                "root": str(root),
                "path": rel,
                "items": [asdict(x) for x in list_dir(current)],
            }
            self._json(payload)
        except RequestError as exc:
            self._json({"error": str(exc)}, 400)

    def _download(self, parsed) -> None:
        try:
            q = parse_qs(parsed.query)
            raw = q.get("path", [""])[0]
            target = safe_path(unquote(raw))
            if not target.exists() or not target.is_file():
                raise RequestError("file not found")

            data = target.read_bytes()
            ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Content-Disposition", f"attachment; filename={quote(target.name)}")
            self.end_headers()
            self.wfile.write(data)
        except RequestError as exc:
            self._json({"error": str(exc)}, 400)

    def _html(self) -> None:
        b = HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _json(self, payload: dict, status: int = 200) -> None:
        b = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *_args) -> None:
        return


def run() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((HOST, PORT), App)
    print(f"Casaco File Browser: http://{HOST}:{PORT} root={ROOT}")
    server.serve_forever()


if __name__ == "__main__":
    run()
