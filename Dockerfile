FROM python:3.9-slim

# ----------------------------
# System dependencies (GDAL stack)
# ----------------------------
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    proj-bin \
    proj-data \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# ----------------------------
# Environment variables for GDAL
# ----------------------------
ENV GDAL_CONFIG=/usr/bin/gdal-config
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# ----------------------------
# Working directory
# ----------------------------
WORKDIR /app

# ----------------------------
# Install Python dependencies
# ----------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ----------------------------
# Copy full project
# ----------------------------
COPY . .

# ----------------------------
# Hugging Face uses port 7860
# ----------------------------
EXPOSE 7860

# ----------------------------
# Start FastAPI
# ----------------------------
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "7860"]
