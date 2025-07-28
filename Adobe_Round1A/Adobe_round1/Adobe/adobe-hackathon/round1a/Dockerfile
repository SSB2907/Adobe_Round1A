FROM --platform=linux/amd64 python:3.9-slim

WORKDIR /app

# Install system dependencies required for OCR and image conversion
RUN apt-get update && apt-get install -y \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-mar \
    libgl1-mesa-glx \
    && apt-get clean

# Copy requirements file first (better for Docker caching)
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Default command to run
CMD ["python", "extractor.py"]
