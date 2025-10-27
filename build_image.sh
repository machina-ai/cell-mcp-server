#!/bin/bash
docker buildx build --platform linux/amd64 --no-cache -t cell-mcp-server:0.1.2 .
