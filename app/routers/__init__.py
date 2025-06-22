"""Router package initialization."""

# Import the actual router modules
from . import analysis_router, auth_router, diagnostic_router, patient_router

# Export for easy import in main.py
__all__ = ["analysis_router", "auth_router",
           "diagnostic_router", "patient_router"]
