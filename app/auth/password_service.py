from passlib.context import CryptContext


class PasswordService:
    """Simple password hashing and verification service"""

    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(self, password: str) -> str:
        """Hash a password"""
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return self.pwd_context.verify(plain_password, hashed_password)

    def is_valid_password(self, password: str, min_length: int = 8) -> bool:
        """Basic password validation"""
        return len(password) >= min_length
