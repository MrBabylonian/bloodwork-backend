"""
Authentication and authorization dependencies for veterinary bloodwork analysis.

This module provides production-grade authentication dependencies that handle
both Admin and User authentication with automatic token validation and clear
role-based access control.

Features:
- Unified authentication for Admin and User models
- Role-based access control with granular permissions
- Automatic token validation and refresh
- Clean dependency injection pattern
- Comprehensive security logging

Author: Bedirhan Gilgiler
Last updated: 2025-06-20
"""

from typing import Union

from app.auth.auth_config import AuthConfig
from app.auth.auth_service import AuthService
from app.config.database_config import DatabaseConfig
from app.models.database_models import Admin, User, UserRole
from app.repositories.repository_factory import RepositoryFactory
from app.services.database_service import DatabaseService
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)

# Singleton instances for dependency injection
_database_service = None
_repository_factory = None
_auth_service = None


def get_database_service() -> DatabaseService:
    """Get singleton database service instance."""
    global _database_service
    if _database_service is None:
        config = DatabaseConfig()
        _database_service = DatabaseService(config)
    return _database_service


def get_repository_factory(db_service: DatabaseService = Depends(get_database_service)) -> RepositoryFactory:
    """Get singleton repository factory instance."""
    global _repository_factory
    if _repository_factory is None:
        _repository_factory = RepositoryFactory(db_service)
    return _repository_factory


def get_auth_service(repo_factory: RepositoryFactory = Depends(get_repository_factory)) -> AuthService:
    """Get singleton authentication service instance."""
    global _auth_service
    if _auth_service is None:
        config = AuthConfig()
        _auth_service = AuthService(
            user_repo=repo_factory.user_repository,
            admin_repo=repo_factory.admin_repository,
            refresh_token_repo=repo_factory.refresh_token_repository,
            config=config
        )
    return _auth_service


async def get_current_authenticated_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> Union[Admin, User]:
    """
    Get current authenticated user (Admin or User).

    This is the main authentication dependency that:
    1. Validates the JWT token
    2. Returns the actual Admin or User model
    3. Handles token refresh automatically
    4. Provides clear error messages

    Returns:
        Union[Admin, User]: The authenticated user instance

    Raises:
        HTTPException: 401 if authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await auth_service.get_authenticated_user(credentials.credentials)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_admin():
    """
    Dependency that requires admin privileges.

    Returns:
        function: Dependency function that ensures user is admin
    """
    async def admin_checker(
        current_user: Union[Admin, User] = Depends(
            get_current_authenticated_user)
    ) -> Admin:
        if not isinstance(current_user, Admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        return current_user
    return admin_checker


def require_veterinarian_or_admin():
    """
    Dependency that requires veterinarian role or admin privileges.

    Returns:
        function: Dependency function that ensures user is vet or admin
    """
    async def vet_or_admin_checker(
        current_user: Union[Admin, User] = Depends(
            get_current_authenticated_user)
    ) -> Union[Admin, User]:
        if isinstance(current_user, Admin):
            return current_user

        if isinstance(current_user, User):
            if current_user.role == UserRole.VETERINARIAN:
                return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Veterinarian or admin privileges required"
        )
    return vet_or_admin_checker


def require_any_authenticated_user():
    """
    Dependency that requires any authenticated user (Admin, Vet, or Tech).

    Returns:
        function: Dependency function that ensures user is authenticated
    """
    async def any_user_checker(
        current_user: Union[Admin, User] = Depends(
            get_current_authenticated_user)
    ) -> Union[Admin, User]:
        # If we got here, the user is authenticated - just return them
        return current_user
    return any_user_checker


# Convenient pre-configured dependencies
require_admin_user = require_admin()
require_vet_or_admin = require_veterinarian_or_admin()
require_authenticated = require_any_authenticated_user()
