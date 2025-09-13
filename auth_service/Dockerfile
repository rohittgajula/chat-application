
# use python base image
FROM python:3.11-slim-bookworm

WORKDIR /app

# Prevent Python from writing pyc files and buffering
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose port (Django default)
EXPOSE 8000

# Run Django dev server (override in docker-compose if needed)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

