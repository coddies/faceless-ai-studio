import sys
import os

# Add the root directory to sys.path so we can import from backend
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Import the FastAPI app from backend.main
from backend.main import app

# Vercel needs 'app' to be exposed
# No uvicorn.run required as Vercel handles the execution
