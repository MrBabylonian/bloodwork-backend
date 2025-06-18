"""Router package initialization."""

# Import the actual router modules
from . import auth_router, patient_router

# Export for easy import in main.py
__all__ = ["auth_router", "patient_router"]
