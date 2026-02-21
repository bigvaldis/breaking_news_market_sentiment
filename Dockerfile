FROM python:3.12-slim

WORKDIR /app

# Install Node for frontend build
RUN apt-get update && apt-get install -y nodejs npm && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App
COPY . .

# Build frontend
RUN cd frontend && npm install && npm run build && cd ..

EXPOSE 8080
ENV PORT=8080
CMD gunicorn -w 2 -b 0.0.0.0:${PORT} api.app:app
