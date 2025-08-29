# =========================
# STAGE 1: build de wheels
# =========================
FROM python:3.11-alpine AS builder

# Toolchain de build para wheels (se descarta al final)
RUN apk add --no-cache build-base libffi-dev openssl-dev cargo

WORKDIR /wheels
COPY requirements.txt .

# Construye wheels de TODAS las dependencias
RUN pip install --no-cache-dir --upgrade pip \
 && pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements.txt

# Si tienes dependencias locales en el repo (opcional):
# COPY . /src
# (y si existiera un pyproject/setup puedes wheelar tu paquete también)

# =========================
# STAGE 2: runtime con mcp-proxy
# =========================
FROM ghcr.io/sparfenyuk/mcp-proxy:v0.8.2 AS runtime

# Libs runtime para wheels compiladas (sin toolchain)
RUN apk add --no-cache libstdc++

ENV PYTHONUNBUFFERED=1
WORKDIR /opt/zen

# Crea venv e instala desde wheels construidas
COPY --from=builder /wheels /wheels
RUN python3 -m venv /opt/zen/.venv \
 && /opt/zen/.venv/bin/pip install --no-cache-dir --upgrade pip \
 && /opt/zen/.venv/bin/pip install --no-cache-dir /wheels/* \
 && rm -rf /wheels

# Copia tu Zen “custodiado” (código fuente)
COPY . /opt/zen
ENV PYTHONPATH=/opt/zen

# Shim para que exista el ejecutable "zen-mcp-server"
RUN printf '#!/bin/sh\nexec /opt/zen/.venv/bin/python /opt/zen/server.py "$@"\n' \
      > /usr/local/bin/zen-mcp-server \
 && chmod +x /usr/local/bin/zen-mcp-server

# mcp-proxy queda como entrypoint; zen se lanza como subproceso STDIO
ENTRYPOINT ["mcp-proxy"]