# Docker image optimized for Render deployment
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Environment variables for Render
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=10000

# Copy essential project files
COPY requirements.txt .
COPY app.py .
COPY README.md .
COPY LICENSE .
COPY .env.template .
COPY deployment_state.json .
COPY start.sh .

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Make start script executable
RUN chmod +x start.sh

# Create data directory for persistent storage
RUN mkdir -p /app/data

# Expose port for Render (uses PORT environment variable)
EXPOSE $PORT

# Run the application with start script optimized for Render
CMD ["./start.sh"]