# Minimal Docker image for Hugging Face Spaces
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Environment variables for Hugging Face Spaces
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=7860

# Copy essential project files
COPY requirements.txt .
COPY app.py .
COPY README.md .
COPY LICENSE .
COPY .env.template .
COPY deployment_state.json .

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Expose port for Hugging Face Spaces
EXPOSE 7860

# Run the application
CMD ["python", "-m", "gunicorn", "--bind", "0.0.0.0:7860", "--workers", "1", "--timeout", "120", "app:app"]