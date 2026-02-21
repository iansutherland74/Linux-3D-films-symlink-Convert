# Casaco File Browser

Simple web file browser for CasaOS/Casaco-like deployments.

## Run local

```bash
python3 casaco_file_browser.py
```

Defaults:
- `FILE_BROWSER_HOST=0.0.0.0`
- `FILE_BROWSER_PORT=8080`
- `FILE_BROWSER_ROOT=/DATA`

Open: `http://localhost:8080`

## Run with Docker

```bash
docker build -t casaco-file-browser .
docker run --rm -p 8080:8080 -v "$PWD/data:/DATA" casaco-file-browser
```

## Run with docker compose

```bash
BROWSE_DIR=/DATA/MyFiles docker compose up --build
```

## CasaOS quick setup

Use custom compose install with:

```yaml
services:
  casaco-file-browser:
    image: ghcr.io/<you>/casaco-file-browser:latest
    ports:
      - "8080:8080"
    environment:
      FILE_BROWSER_HOST: 0.0.0.0
      FILE_BROWSER_PORT: 8080
      FILE_BROWSER_ROOT: /DATA
    volumes:
      - /DATA:/DATA
```
