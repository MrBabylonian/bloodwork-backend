"""Repository package for data access layer."""

from app.repositories.admin_repository import AdminRepository
from app.repositories.ai_diagnostic_repository import AiDiagnosticRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.repository_factory import RepositoryFactory
from app.repositories.user_repository import UserRepository

# Note: SequenceCounterRepository has been removed and replaced with
# DatabaseService.get_next_sequential_id for more reliable ID generation

__all__ = [
    "AdminRepository",
    "AiDiagnosticRepository",
    "PatientRepository",
    "RefreshTokenRepository",
    "RepositoryFactory",
    "UserRepository"
]
