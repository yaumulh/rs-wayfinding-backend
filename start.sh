#!/bin/bash
# Start script for Railway deployment
exec uvicorn server:app --host 0.0.0.0 --port $PORT
