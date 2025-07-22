FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for reconnaissance tools
RUN apt-get update && apt-get install -y \
    nmap \
    nikto \
    openssl \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY server.py .

# Copy AlienRecon source (for tool implementations)
COPY ../../src/alienrecon /app/alienrecon

EXPOSE 50051

CMD ["python", "server.py"]
