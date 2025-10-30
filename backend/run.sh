#!/usr/bin/env bash
# Run the backend for development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
