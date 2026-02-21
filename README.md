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

### Docker run helper script

```bash
./docker-run.sh
```

Optional overrides:

- `IMAGE_NAME` (default: `symlink-editor`)
- `CONTAINER_NAME` (default: `symlink-editor`)
- `HOST_PORT` (default: `8080`)
- `FILMS_DIR` (default: `./films`)

Example:

```bash
HOST_PORT=8090 FILMS_DIR=/DATA/AppData/symlink-editor/films ./docker-run.sh
```


## Install on CasaOS

CasaOS can run this app as a custom container. CasaOS compose import typically expects an image (not local `build: .`), so publish/use an image tag first.

### Option 1: Import docker-compose (recommended)

1. In CasaOS, open **App Store** → **Custom Install** (or **Install via Compose** depending on CasaOS version).
2. Build and publish an image first (for example `ghcr.io/<you>/symlink-editor:latest`).
3. Paste this compose into CasaOS:

```yaml
services:
  symlink-editor:
    image: ghcr.io/<you>/symlink-editor:latest
    container_name: symlink-editor
    ports:
      - "8080:8080"
    environment:
      FILMS_ROOT: /data/3d_films
      SYMLINK_EDITOR_HOST: 0.0.0.0
      SYMLINK_EDITOR_PORT: 8080
    volumes:
      - /DATA/AppData/symlink-editor/films:/data/3d_films
    restart: unless-stopped
```

4. Adjust the image tag and host path (`/DATA/AppData/symlink-editor/films`) to your setup.
5. Install/start the app.
6. Open it from CasaOS dashboard (or `http://<your-casaos-ip>:8080`).

### Option 2: Manual container form in CasaOS

If you prefer the one-container form:

- **Image**: build/push this project image first (for example `ghcr.io/<you>/symlink-editor:latest`) and use that image.
- **Port mapping**: `8080` (host) → `8080` (container)
- **Environment**:
  - `FILMS_ROOT=/data/3d_films`
  - `SYMLINK_EDITOR_HOST=0.0.0.0`
  - `SYMLINK_EDITOR_PORT=8080`
- **Volume mapping**:
  - Host: `/DATA/AppData/symlink-editor/films`
  - Container: `/data/3d_films`

After deploy, browse to `http://<your-casaos-ip>:8080`.

## Notes

- `movie_name` cannot contain `/` or `\`.
- `year` must be exactly 4 digits.
- `three_d_type` must be one of `hsbs`, `fsbs`, `htab`, `ftab`, `mvc`.
- `target_path` can be absolute or relative to `FILMS_ROOT`.
