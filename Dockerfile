# Build stage
FROM python:3.10-slim as builder

WORKDIR /app
COPY requirements.txt .

RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.10-slim

WORKDIR /app

# Copy only the necessary files from builder
COPY --from=builder /root/.local /root/.local
COPY . .

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Clean up
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

EXPOSE 8000

# Make migrations and start app
CMD alembic upgrade head && uvicorn src.main:app --host 0.0.0.0 --port 8000
