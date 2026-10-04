# Dockerfile
# ----------
# WHY THIS FILE EXISTS:
#   Google Cloud Run runs "containers": a sealed box with Linux, Python and our server inside.
#   This file is the recipe for building that box. You don't need Docker on your PC - the command
#   "gcloud run deploy --source ." uploads this folder and Google builds the box for you.

# Start from an official, small Linux image that already has Python 3.13 installed.
FROM python:3.13-slim

# Python settings: don't write .pyc files, and print logs immediately (so Cloud Run shows them).
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# All following commands run inside the folder /srv in the container.
WORKDIR /srv

# Copy ONLY the requirements first - Docker caches this step, so rebuilding after a code change is fast.
COPY server/requirements.txt server/requirements.txt

# Install Flask, gunicorn and Pillow (no download cache kept = smaller image).
RUN pip install --no-cache-dir -r server/requirements.txt

# Copy the code the server needs: the shared app logic, the server itself and the recipe pictures.
COPY app/ app/
COPY server/ server/
COPY assets/recipe_images/ assets/recipe_images/

# Cloud Run tells the container which port to listen on via $PORT (usually 8080); 8080 is the default.
ENV PORT=8080

# Start gunicorn: 1 worker process with 8 threads is plenty for this small API and fits in 512 MB.
# "exec" makes gunicorn the main process, so Cloud Run can stop it cleanly.
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 30 server.wsgi:application
