import pytest
import jwt
from datetime import datetime, timedelta

from src.api.admin import create_token, decode_token, JWT_SECRET, JWT_ALGORITHM


class TestTokenCreation:
    def test_create_token_returns_string(self):
        token = create_token({"user_id": 1, "username": "admin", "role": "super_admin"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_contains_payload(self):
        token = create_token({"user_id": 42, "username": "testuser"})
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        assert payload["user_id"] == 42
        assert payload["username"] == "testuser"

    def test_token_has_expiry(self):
        token = create_token({"user_id": 1})
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        assert "exp" in payload
        exp = datetime.utcfromtimestamp(payload["exp"])
        assert exp > datetime.utcnow()


class TestTokenDecoding:
    def test_decode_valid_token(self):
        token = create_token({"user_id": 1, "username": "admin", "role": "super_admin"})
        payload = decode_token(token)
        assert payload["user_id"] == 1
        assert payload["username"] == "admin"
        assert payload["role"] == "super_admin"

    def test_decode_expired_token_raises(self):
        payload = {
            "user_id": 1,
            "exp": datetime.utcnow() - timedelta(hours=1),
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        with pytest.raises(jwt.ExpiredSignatureError):
            decode_token(token)

    def test_decode_invalid_token_raises(self):
        with pytest.raises(jwt.InvalidTokenError):
            decode_token("invalid.token.here")

    def test_decode_tampered_token_raises(self):
        token = create_token({"user_id": 1})
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(jwt.InvalidTokenError):
            decode_token(tampered)
