FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    LD_LIBRARY_PATH="/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH}"

WORKDIR /app

# Install Linux system dependencies for Debian 12 (Bookworm)
# Includes libgl1, libegl1, libgles2, and mesa-dri required by MediaPipe PoseLandmarker on headless Linux
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libegl1 \
    libgles2 \
    libgl1-mesa-dri \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    unixodbc-dev \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code (excluding files in .dockerignore)
COPY . .

# Expose backend port
EXPOSE 8000

# Start FastAPI Uvicorn server bound to 0.0.0.0 and dynamic cloud port
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}"]
