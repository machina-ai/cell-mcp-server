# =========================
# STAGE 1: build de wheels
# =========================
FROM python:3.12-alpine AS builder

RUN apk add --no-cache build-base libffi-dev openssl-dev cargo

WORKDIR /build
COPY requirements.txt .

# Construye wheels en /dist
RUN pip install --no-cache-dir --upgrade pip \
 && pip wheel --no-cache-dir --wheel-dir=/dist -r requirements.txt

# =========================
# STAGE 2: runtime con mcp-proxy
# =========================
FROM mcp-proxy:0.8.2-rc1 AS runtime

RUN apk add --no-cache libstdc++

ENV PYTHONUNBUFFERED=1
WORKDIR /opt/zen

# Copia wheels y el requirements.txt
COPY --from=builder /dist /wheels
COPY --from=builder /build/requirements.txt /wheels/requirements.txt

# Crea venv e instala EXCLUSIVAMENTE desde /wheels (sin acceder a PyPI)
RUN python3 -m venv /opt/zen/.venv \
 && /opt/zen/.venv/bin/pip install --no-cache-dir --upgrade pip \
 && /opt/zen/.venv/bin/pip install --no-index --find-links=/wheels -r /wheels/requirements.txt \
 && rm -rf /wheels

# Copia tu Zen “custodiado”
COPY . /opt/zen
ENV PYTHONPATH=/opt/zen

# Shim ejecutable para que el proxy pueda spawnnear "zen-mcp-server"
RUN printf '#!/bin/sh\nexec /opt/zen/.venv/bin/python /opt/zen/server.py "$@"\n' \
      > /usr/local/bin/zen-mcp-server \
 && chmod +x /usr/local/bin/zen-mcp-server

ENTRYPOINT ["mcp-proxy"]