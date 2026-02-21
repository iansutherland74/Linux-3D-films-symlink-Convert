#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

HOST = os.getenv("SYMLINK_EDITOR_HOST", "192.168.1.14")
PORT = int(os.getenv("SYMLINK_EDITOR_PORT", "8080"))
ROOT = Path(os.getenv("FILMS_ROOT", "/mnt/3DFF")).expanduser()
THREE_D_TYPES = ("hsbs", "fsbs", "htab", "ftab", "mvc")


HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>3D Films Symlink Editor</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 1.5rem auto; max-width: 1000px; padding: 0 1rem; }
    h1 { margin-bottom: 0.25rem; }
    .muted { color: #555; margin-top: 0; }
    table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
    th, td { border-bottom: 1px solid #ddd; padding: 0.5rem; text-align: left; word-break: break-word; }
    form { display: grid; grid-template-columns: 1.2fr .5fr .8fr 1.5fr auto; gap: .6rem; align-items: end; margin-top: 1rem; }
    input, select { padding: .5rem; }
    button { padding: .5rem .7rem; cursor: pointer; }
    #status { margin-top: 0.5rem; min-height: 1.2rem; }
    .ok { color: #0a7f22; }
    .err { color: #ad1e00; }
    .help { margin-top: .75rem; color: #333; }
    code { background: #f6f6f6; padding: 0 .25rem; border-radius: 4px; }
  </style>
</head>
<body>
  <h1>3D Films Symlink Editor</h1>
  <p class="muted">Manage symbolic links and view all files inside <code id="root"></code>.</p>

  <form id="createForm">
    <label>Movie name<br /><input required name="movie_name" placeholder="Avatar" /></label>
    <label>Year<br /><input required name="year" inputmode="numeric" pattern="\\d{4}" placeholder="2009" /></label>
    <label>3D type<br />
      <select name="three_d_type" required>
        <option value="hsbs">hsbs (half side-by-side)</option>
        <option value="fsbs">fsbs (full side-by-side)</option>
        <option value="htab">htab (half top-and-bottom)</option>
        <option value="ftab">ftab (full top-and-bottom)</option>
        <option value="mvc">mvc (multiview video coding)</option>
      </select>
    </label>
    <label>Target path (absolute or inside root)<br /><input required name="target_path" placeholder="/mnt/storage/3d/Avatar (2009).mkv" /></label>
    <button type="submit">Create / Replace</button>
  </form>

  <p class="help">Generated filename format: <code>Movie Name - Year.3D.type.ext</code> (example: <code>Avatar - 2009.3D.hsbs.mkv</code>).</p>

  <div id="status"></div>

  <h2>Symlinks</h2>
  <table>
    <thead><tr><th>Link path</th><th>Target</th><th></th></tr></thead>
    <tbody id="rows"></tbody>
  </table>

  <h2>All files in FILMS_ROOT</h2>
  <table>
    <thead><tr><th>File path</th><th>Type</th></tr></thead>
    <tbody id="fileRows"></tbody>
  </table>

<script>
const statusEl = document.getElementById('status');
const rowsEl = document.getElementById('rows');
const fileRowsEl = document.getElementById('fileRows');

function setStatus(msg, ok=true) {
  statusEl.textContent = msg || '';
  statusEl.className = ok ? 'ok' : 'err';
}

async function loadLinks() {
  const res = await fetch('/api/links');
  const data = await res.json();
  document.getElementById('root').textContent = data.root;
  rowsEl.innerHTML = '';
  fileRowsEl.innerHTML = '';

  for (const row of data.links) {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${row.link_path}</td><td>${row.target_path}</td><td><button data-link="${row.link_path}">Delete</button></td>`;
    tr.querySelector('button').addEventListener('click', async () => {
      const del = await fetch('/api/links', {
        method: 'DELETE',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({link_path: row.link_path}),
      });
      const body = await del.json();
      if (!del.ok) return setStatus(body.error || 'Delete failed', false);
      setStatus('Deleted ' + row.link_path);
      await loadLinks();
    });
    rowsEl.appendChild(tr);
  }

  for (const file of data.files) {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${file.path}</td><td>${file.type}</td>`;
    fileRowsEl.appendChild(tr);
  }
}

document.getElementById('createForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const payload = {
    movie_name: fd.get('movie_name').toString(),
    year: fd.get('year').toString(),
    three_d_type: fd.get('three_d_type').toString(),
    target_path: fd.get('target_path').toString(),
  };
  const res = await fetch('/api/links', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload),
  });
  const body = await res.json();
  if (!res.ok) return setStatus(body.error || 'Create failed', false);
  setStatus('Created symlink: ' + body.link_path + ' → ' + body.target_path);
  e.target.reset();
  await loadLinks();
});

loadLinks().catch((e) => setStatus(String(e), false));
</script>
</body>
</html>
"""


@dataclass
class LinkRow:
    link_path: str
    target_path: str


@dataclass
class FileRow:
    path: str
    type: str


class RequestError(Exception):
    pass


def _json(handler: BaseHTTPRequestHandler, payload: dict, status: int = 200) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _safe_link_path(raw_link: str) -> Path:
    path = Path(raw_link)
    if path.is_absolute():
        raise RequestError("link_path must be relative to FILMS_ROOT")

    root = Path(os.path.normpath(str(ROOT.expanduser())))
    full = Path(os.path.normpath(str(ROOT / path)))
    if os.path.commonpath([str(root), str(full)]) != str(root):
        raise RequestError("link_path escapes FILMS_ROOT")
    return full


def _target_path(raw_target: str) -> Path:
    target = Path(raw_target).expanduser()
    if target.is_absolute():
        return target
    return (ROOT / target).resolve(strict=False)


def _validate_movie_name(movie_name: str) -> str:
    clean = re.sub(r"\s+", " ", movie_name.strip())
    if not clean:
        raise RequestError("movie_name is required")
    if any(c in clean for c in "/\\"):
        raise RequestError("movie_name cannot contain path separators")
    return clean


def _validate_year(raw_year: str) -> str:
    year = raw_year.strip()
    if not re.fullmatch(r"\d{4}", year):
        raise RequestError("year must be exactly 4 digits")
    return year


def _validate_three_d_type(raw_type: str) -> str:
    value = raw_type.strip().lower()
    if value not in THREE_D_TYPES:
        raise RequestError(f"three_d_type must be one of: {', '.join(THREE_D_TYPES)}")
    return value


def _build_link_name(movie_name: str, year: str, three_d_type: str, target: Path) -> str:
    ext = "".join(target.suffixes) or ".mkv"
    return f"{movie_name} - {year}.3D.{three_d_type}{ext}"


def list_links() -> list[LinkRow]:
    ROOT.mkdir(parents=True, exist_ok=True)
    result: list[LinkRow] = []
    for p in ROOT.rglob("*"):
        if p.is_symlink():
            result.append(LinkRow(link_path=str(p.relative_to(ROOT)), target_path=os.readlink(p)))
    result.sort(key=lambda r: r.link_path.lower())
    return result


def list_files() -> list[FileRow]:
    ROOT.mkdir(parents=True, exist_ok=True)
    result: list[FileRow] = []
    for p in ROOT.rglob("*"):
        if p.is_dir():
            continue
        item_type = "symlink" if p.is_symlink() else "file"
        result.append(FileRow(path=str(p.relative_to(ROOT)), type=item_type))
    result.sort(key=lambda r: r.path.lower())
    return result


def parse_json(handler: BaseHTTPRequestHandler) -> dict:
    try:
        length = int(handler.headers.get("Content-Length", "0"))
        data = handler.rfile.read(length) if length else b"{}"
        return json.loads(data.decode("utf-8"))
    except Exception as exc:
        raise RequestError("invalid JSON payload") from exc


class App(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._serve_html()
            return
        if parsed.path == "/api/links":
            _json(
                self,
                {
                    "root": str(ROOT),
                    "types": list(THREE_D_TYPES),
                    "links": [asdict(x) for x in list_links()],
                    "files": [asdict(x) for x in list_files()],
                },
            )
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/api/links":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            body = parse_json(self)
            target = _target_path(body.get("target_path", ""))

            if body.get("movie_name") is not None:
                movie_name = _validate_movie_name(str(body.get("movie_name", "")))
                year = _validate_year(str(body.get("year", "")))
                three_d_type = _validate_three_d_type(str(body.get("three_d_type", "")))
                link_name = _build_link_name(movie_name, year, three_d_type, target)
                link = _safe_link_path(link_name)
            else:
                link = _safe_link_path(body.get("link_path", ""))

            link.parent.mkdir(parents=True, exist_ok=True)
            if link.exists() or link.is_symlink():
                link.unlink()
            os.symlink(str(target), str(link))
            _json(self, {"ok": True, "link_path": str(link.relative_to(ROOT)), "target_path": str(target)}, status=201)
        except RequestError as exc:
            _json(self, {"error": str(exc)}, status=400)
        except Exception as exc:
            _json(self, {"error": f"failed to create symlink: {exc}"}, status=500)

    def do_DELETE(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/api/links":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            body = parse_json(self)
            link = _safe_link_path(body.get("link_path", ""))
            if not link.is_symlink():
                raise RequestError("link_path is not a symlink")
            link.unlink()
            _json(self, {"ok": True})
        except RequestError as exc:
            _json(self, {"error": str(exc)}, status=400)
        except Exception as exc:
            _json(self, {"error": f"failed to delete symlink: {exc}"}, status=500)

    def log_message(self, *_args) -> None:
        return

    def _serve_html(self) -> None:
        body = HTML.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((HOST, PORT), App)
    print(f"Serving symlink editor on http://{HOST}:{PORT} (FILMS_ROOT={ROOT})")
    server.serve_forever()


if __name__ == "__main__":
    run()
