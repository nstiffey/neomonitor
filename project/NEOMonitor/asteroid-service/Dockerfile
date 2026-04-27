# Standard Dockerfile for Gateway, Asteroid, and Risk services
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY asteroid-service/app.py .

CMD ["python", "app.py"]