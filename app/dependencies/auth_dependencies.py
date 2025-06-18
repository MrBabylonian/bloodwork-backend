from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.auth.auth_service import AuthService
from app.auth.auth_config import AuthConfig
from app.config.database_config import DatabaseConfig
from app.models.database_models import UserRole
from app.repositories import RepositoryFactory
from app.services.database_service import DatabaseService

# Security scheme for token extraction
security = HTTPBearer()

# Global instances (singleton pattern)
_database_service = None
_repository_factory = None
_auth_service = None


def get_database_service() -> DatabaseService:
    """Get database service instance"""
    global _database_service
    if _database_service is None:
        config = DatabaseConfig()
        _database_service = DatabaseService(config)
    return _database_service


def get_repository_factory(db_service: DatabaseService = Depends(get_database_service)) -> RepositoryFactory:
    """Get repository factory instance"""
    global _repository_factory
    if _repository_factory is None:
        _repository_factory = RepositoryFactory(db_service)
    return _repository_factory


def get_auth_service(repo_factory: RepositoryFactory = Depends(get_repository_factory)) -> AuthService:
    """Get authentication service instance"""
    global _auth_service
    if _auth_service is None:
        config = AuthConfig()
        _auth_service = AuthService(
            user_repo=repo_factory.user_repository,
            refresh_token_repo=repo_factory.refresh_token_repository,
            config=config
        )
    return _auth_service


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> dict:
    """Get current authenticated user from JWT token"""
    token = credentials.credentials
    user_info = await auth_service.verify_access_token(token)
    
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_info


async def get_current_active_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Get current active user (same as get_current_user, but more explicit)"""
    return current_user


def require_role(required_role: UserRole):
    """Create a dependency that requires a specific role"""
    async def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        user_role = current_user.get("role")
        if user_role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {required_role}"
            )
        return current_user
    return role_checker


# Pre-configured role dependencies  
def require_veterinarian():
    return require_role(UserRole.VETERINARIAN)

def require_technician():
    return require_role(UserRole.VETERINARY_TECHNICIAN)

def require_admin_role():
    """Dependency that requires admin role"""
    async def admin_checker(current_user: dict = Depends(get_current_user)) -> dict:
        # Check if user has admin role or is actually an admin
        user_role = current_user.get("role")
        if user_role not in ["admin", UserRole.VETERINARIAN]:  # Allow vets to have admin functions
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Admin privileges required."
            )
        return current_user
    return admin_checker
