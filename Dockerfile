# =========================
# STAGE 1: build de wheels
# =========================
FROM python:3.12-slim-bookworm AS builder

RUN apt-get update && apt-get install -y --no-install-recommends build-essential libffi-dev libssl-dev cargo && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt .

# Construye wheels en /dist
RUN pip install --no-cache-dir --upgrade pip \
    && pip wheel --no-cache-dir --wheel-dir=/dist -r requirements.txt

# =========================
# STAGE 2: Extraer mcp-proxy
# =========================
FROM --platform=$TARGETPLATFORM mcp-proxy2:v0.41.1 AS proxy_extractor
# Solo usamos esta etapa para copiar el binario, no hacemos nada más.

# =========================
# STAGE 3: runtime
# =========================
FROM python:3.12-slim-bookworm AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends libstdc++6 && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1
WORKDIR /opt/zen

# Copia el binario de mcp-proxy desde la etapa de extracción
COPY --from=proxy_extractor /app/mcp-proxy /opt/zen/

# Copia wheels y el requirements.txt
COPY --from=builder /dist /wheels
COPY --from=builder /build/requirements.txt /wheels/requirements.txt

# Crea venv e instala EXCLUSIVAMENTE desde /wheels (sin acceder a PyPI)
RUN python3 -m venv /opt/zen/.venv \
    && /opt/zen/.venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/zen/.venv/bin/pip install --no-index --find-links=/wheels -r /wheels/requirements.txt \
    && rm -rf /wheels

# Copia tu Zen “custodiado” y el archivo de configuración del proxy
COPY . /opt/zen
COPY mcp-proxy.json /opt/zen/mcp-proxy.json
ENV PYTHONPATH=/opt/zen

# Shim ejecutable para que el proxy pueda spawnnear "zen-mcp-server"
RUN printf '#!/bin/sh\nexec /opt/zen/.venv/bin/python /opt/zen/server.py "$@"\n' \
    > /usr/local/bin/zen-mcp-server \
    && chmod +x /usr/local/bin/zen-mcp-server

ENTRYPOINT ["./mcp-proxy", "-config", "./mcp-proxy.json"]
