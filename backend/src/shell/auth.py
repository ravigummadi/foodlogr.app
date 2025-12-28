"""Authentication - API key generation and validation.

Handles API key creation, hashing, and validation. Never stores plaintext keys.
"""

import hashlib
import logging
import secrets
from datetime import datetime

from google.cloud import firestore

from ..core.models import User


logger = logging.getLogger(__name__)

# API key prefix for identification
API_KEY_PREFIX = "flr_"


def generate_api_key() -> str:
    """Generate a cryptographically secure API key.

    Returns:
        API key in format: flr_<random_chars>
    """
    random_part = secrets.token_urlsafe(32)
    return f"{API_KEY_PREFIX}{random_part}"


def hash_api_key(api_key: str) -> str:
    """Hash an API key to create a user_id.

    Uses SHA256 and truncates to 32 chars for Firestore document ID.
    Never store plaintext API keys.

    Args:
        api_key: The plaintext API key

    Returns:
        32-character hash to use as user_id
    """
    return hashlib.sha256(api_key.encode()).hexdigest()[:32]


def validate_api_key_format(api_key: str) -> bool:
    """Check if API key has valid format.

    Args:
        api_key: The API key to validate

    Returns:
        True if format is valid
    """
    if not api_key:
        return False
    if not api_key.startswith(API_KEY_PREFIX):
        return False
    if len(api_key) < 40:  # prefix + at least some random chars
        return False
    return True


class AuthClient:
    """Client for API key authentication operations.

    Handles user registration and API key validation against Firestore.
    """

    def __init__(self, db: firestore.Client) -> None:
        """Initialize auth client.

        Args:
            db: Firestore client instance
        """
        self._db = db

    def _get_user_ref(self, user_id: str) -> firestore.DocumentReference:
        """Get reference to user document."""
        return self._db.collection("users").document(user_id)

    def register_user(self, email: str) -> tuple[str, str]:
        """Register a new user and generate their API key.

        Args:
            email: User's email address

        Returns:
            Tuple of (api_key, user_id) - api_key is only returned once!
        """
        logger.info("Registering new user: %s", email)

        api_key = generate_api_key()
        user_id = hash_api_key(api_key)

        user = User(
            email=email,
            api_key_hash=user_id,
            created_at=datetime.utcnow(),
        )

        self._get_user_ref(user_id).set(user.model_dump())

        logger.info("User registered successfully: %s", user_id[:8])
        return api_key, user_id

    def validate_api_key(self, api_key: str) -> str | None:
        """Validate an API key and return the user_id if valid.

        Args:
            api_key: The API key to validate

        Returns:
            user_id if valid, None if invalid
        """
        if not validate_api_key_format(api_key):
            logger.warning("Invalid API key format")
            return None

        user_id = hash_api_key(api_key)

        try:
            user_doc = self._get_user_ref(user_id).get()
            if user_doc.exists:
                logger.debug("API key validated for user: %s", user_id[:8])
                return user_id
            else:
                logger.warning("API key not found in database")
                return None
        except Exception as e:
            logger.error("Error validating API key: %s", str(e))
            return None

    def get_user(self, user_id: str) -> User | None:
        """Get user by ID.

        Args:
            user_id: The user's ID (hashed API key)

        Returns:
            User if found, None otherwise
        """
        try:
            user_doc = self._get_user_ref(user_id).get()
            if user_doc.exists:
                return User(**user_doc.to_dict())
            return None
        except Exception as e:
            logger.error("Error fetching user: %s", str(e))
            return None

    def user_exists(self, user_id: str) -> bool:
        """Check if a user exists.

        Args:
            user_id: The user's ID

        Returns:
            True if user exists
        """
        try:
            return self._get_user_ref(user_id).get().exists
        except Exception:
            return False
