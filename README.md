# 3D Films Symlink Editor

A small Linux-focused web app to manage symlinks for a 3D films library.

## What it does

- Shows all symlinks under a configured root directory.
- Creates/replaces symlinks from the browser using 3D format types:
  - `hsbs` (half side-by-side)
  - `fsbs` (full side-by-side)
  - `htab` (half top-and-bottom)
  - `ftab` (full top-and-bottom)
  - `mvc` (Multiview Video Coding)
- Deletes symlinks from the browser.

## Generated link filename format

`Movie Name - Year.3D.type.ext`

Example: `Avatar - 2009.3D.hsbs.mkv`

The extension (`.ext`) is inferred from the target path. If there is no extension, `.mkv` is used.

## Run

```bash
python3 app.py
```

Optional environment variables:

- `FILMS_ROOT`: root folder that holds symlinks (default: `~/Videos/3D_films`)
- `SYMLINK_EDITOR_HOST`: host bind (default: `127.0.0.1`)
- `SYMLINK_EDITOR_PORT`: port (default: `8080`)

Open `http://127.0.0.1:8080`.


## Run with Docker

### Docker

```bash
docker build -t symlink-editor .
docker run --rm -p 8080:8080 \
  -e FILMS_ROOT=/data/3d_films \
  -v "$PWD/films:/data/3d_films" \
  symlink-editor
```

### Docker Compose

```bash
docker compose up --build
```

This mounts `./films` from your host into the container as `/data/3d_films`, so created symlinks persist on your machine.

## Notes

- `movie_name` cannot contain `/` or `\`.
- `year` must be exactly 4 digits.
- `three_d_type` must be one of `hsbs`, `fsbs`, `htab`, `ftab`, `mvc`.
- `target_path` can be absolute or relative to `FILMS_ROOT`.
