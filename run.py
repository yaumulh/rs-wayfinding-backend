#!/usr/bin/env python3
"""
Script to run the FastAPI backend server
"""
import uvicorn
import os
from pathlib import Path

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / '.env')

    # Get port from environment or default to 8000
    port = int(os.environ.get('PORT', 8000))
    host = os.environ.get('HOST', '0.0.0.0')

    print(f"Starting server on {host}:{port}")
    uvicorn.run("server:app", host=host, port=port, reload=True)
