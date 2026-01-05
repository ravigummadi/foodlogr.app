"""Unit tests for auth module - pure functions only."""

from src.shell.auth import (
    generate_api_key,
    hash_api_key,
    validate_api_key_format,
    API_KEY_PREFIX,
)


class TestGenerateApiKey:
    """Tests for generate_api_key."""

    def test_starts_with_prefix(self):
        """Generated key starts with flr_ prefix."""
        key = generate_api_key()
        assert key.startswith(API_KEY_PREFIX)

    def test_sufficient_length(self):
        """Generated key has sufficient length for security."""
        key = generate_api_key()
        # prefix (4) + base64 encoded 32 bytes (~43 chars)
        assert len(key) >= 40

    def test_unique_keys(self):
        """Each generated key is unique."""
        keys = [generate_api_key() for _ in range(100)]
        assert len(set(keys)) == 100


class TestHashApiKey:
    """Tests for hash_api_key."""

    def test_returns_32_char_hash(self):
        """Hash is exactly 32 characters."""
        key = "flr_test_key_12345678901234567890"
        hashed = hash_api_key(key)
        assert len(hashed) == 32

    def test_deterministic(self):
        """Same key always produces same hash."""
        key = "flr_test_key_12345678901234567890"
        assert hash_api_key(key) == hash_api_key(key)

    def test_different_keys_different_hashes(self):
        """Different keys produce different hashes."""
        key1 = "flr_key1_1234567890123456789012345"
        key2 = "flr_key2_1234567890123456789012345"
        assert hash_api_key(key1) != hash_api_key(key2)

    def test_hash_is_hex(self):
        """Hash contains only hex characters."""
        key = "flr_test_key_12345678901234567890"
        hashed = hash_api_key(key)
        assert all(c in "0123456789abcdef" for c in hashed)


class TestValidateApiKeyFormat:
    """Tests for validate_api_key_format."""

    def test_valid_key(self):
        """Valid key format returns True."""
        key = generate_api_key()
        assert validate_api_key_format(key) is True

    def test_empty_string(self):
        """Empty string returns False."""
        assert validate_api_key_format("") is False

    def test_none_value(self):
        """None returns False."""
        assert validate_api_key_format(None) is False

    def test_missing_prefix(self):
        """Key without prefix returns False."""
        assert validate_api_key_format("abc_12345678901234567890123456789012345") is False

    def test_wrong_prefix(self):
        """Key with wrong prefix returns False."""
        assert validate_api_key_format("api_12345678901234567890123456789012345") is False

    def test_too_short(self):
        """Key that's too short returns False."""
        assert validate_api_key_format("flr_short") is False

    def test_minimum_length(self):
        """Key at minimum length returns True."""
        # prefix (4) + 36 chars = 40 minimum
        key = "flr_" + "a" * 36
        assert validate_api_key_format(key) is True

    def test_below_minimum_length(self):
        """Key below minimum length returns False."""
        key = "flr_" + "a" * 35
        assert validate_api_key_format(key) is False
