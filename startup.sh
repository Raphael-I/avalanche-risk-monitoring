#!/bin/sh

# Azure App Service startup command for the FastAPI application.
exec gunicorn \
  --workers 2 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:${PORT:-8000} \
  --chdir src \
  avalanche_risk_monitoring.services.api.app:app
