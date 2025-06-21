from app.repositories.admin_repository import AdminRepository
from app.repositories.ai_diagnostic_repository import AiDiagnosticRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.sequence_counter_repository import SequenceCounterRepository
from app.repositories.user_repository import UserRepository
from app.services.database_service import DatabaseService


class RepositoryFactory:
    """Factory class for creating repository instances"""

    def __init__(self, database_service: DatabaseService):
        self.database_service = database_service
        self._patient_repo = None
        self._user_repo = None
        self._admin_repo = None
        self._ai_diagnostic_repo = None
        self._refresh_token_repo = None
        self._sequence_counter_repo = None

    @property
    def patient_repository(self) -> PatientRepository:
        """Get PatientRepository instance (singleton pattern)"""
        if self._patient_repo is None:
            self._patient_repo = PatientRepository(self.database_service)
        return self._patient_repo

    @property
    def user_repository(self) -> UserRepository:
        """Get UserRepository instance (singleton pattern)"""
        if self._user_repo is None:
            self._user_repo = UserRepository(self.database_service)
        return self._user_repo

    @property
    def admin_repository(self) -> AdminRepository:
        """Get AdminRepository instance (singleton pattern)"""
        if self._admin_repo is None:
            self._admin_repo = AdminRepository(self.database_service)
        return self._admin_repo

    @property
    def ai_diagnostic_repository(self) -> AiDiagnosticRepository:
        """Get AiDiagnosticRepository instance (singleton pattern)"""
        if self._ai_diagnostic_repo is None:
            self._ai_diagnostic_repo = AiDiagnosticRepository(
                self.database_service)
        return self._ai_diagnostic_repo

    @property
    def refresh_token_repository(self) -> RefreshTokenRepository:
        """Get RefreshTokenRepository instance (singleton pattern)"""
        if self._refresh_token_repo is None:
            self._refresh_token_repo = RefreshTokenRepository(
                self.database_service)
        return self._refresh_token_repo

    @property
    def sequence_counter_repository(self) -> SequenceCounterRepository:
        """Get SequenceCounterRepository instance (singleton pattern)"""
        if self._sequence_counter_repo is None:
            self._sequence_counter_repo = SequenceCounterRepository(
                self.database_service)
        return self._sequence_counter_repo
