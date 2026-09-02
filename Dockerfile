FROM python:3.12-slim
WORKDIR /app

# System dependencies needed by psycopg2, pymupdf, and torch/open-clip
   RUN apt-get update && apt-get install -y \
       build-essential \
       libpq-dev \
       libgl1 \
       tesseract-ocr \
       && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install CPU-only torch/torchvision first (avoids pulling huge NVIDIA CUDA packages)
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]