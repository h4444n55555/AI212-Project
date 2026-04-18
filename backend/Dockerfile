FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for OpenCV and GLib (required by ultralytics/yolov8)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install specific Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application source code
COPY . .

# Generate the start wrapper script inside the container
# This perfectly mimics what start.bat achieves locally mapping 4 workers to ports 8001-8004
# and the primary router to 8000
RUN echo '#!/bin/bash\n\
uvicorn main:app --port 8001 --host 127.0.0.1 --log-level critical &\n\
uvicorn main:app --port 8002 --host 127.0.0.1 --log-level critical &\n\
uvicorn main:app --port 8003 --host 127.0.0.1 --log-level critical &\n\
uvicorn main:app --port 8004 --host 127.0.0.1 --log-level critical &\n\
sleep 2\n\
uvicorn router:app --port 8000 --host 0.0.0.0\n\
' > start.sh && chmod +x start.sh

# Expose router port
EXPOSE 8000

# Start the cluster wrapper
CMD ["./start.sh"]
