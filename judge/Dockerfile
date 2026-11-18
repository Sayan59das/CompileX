# The judge: runs players' code in Docker sandboxes. Build with the REPOSITORY ROOT as the context:
#   docker build -f judge/Dockerfile -t compilex-judge .
# It runs as root on purpose: it must talk to the Docker socket, which is root on the host anyway. Run it on a machine that holds nothing else.
FROM python:3.11-slim

WORKDIR /srv

COPY judge/requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Only what the executor needs, copied from the backend so there is one executor, not two.
COPY backend/app/__init__.py app/__init__.py
COPY backend/app/core/__init__.py backend/app/core/config.py app/core/
COPY backend/app/services/__init__.py backend/app/services/code_executor.py app/services/
COPY judge/main.py main.py

ENV PORT=9000
EXPOSE 9000
CMD ["bash", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-9000}"]
