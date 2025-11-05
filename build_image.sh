#!/bin/bash
docker buildx build --platform linux/amd64 --no-cache -t cell-mcp-server:9.1.3-rc5 .
