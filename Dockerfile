FROM python:3.9-slim

# ----------------------------
# System dependencies (minimal)
# ----------------------------
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

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
