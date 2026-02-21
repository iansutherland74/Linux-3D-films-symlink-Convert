FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FILMS_ROOT=/data/3d_films \
    SYMLINK_EDITOR_HOST=0.0.0.0 \
    SYMLINK_EDITOR_PORT=8080

WORKDIR /app
COPY app.py /app/app.py

EXPOSE 8080

VOLUME ["/data/3d_films"]

CMD ["python", "/app/app.py"]
