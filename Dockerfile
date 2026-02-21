FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FILE_BROWSER_HOST=0.0.0.0 \
    FILE_BROWSER_PORT=8080 \
    FILE_BROWSER_ROOT=/DATA

WORKDIR /app
COPY casaco_file_browser.py /app/casaco_file_browser.py

EXPOSE 8080
VOLUME ["/DATA"]

CMD ["python", "/app/casaco_file_browser.py"]
