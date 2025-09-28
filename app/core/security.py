"""
Security utilities for authentication and authorization
"""

import bcrypt
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import streamlit as st
from jose import JWTError, jwt

from .config import settings


class SecurityManager:
    """Handles password hashing and JWT tokens"""

    def __init__(self):
        self.algorithm = "HS256"
        self.secret_key = settings.SECRET_KEY

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception:
            return False

    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(seconds=settings.SESSION_TIMEOUT)

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            return None

    def generate_session_id(self) -> str:
        """Generate a secure session ID"""
        return secrets.token_urlsafe(32)


# Global security manager instance
security = SecurityManager()


class SessionManager:
    """Manages user sessions in Streamlit"""

    @staticmethod
    def init_session_state():
        """Initialize session state variables"""
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'user' not in st.session_state:
            st.session_state.user = None
        if 'user_role' not in st.session_state:
            st.session_state.user_role = None
        if 'session_token' not in st.session_state:
            st.session_state.session_token = None

    @staticmethod
    def login_user(user_data: Dict[str, Any]):
        """Login a user and set session state"""
        st.session_state.authenticated = True
        st.session_state.user = user_data
        st.session_state.user_role = user_data.get('rolle', 'auszubildende')

        # Create session token
        token_data = {
            "user_id": user_data.get('id'),
            "username": user_data.get('benutzername'),
            "role": user_data.get('rolle')
        }
        st.session_state.session_token = security.create_access_token(token_data)

    @staticmethod
    def logout_user():
        """Logout user and clear session state"""
        st.session_state.authenticated = False
        st.session_state.user = None
        st.session_state.user_role = None
        st.session_state.session_token = None

    @staticmethod
    def is_authenticated() -> bool:
        """Check if user is authenticated"""
        return st.session_state.get('authenticated', False)

    @staticmethod
    def get_current_user() -> Optional[Dict[str, Any]]:
        """Get current user data"""
        return st.session_state.get('user')

    @staticmethod
    def get_user_role() -> Optional[str]:
        """Get current user role"""
        return st.session_state.get('user_role')

    @staticmethod
    def verify_session() -> bool:
        """Verify current session token"""
        token = st.session_state.get('session_token')
        if not token:
            return False

        payload = security.verify_token(token)
        return payload is not None

    @staticmethod
    def has_permission(required_role: str) -> bool:
        """Check if current user has required permission"""
        if not SessionManager.is_authenticated():
            return False

        current_role = SessionManager.get_user_role()

        # Role hierarchy: admin > netzwerker > auszubildende
        role_levels = {
            'admin': 3,
            'netzwerker': 2,
            'auszubildende': 1
        }

        current_level = role_levels.get(current_role, 0)
        required_level = role_levels.get(required_role, 0)

        return current_level >= required_level


def require_auth(func):
    """Decorator to require authentication for a function"""
    def wrapper(*args, **kwargs):
        SessionManager.init_session_state()

        if not SessionManager.is_authenticated() or not SessionManager.verify_session():
            st.error("Sie müssen sich anmelden, um diese Seite zu sehen.")
            st.stop()

        return func(*args, **kwargs)

    return wrapper


def require_role(role: str):
    """Decorator to require specific role for a function"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            SessionManager.init_session_state()

            if not SessionManager.has_permission(role):
                st.error(f"Sie benötigen {role}-Berechtigung für diese Aktion.")
                st.stop()

            return func(*args, **kwargs)

        return wrapper
    return decorator